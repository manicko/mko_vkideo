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

#### `B3-AUDIT` — block-`B3` audit findings (Auditor; read-only at `bccf8b9`)

Windows, CPython 3.12.1, `os.name == "nt"`. Every number below was executed, not reasoned.
No production file, no test file, no existing audit-phase file and nothing in the staging
area was touched; this section is the only edit.

Baseline re-measured and **identical to the block's**: `884 passed, 6 skipped, 1 warning in
41.09s` · `mypy src` `Success: no issues found in 31 source files` · `ruff check src tests`
`All checks passed!` · `ruff format --check src tests` `54 files already formatted` ·
`mypy src tests` `Found 93 errors in 8 files`.

##### `B3-A1` — the skip set: **confirmed**, 6 skips, **3 D-11 + 3 phase-05, no fourth D-11**

`uv run pytest -q -rs -p no:randomly`, complete `SKIPPED` output:

| # | Site | Reason | Class |
|---|---|---|---|
| 1 | `tests/test_config.py:980` `test_log_file_created_with_owner_only_permissions` | `Owner-only confinement is not offered on Windows: os.chmod there toggles only the read-only attribute, so the measured mode is 0o666 rather than the requested 0o600 (D-11).` | **D-11** |
| 2 | `tests/test_config.py:996` `test_existing_log_file_permissions_updated` | same string | **D-11** |
| 3 | `tests/test_hls_downloader.py:379` `TestCreateTempCookieFile::test_file_permissions_are_0600` | same string | **D-11** |
| 4 | `tests/test_ffmpeg_utils.py:163` `test_killpg_called_when_returncode_none` | `POSIX-only: killpg path` | not D-11 |
| 5 | `tests/test_ffmpeg_utils.py:186` `test_killpg_skipped_when_returncode_set` | `POSIX-only: killpg path` | not D-11 |
| 6 | `tests/test_hls_downloader.py:4602` `test_descendant_killed_on_posix` | `POSIX-only: killpg reaches descendants` | not D-11 |

`git show d572d96` confirms 4–6 came in with `TRN-001`/phase 05 and are unrelated. A grep for
`skipif` across `tests/` returns **7** guards: these six plus
`tests/test_hls_downloader.py:4621` `test_descendant_survives_on_windows`, which is
`skipif(sys.platform != "win32")` and therefore **runs** here. **Nothing is review-blocking.**
`T-B3` step 1 and `AC-3` are satisfied as written.

##### `B3-A2` — the three oracles, read exactly; none of their claims is expressible on Windows

**`O1` — `tests/test_config.py::TestEnvFileValidationRendering::test_log_file_created_with_owner_only_permissions`**

```python
    @pytest.mark.skipif(
        os.name == "nt",
        reason="Owner-only confinement is not offered on Windows: os.chmod there toggles "
        "only the read-only attribute, so the measured mode is 0o666 rather than the "
        "requested 0o600 (D-11).",
    )
    def test_log_file_created_with_owner_only_permissions(self, tmp_path: Path) -> None:
        """SEC-003: log file should be created with 0o600 permissions."""
        log_file = tmp_path / "app.log"
        settings = Settings(log_file=str(log_file), log_level="DEBUG")

        setup_logging(settings)

        mode = os.stat(log_file).st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
```

**`O2` — `tests/test_config.py::TestEnvFileValidationRendering::test_existing_log_file_permissions_updated`**

```python
    @pytest.mark.skipif(
        os.name == "nt",
        reason="Owner-only confinement is not offered on Windows: os.chmod there toggles "
        "only the read-only attribute, so the measured mode is 0o666 rather than the "
        "requested 0o600 (D-11).",
    )
    def test_existing_log_file_permissions_updated(self, tmp_path: Path) -> None:
        """SEC-003: existing log file should have permissions corrected to 0o600."""
        log_file = tmp_path / "existing.log"
        log_file.write_text("old content")
        # Set insecure permissions
        os.chmod(log_file, 0o644)

        settings = Settings(log_file=str(log_file), log_level="DEBUG")
        setup_logging(settings)

        mode = os.stat(log_file).st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
```

**`O3` — `tests/test_hls_downloader.py::TestCreateTempCookieFile::test_file_permissions_are_0600`**

```python
    @pytest.mark.skipif(
        os.name == "nt",
        reason="Owner-only confinement is not offered on Windows: os.chmod there toggles "
        "only the read-only attribute, so the measured mode is 0o666 rather than the "
        "requested 0o600 (D-11).",
    )
    def test_file_permissions_are_0600(self) -> None:
        """Test that the temp cookie file is created with 0o600 permissions (DF-007)."""
        cookies = "vk=sensitive_session_token"
        result = _create_temp_cookie_file(cookies)

        try:
            stat_info = os.stat(result)
            # DF-007: permissions should be 0o600 (owner read/write only)
            actual_mode = stat_info.st_mode & 0o777
            assert actual_mode == 0o600, f"Expected 0o600 permissions, got 0o{actual_mode:o}"
        finally:
            result.unlink(missing_ok=True)
```

| Oracle | Property it currently claims | Expressible on Windows? |
|---|---|---|
| `O1` | the **granted** mode of a file `setup_logging` created is `0o600` | **No.** Measured: `0o666`, always. `Path.touch(mode=0o600)` reaches `os.open(path, flags, 0o600)` and Windows discards everything but the writable bit. |
| `O2` | an **existing** log file's mode is **corrected to** `0o600` | **No**, as written: `chmod(0o644)` then `chmod(0o600)` both land on `0o666`, so the two calls are indistinguishable. See `B3-A4`. |
| `O3` | the yt-dlp cookie artefact's **granted** mode is `0o600` | **No.** Measured `0o666`. |

`O2`'s word "updated" is the only claim with a Windows analogue, and only if the starting
state is chosen so that `0o600` and `0o444` differ on this platform. `B3-A4` does that.

##### `B3-A3` — `D-4` resolved **per oracle**, not globally. Measurement first.

Raw `os.stat(...)` on this platform. `FILE_ATTRIBUTE_READONLY == 0x1`; a fresh file reports
`32` (`0x20`, `FILE_ATTRIBUTE_ARCHIVE`), a read-only file `33`, a directory `16`.

| # | State | `st_mode & 0o777` | `st_file_attributes` | `READONLY` bit | write after |
|---|---|---|---|---|---|
| A1 | fresh, `Path.touch(mode=0o600)` — `setup_logging`'s **absent** branch | `0o666` | `32` | clear | ok |
| A2 | `write_text` — the **exists** branch, pre-state | `0o666` | `32` | clear | ok |
| A3 | after `os.chmod(p, 0o644)` | `0o666` | `32` | clear | ok |
| A4 | after `os.chmod(p, 0o600)` — `setup_logging`'s **exists** branch | `0o666` | `32` | clear | ok |
| A5 | fresh `tempfile.mkstemp()` — the artefact path | `0o666` | `32` | clear | ok |
| A6 | after `os.chmod(p, 0o600)` on the artefact | `0o666` | `32` | clear | ok |
| A7 | control, `os.chmod(p, 0o444)` — **positive control** | `0o444` | `33` | **set** | **`PermissionError`** |
| A8 | back to `os.chmod(p, 0o600)` | `0o666` | `32` | clear | ok |
| A9 | fresh `mkdtemp` directory | `0o777` | `16` | clear | — |

Branch spy over a real `setup_logging` call, three preconditions:

| Precondition | Calls observed | Post-state |
|---|---|---|
| absent | `[Path.touch(mode=0o600), os.open(path, 0o600)]` | `0o666` / `32` / clear |
| exists, `0o666` | `[Path.chmod(p, 0o600)]` | `0o666` / `32` / clear — **identical to doing nothing** |
| exists, `0o444` | `[Path.chmod(p, 0o600)]` | `0o666` / `32` / **clear** — the attribute was flipped |

**Two facts decide `D-4`.** (i) On the **absent** branch a fresh file already has the
read-only bit clear, so `Alt B` is **vacuous** there — a file with neither `touch` nor `chmod`
reports byte-identical state (`B3-A4` counterfactual 1). (ii) On the **exists** branch a
`0o444` precondition is **flipped to clear** by `chmod(0o600)`, so `Alt B` is real and
**discriminating** there.

**Recommendation, with the criterion stated: `Alt B` where it is both satisfiable *and*
discriminating; `Alt A` only where `B` is vacuous. Criterion = "delete the property the
oracle names and the test must go red".** `Alt C` stays prohibited (§1.3.4 / `D-2`; `pywin32`,
`win32security`, `icacls` are all absent from `src/` and `pyproject.toml` — plan 12 `ART-007`
row 8 re-confirms no compensating control exists). `Alt B` here **claims no confinement**: it
asserts the file is not marked read-only, which is what `os.chmod(…, 0o600)` computes to on
Windows and is strictly weaker than "other principals cannot read it". Note also, measured:
Windows `st_mode` is a **synthetic projection of that single bit** (`0o444` vs `0o666`), not
a permissions record — so `Alt B` asserts the attribute, never the mode field.

##### `B3-A4` — falsification: which conversions actually discriminate

Each proposal was run three ways: intact, property removed, property changed. A conversion
is admissible only if the latter two go red.

| Proposal | Intact | Property removed | Property changed | Verdict |
|---|---|---|---|---|
| **`O1` → `Alt B`** (assert `READONLY` clear after `setup_logging`) | passes | **passes** — a file with no `touch`/`chmod` at all reports `0o666` / `32` / clear | passes | **VACUOUS — inadmissible.** `Alt A` is the only honest option for `O1`. |
| **`O1` → `Alt A`** (spy the absent branch) | `[Path.touch(0o600), os.open(0o600)]` | **no `touch` call recorded** → red | `mode` ≠ `0o600` → red | **discriminating.** Not the degenerate constant-equals-constant shape: it pins *that the absent branch is the one taken* and *that the 0o600 literal reaches `os.open`*. |
| **`O2` → `Alt B`, precondition reversed to `0o444`** | `0o444`/`33`/set → `0o666`/`32`/**clear** → passes | `Path.chmod` no-op ⇒ file stays `0o444`/`33`/set, and `logging.FileHandler` raises `PermissionError: [Errno 13]` → red | `chmod(0o444)` ⇒ same `PermissionError` → red | **discriminating, twice over.** |
| **`O3` → `Alt B`, `mkstemp` wrapper pre-marks `0o444`** | `0o666`/`32`/clear → passes (88 B written through the still-open fd) | file stays `0o444`/`33`/**set** → assertion red | same → red | **discriminating.** |

`O2`'s sabotaged runs fail with `PermissionError` from `logging.FileHandler`, not from the
oracle's own assertion. That is still red, and it is itself a fact worth recording: **on
Windows, `log_path.chmod(0o600)` is the only thing that lets `FileHandler` open a
pre-existing read-only log file.** The Implementor must say so in the docstring rather than
let a reader read the `PermissionError` as an unrelated flake.

##### `B3-A5` — the `R1`/`R2` coupling: **already covered. Do not duplicate.**

`R1` (`72c8283`) and `R2` (`6b18060`, `01325b4`) changed what the artefact's confinement *is*.
What is now assertable, and where it already lives:

| Property `R1`/`R2` deliver | Already asserted by | Windows-executable? |
|---|---|---|
| artefact's parent is a per-run private dir **this process created** | `TestCreateTempCookieFile::test_file_created_in_private_cookie_subdir` (`parent != temp_dir`, `temp_dir in parent.parents`, `parent in _COOKIE_ARTIFACT_DIRS`); `TestCookieArtefactLifecycle::test_create_cookie_artifact_dir_creates_private_subdir_in_temp` | yes |
| that directory is **removable** | `test_file_created_in_private_cookie_subdir` (`assert not result.parent.exists()`); `TestCookieArtefactLifecycle::test_remove_cookie_artifact_dir_removes_created_dir`, `::test_full_round_trip_removes_parent_dir`, and the two rewritten `finally` blocks | yes |
| sweep is **liveness-gated** | `test_sweep_stale_cookie_dirs_removes_dead_owner`, `::test_sweep_stale_cookie_dirs_preserves_live_owner` | yes |
| sweep is **default-deny** | `test_read_owner_pid_missing_file_returns_none`, `test_zero_length_owner_pid_survives_sweep`, `test_unparseable_owner_pid_survives_sweep`, `test_owner_pid_is_a_directory_survives_sweep`, `test_torn_digit_prefix_owner_pid_behaviour_is_explicit`, `test_pidless_new_dir_survives_sweep`, `test_pidless_dir_with_unknown_age_survives_sweep`, `test_pidless_dir_aged_past_grace_is_swept`, `test_created_cookie_dir_matches_the_sweep_filter`, plus `TestCookieArtefactCreationRaceAcrossProcesses` | yes |

**Stated plainly: the block's scope item 2 is already satisfied by landed coverage.** The two
classes measure **28 passed, 1 skipped** — the skip being `O3`. §`B3`'s instruction to "convert
it to assert what `R1` delivers" therefore **reduces to removing `O3`'s guard and giving it the
Windows-meaningful assertion**; re-asserting removability inside `O3` would be a fourth copy
of an existing oracle. `O3`'s docstring must **name** the tests that own the `R1`/`R2` property
instead. The POSIX mode check stays, as an **additive** `os.name != "nt"` half — never a
replacement (`T-B3` step 6).

`O3` does have one defect of its own: its `finally` unlinks the file but never removes the
directory `_create_temp_cookie_file` created, so it leaks a tracked `vk_cookies__dir<rand>/`
for the rest of the session. Measured: **delta 0 in `%TEMP%`** after a run of both classes —
`atexit` `_cleanup_cookie_artifact_dirs` reclaims it — so this is in-session accumulation
only, not permanent residue. `LOW`. `B3` is rewriting this exact test, so it should remove its
own directory (`_remove_cookie_artifact_dir(result.parent)`), which is what
`test_file_created_in_private_cookie_subdir` already does. The same one-line omission exists
in four sibling tests; that is a suite-wide cleanup and **not** `B3`'s.

##### `B3-A6` — the phantom requirement: **confirmed**. The `SEC-003:` comment is already correct.

- `argfile` — **zero** occurrences anywhere in `src/` (grep over `src/vkdownloader`).
- `git log -S "argfile" -- src/vkdownloader/config.py` — **empty**. It never appeared in that file.
- `git log -S "argfile" -- src/` returns only `d572d96` and `665c6ac`, both touching
  `src/vkdownloader/services/downloader.py` — the ffmpeg loader, not `config.py`.
- `git log -S "SEC-003" -- src/vkdownloader/config.py` returns exactly one commit, `665c6ac`,
  and its text is *"SEC-003: Create log file with owner-only permissions (0o600) before
  FileHandler opens it, so subprocess output sanitized for SEC-002 is not readable by other
  local users."* — **no argfile, ever**. Plan 11 §3.3 criterion 7's argfile clause and plan 11
  `T-B3` step 8's identical clause are **phantom**; `§2.6`'s strike is confirmed. Do not
  "fix" a clause that has no referent.

The comment as it reads today, above `config.setup_logging`'s log-file branch:

```python
        # SEC-003: Create the log file before FileHandler opens it, so subprocess
        # output sanitized for SEC-002 is not readable by other local users.
        # 0o600 sets POSIX permission bits, and that is the only place the
        # owner-only confinement is delivered: on Windows `touch(mode=...)` ignores
        # the mode and `chmod` toggles only the read-only attribute, so both
        # branches leave the file readable by any local user. Confinement is not
        # offered there (D-11); the mode is requested for its POSIX effect only,
        # and no access control list is applied.
```

Claim-by-claim against measurement: *"create the file before `FileHandler` opens it"* —
**true**, the `touch`/`chmod` block precedes `logging.basicConfig(handlers=[FileHandler(…)])`.
*"`touch(mode=...)` ignores the mode"* — **true**, `B3-A3` A1 (`os.open` receives `0o600`,
the file reports `0o666`/`32`/clear). *"`chmod` toggles only the read-only attribute"* —
**true**, A3/A4/A7/A8 flip `32↔33` and nothing else. *"both branches leave the file readable
by any local user"* — **true**, both end at `0o666`/`32`/clear. *"no access control list is
applied"* — **true**, no ACL API is imported or called anywhere in `src/`. *D-11 named* —
**true**. **Its substantive half is satisfied: the comment does not imply a confinement
Windows does not deliver**, because the very next sentence states that it does not.

**One residual, and it is not `B3`'s.** Sentence 1 states the *purpose* — "so subprocess
output … is not readable by other local users" — as an unqualified claim; the scoping arrives
one sentence later, with no in-line pointer. `LOW`, stylistic. `B3` must not touch it: doing so
would violate `AC-4`/`AC-6` ("no production file"), and `config.py`'s documentation is already
owned downstream by `B4` (§2.7) and `B6`. **Record it there; do not absorb it here.** An
undisclosed inaccuracy is the failure mode this plan warns about in §`R1-A14` C1/C2.

##### `B3-A7` — `B3` writes **no production file**. Confirmed and consequential.

| Candidate | Verdict |
|---|---|
| `src/vkdownloader/config.py` | **untouched.** `B3-A6`: the comment is accurate; the only residual is out of scope and owned by `B4`/`B6`. `T-B6` step 11's "do not touch `setup_logging`'s log-file `touch`/`chmod` branch or the `SEC-003:` comment — `B3` owns those" is therefore a **no-op**, which is the correct outcome, not an omission. |
| `src/vkdownloader/services/ytdlp_downloader.py` | **untouched.** `_create_temp_cookie_file` already calls `os.chmod(path, 0o600)` and its `DF-007:` comment already states the real property — *"Confine the artefact by location, not just by mode"*, "on Windows `os.chmod` toggles only the read-only attribute, so the owner-only guarantee is not offered there (D-11)". Nothing in `R1`/`R2` left a production gap for `B3` to fill. |
| `.gitignore`, `docs/STRUCT.md` | **untouched.** No duty (`R1-A6`, `R1-A13`). |

**File set: `tests/test_config.py`, `tests/test_hls_downloader.py`. Two test files, zero
production files.** `AC-4` is satisfied by construction, `git status` needs no gate, the
`B3`→`B6` `config.py` lock stays void, and the remaining `B3`→`B6` dependency is purely
*content* — the oracles exercise `setup_logging`'s final shape. Risk profile: **the lowest in
the plan.** No production behaviour can regress; the only failure modes are a weakened oracle
and the mypy delta.

`T-B3` step 4's "other gate" is also settled: plan 12's `ART-007` records `config.setup_logging`
as **`unchanged`**, and its remedy part (2) is `OUT` → `TST-013` (phase 10). Nothing has
changed the log-file branch, so `O1`/`O2` need no re-evaluation.

##### `B3-A8` — precise edits required, by symbol. This is the complete list.

1. **`tests/test_config.py` · `test_log_file_created_with_owner_only_permissions`** — delete the
   `skipif`; keep the POSIX half verbatim (`st_mode & 0o777 == 0o600`) under `if os.name != "nt"`;
   add a Windows half that monkeypatches `Path.touch` and `Path.chmod` with annotated spies,
   runs `setup_logging`, and asserts exactly one `Path.touch` recorded with `mode == 0o600`,
   no `Path.chmod`, and `getattr(os.stat(log_file), "st_file_attributes", 0) & 0x1 == 0` as a
   companion. Rewrite the docstring to state: *POSIX — granted mode is `0o600`, owner-only;
   Windows — only that the `0o600` request reached `os.open` on the absent branch and the file
   is not marked read-only; no ACL is applied and other local principals may read it (D-11).*
2. **`tests/test_config.py` · `test_existing_log_file_permissions_updated`** — delete the
   `skipif`; make the **precondition platform-opposite**: POSIX `os.chmod(log_file, 0o644)`,
   Windows `os.chmod(log_file, 0o444)` (read-only **set**, `attr == 33`); POSIX half asserts
   `st_mode & 0o777 == 0o600`, Windows half asserts
   `getattr(os.stat(log_file), "st_file_attributes", 0) & 0x1 == 0`, i.e. `setup_logging`
   **cleared** it. Docstring must add the measured Windows-only fact: this `chmod(0o600)` is
   what lets `logging.FileHandler` open a pre-existing read-only log file, and if it is
   removed the call raises `PermissionError` rather than failing an assertion. Name the
   property: *not* confinement.
3. **`tests/test_hls_downloader.py` · `test_file_permissions_are_0600`** — delete the `skipif`;
   keep the POSIX half verbatim; add a Windows half that wraps
   `vkdownloader.services.ytdlp_downloader.tempfile.mkstemp` (the file's existing pattern) so
   the returned path is `os.chmod(…, 0o444)`-marked **after** the fd is open, then asserts
   `getattr(os.stat(result), "st_file_attributes", 0) & 0x1 == 0` — proving
   `_create_temp_cookie_file`'s `os.chmod(path, 0o600)` reached the platform. Extend `finally`
   with `os.chmod(result, 0o600)` (so a sabotaged run does not fail in teardown with a
   `PermissionError` that masks the real assertion) and
   `_remove_cookie_artifact_dir(result.parent)` per `B3-A5`. Rewrite the docstring to state
   what is asserted on which platform **and to name by symbol**
   `test_file_created_in_private_cookie_subdir`, `test_full_round_trip_removes_parent_dir`
   and `test_remove_cookie_artifact_dir_removes_created_dir` as the owners of the `R1`
   removability / private-parent property, so `B3-A5` is traceable from the test itself.
4. **Commit message** — name all three conversions, state that the resulting total skip count
   is **3** and that all three are the pre-existing `killpg` skips from `12d97d4`, unrelated to
   this block; state `D-4` resolved **A for `O1`, B for `O2`, B for `O3`**, with `B3-A3`'s
   vacuity measurement as the reason `O1` could not take `B`; state that `test_temp_argfile_permissions_are_0600`
   and `_temp_argfile` are **absent by `d572d96` (`TRN-001`), not by this commit** (`T-B3`
   step 2 / §3.3 criterion 6); state that the `SEC-003:` argfile clause is **phantom** and no
   `config.py` line was touched (`AC-6`); record `B3-A6`'s residual comment inaccuracy as
   handed to `B4`/`B6`.
5. **Do not** add a fourth D-11 guard, weaken any POSIX assertion, fold a reformat in
   (`ruff format --check` is green — §2.3), or change any node ID (see `B3-A9`).

**Resulting skip count: 6 → 3. D-11 count 3 → 0.**

##### `B3-A9` — two mechanical hazards the Implementor will hit

- **`mypy src tests` is the binding gate** (`93 errors in 8 files`, delta must not rise).
  `tests/test_config.py` is one of the eight and `strict = true`. Consequences: the spy
  closures need explicit parameter annotations **and** return types (`disallow_untyped_defs`);
  `getattr(os.stat(p), "st_file_attributes", 0)` returns `Any` on the POSIX typeshed stub and
  `int` on the Windows one, so bind it to an annotated local (`attrs: int = …`) rather than
  comparing inline. `unittest.mock` is **not** imported in `tests/test_config.py`; the file's
  convention is `pytest.MonkeyPatch`, and `monkeypatch.setattr(Path, "touch", spy)` needs no
  new import — prefer it over adding `from unittest import mock`.
- **`tests/test_config.py`'s three SEC-003 log-file tests are in the wrong class.** All three
  sit in `TestEnvFileValidationRendering` (`class` at 866, next class at 1023), and the string
  at 969 — *"Tests for setup_logging log file creation and permissions (SEC-003)."* — is a
  **bare no-op expression between methods**, not a class docstring: `TestEnvFileValidationRendering`'s
  real docstring is at 867. Moving `O1`/`O2`/`test_log_file_created_when_absent` into a
  correctly named `TestSetupLoggingLogFilePermissions` would give the platform-scoped docstrings
  `AC-5` demands a real home. **Not required by any criterion** and it changes three node IDs
  (so `AC`'s "named conversion" must list the old names), but `B3` is rewriting all three
  bodies anyway and this is the cheapest moment. **[BEST-PRACTICE] — recommended, effort
  trivial.** Leaving them in place is acceptable if the Planner prefers a minimal diff; either
  way the dead string at 969 must not be left as if it were documentation.

##### `B3-A10` — no existing expectation has to change

Checked every oracle `B3` touches and every one it neighbours. **Nothing weakens, nothing
inverts, no rename is required.** The POSIX halves of `O1`/`O2`/`O3` survive verbatim as
additive branches; the four `TestCreateTempCookieFile` and fifteen
`TestCookieArtefactLifecycle` tests are untouched; `R1`'s `test_file_created_in_private_cookie_subdir`
is untouched. **No design failure to report** — which is the outcome `AC`-5 requires, because
the only expectation that *would* have had to move is the `SEC-003:` comment's argfile clause,
and there is none to move.

**Advisories carried (none is a `B3` defect):** `B3-A6`'s comment sentence 1 → `B4`/`B6` ·
`B3-A5`'s four sibling tests that leak their artefact directory in-session → suite cleanup ·
`B3-A9`'s class mislocation → this block, optional.

**Audit footprint: this section only.** No code, no test, no plan 11 edit, no staging, no
commit. Three `vk_cookies__dir*` directories left in `%TEMP%` by the falsification harness's
sabotaged cases (read-only files; removal was denied by tooling) are outside the repository and
are reclaimed by the OS temp cleaner.

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

#### `B4-AUDIT` — block-`B4` audit findings (Auditor)

Read-only inspection at `01325b4`. Nothing in `src/`, `tests/`, or any audit-phase file was
touched; the only edit is this subsection. Claims are marked **[read]** (verified by reading),
**[exec]** (verified by running code on this machine, Windows/CPython 3.12), **[uncertain]**.

##### `B4-A1` — `utils/url_sanitizer.py` defines exactly five symbols; `_URL_REGEX` is the whole of the matching surface

| Symbol | Current behaviour **[read]** | Docstring/comment claim **[read]** |
|---|---|---|
| `_URL_REGEX` | `re.compile(r"https?://[^\s'\"<>]+")` — one literal-gated pattern; excluded set is whitespace, `'`, `"`, `<`, `>` and **not** `*`, `/`, `\`, `=` | line 6-7: "Matches http/https URLs in text (including query strings with signed tokens). Used to redact URLs found in subprocess stdout/stderr before logging." — **accurate, URL-only** |
| `_strip_auth_params` | `urlsplit` → `f"{scheme}://{netloc}/***REDACTED***"`; bare `***REDACTED***` when scheme or netloc is missing or `urlsplit` raises | "preventing signed CDN URLs with embedded tokens from leaking into log files" — **accurate; corrected by `09f1b10`, do not revisit** |
| `sanitize_text_for_log` | one `_URL_REGEX.sub(lambda m: _strip_auth_params(m.group(0)), text)`. **No alternative branch, no rule table, no ordering decision.** | "preventing signed CDN URLs with embedded tokens in subprocess output" — **accurate**; `Returns:` claims `scheme://host/***REDACTED***/` (a trailing `/` the code does not emit — cosmetic, see `B4-A10`) |
| `sanitize_url_for_log` | `return _strip_auth_params(url)` — a pure public alias, adds nothing | duplicates `_strip_auth_params`'s accurate claim |
| `__all__` (module) | `["_strip_auth_params", "sanitize_text_for_log", "sanitize_url_for_log"]` — **differs from the package's** (below) |

Measured by AST over `src/` **[exec]**: `_strip_auth_params` has **63** call sites, of which
**2 are internal** (inside `sanitize_url_for_log` and `sanitize_text_for_log`), leaving **61**
external — `ytdlp_downloader` 20, `extractor` 12, `segment_downloader` 12, `network_monitor` 10,
`downloader` 3, `batch_downloader` 2, `exceptions` 1, `downloader_throttle` 1 — plus the
`utils/__init__.py` re-export. `sanitize_url_for_log` has **2** (`cli.py` `download_failed`,
`invalid_url_in_batch`). `sanitize_text_for_log` has **3** (`ffmpeg_utils` 2, `ytdlp_downloader` 1)
— all three listed in `B4-A3`. `B4` touches none of the 61; `sanitize_url_for_log` and
`_strip_auth_params` behaviour are out of scope.

##### `B4-A2` — `utils/__init__.py` `__all__` confirmed; the package's own convention is inconsistent **[read]**

`["validate_output_path", "sanitize_title", "_resolve_output_file", "sanitize_url_for_log",
"_strip_auth_params"]` — exactly as plan 17 §2.8 states. `sanitize_text_for_log` is deliberately
absent and must stay absent (`T-B4` step 9). The convention is inconsistent in two directions at
once: `_strip_auth_params` and `_resolve_output_file` are underscore-named yet exported, while
`sanitize_text_for_log` — the function `B4` widens — is not. **Recommendation: do not touch this
file in `B4`** (`targets: no-change`). The inconsistency is pre-existing and plan 11 §4.3 already
records that "`must be a public name`" for `B6`'s processor is a plan-level decision, not a
package consequence. Fixing it here would widen the diff for no `SEC-006` benefit.

##### `B4-A3` — the call-site set is **three sites / three call classes**; `T-B4` step 1's "a fourth is a finding" does **not** trigger **[read + exec]**

Exhaustive AST sweep of `src/` — 3 `Call` nodes, `ffmpeg_utils` 2 and `ytdlp_downloader` 1
(the only other `src/` hits are two import lines). All three pass **raw child output**, never a
`Path` and never a header:

| # | File | Enclosing symbol | Passes | Lands in |
|---|---|---|---|---|
| 1 | `services/ytdlp_downloader.py` | `_download_with_ytdlp` | `sanitize_text_for_log(error_msg)` where `error_msg = output_data.decode() if output_data else "Unknown yt-dlp error"` — the **joined yt-dlp stdout transcript** | `download_failed.error` |
| 2 | `services/ffmpeg_utils.py` | `_merge_batch_segments` | `sanitize_text_for_log(error)[:200]` where `error = stderr.decode() if stderr else "Unknown error"` | `batch_merge_failed.error` |
| 3 | `services/ffmpeg_utils.py` | `_perform_final_merge` | `sanitize_text_for_log(stderr.decode())[:200] if stderr else "Unknown"` | `final_merge_failed.error` |

**`batch_merge_failed` and `final_merge_failed` confirmed** — both already pass
`error=sanitize_text_for_log(...)`, landed by `486bfd9`. **Not modified by this audit; they are
plan-10 `B14`'s.** Consequence for `B4`: idempotency is load-bearing in production **today**, at
sites 2 and 3, before `B5`/`B6` land — and site 2/3's transform is applied to bytes that then get
truncated to 200 chars, so any rule that *expands* text can silently move the truncation boundary.

##### `B4-A4` — live instances: two `SEC-006` paths, three `SEC-007` exception texts; full `path=str(...)` inventory **[read]**

**`SEC-006` instances (a path the transform provably cannot match — measured byte-identical in `B4-A9`):**

| Record | File / symbol | Field |
|---|---|---|
| `cookie_file_cleaned_up` (**DEBUG**, on **every successful download** — larger exposure than the warning, because it fires on the success path) | `ytdlp_downloader.py::_download_with_ytdlp`, the `finally:` else-arm | `path=str(cookie_file)` |
| `cookie_file_cleanup_failed` (**WARNING**) | `ytdlp_downloader.py::_download_with_ytdlp`, `finally:` except-arm | `path=str(cookie_file)` |
| `cookie_file_cleanup_failed` (**WARNING**) | `ytdlp_downloader.py::_remove_cookie_artifact_dir` | `path=str(cookie_dir)` |

All three confirmed at `01325b4` with those exact field names. `R1` removes the third from the
success path but it survives on genuine survival; `B4` makes all three matchable, `B6` owns the
pipeline. **`SEC-007` instances (untransformed exception text, owned by `B6`):** the sibling
`error=str(exc)` / `error=str(failure)` on all three records above.

**Every record carrying `path=str(...)` in `src/` — complete, for `D-7`'s key allowlist:**
`cli.py::_log_env_file_path` `env_file_resolved`; `utils/security.py::validate_output_path`
`output_path_inside_repository`; `ytdlp_downloader.py::_download_with_ytdlp`
`cookie_file_cleanup_failed` + `cookie_file_cleaned_up` + `ytdlp_not_found` (the last uses
`path=exc.filename`, not `str(...)` — a binary path, still a path);
`ytdlp_downloader.py::_remove_cookie_artifact_dir` `cookie_file_cleanup_failed`;
`ytdlp_downloader.py::_download_with_ytdlp` `failed_to_cleanup_partial_file`;
`ytdlp_downloader.py::_attempt_segment_resume` `download_interrupted_switching_to_segments`.
**Only the three cookie-artefact records are `SEC-006`.** The rest carry **user-chosen output
paths** (the operator's own download directory) and are explicitly *not* credential artefacts —
redacting them would destroy the field operators triage with, and they are out of `B4`'s scope.

##### `B4-A5` — documentation sites: §2.7's two corrections confirmed; a **third, un-enumerated over-claim survives** **[read + exec]**

Confirmed via `git show 09f1b10` (body names both, diff touches exactly the two sites):
`sanitize_text_for_log`'s docstring now reads "preventing signed CDN URLs with embedded tokens"
and `ytdlp_downloader.py`'s `# SEC-002:` comment above `error_msg = sanitize_text_for_log(error_msg)`
now reads "redact any signed CDN URLs that yt-dlp may echo in error messages". **Do not re-litigate
either.** `ffmpeg_utils.py`'s import-site comment ("SEC-002: redact signed CDN URLs from
merge-failure stderr before logging") and `config.py`'s `SEC-003:` comment (about log-file
permissions, not the transform) are both **accurate**. `url_sanitizer.py`'s module docstring and
line 6-7 comment are URL-only and **accurate**.

**`B4-A6` — the surviving over-claim is on `_COOKIE_ARTIFACT_SUFFIX`, not on any sanitizer site.**
`ytdlp_downloader.py`'s comment above the frozen constants asserts: *"the suffix `.cookies.txt` is
what the operator-facing **redaction and cleanup tooling keys on**."* Measured: `.cookies.txt`
appears **only** as the value of `_COOKIE_ARTIFACT_SUFFIX` in `src/`. There is no redaction tooling,
no cleanup tooling, and no second consumer. This is the same defect class as `SEC-006` — a coverage
claim nothing implements — and it is **not** in plan 17's §2.7 list, so §2.7's "documentation duty
is exactly two items" is wrong. It is also the strongest *reason* `B4`'s rule should key on the
**suffix** as well as the prefix: doing so is what makes this comment true. Either the rule matches
`vk_cookies_….cookies.txt` (comment becomes true, preferred) or the comment is corrected in the
same commit. `AC` needs an eighth row for it. **[SPEC-DEVIATION]**, advisory, effort trivial.

##### `B4-A7` — `vk_ffmpeg_*.args` is a phantom artefact family; only one artefact family exists **[read + exec]**

Plan 11 §3.4 Alt A names two patterns, `vk_cookies_*.cookies.txt` and `vk_ffmpeg_*.args`.
Measured: `vk_ffmpeg` has **zero** occurrences in `src/`; the argfile mechanism was deleted by
plan-10 `B10` (`486bfd9`/`09f1b10` lineage; `argfile` is also absent — plan 17 §2.6 already
established that for `SEC-003`). `mkstemp`/`NamedTemporaryFile`/`TemporaryDirectory` appear
**exactly once** in `src/` — the cookie artefact. The real second shape is the artefact
**directory** `vk_cookies__dir<8 chars>` (composed `_COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX`),
plus `owner.pid` inside it. The ffmpeg concat list files `batch_list_<n>.txt` / `final_list.txt` are
argv paths a child could echo but are **not** prefixed artefacts and carry no credential material.
**Alt A's rule list must be `vk_cookies_` (file) + `vk_cookies__dir` (directory), not `vk_ffmpeg_`.**

##### `B4-A8` — `D-5` **measured: `Alt A`.** No sink receives a `Cookie:`/`Set-Cookie:` header from a child process

The criterion is explicit and it is **not met**, on three independent measured grounds:

1. **yt-dlp is never asked to print headers.** `_build_ytdlp_cli_command` passes `--no-warnings`
   and **no `--verbose`**; its output therefore contains no request headers. The only cookie it
   receives is a **path** via `--cookies <path>` — a `SEC-006` path instance, not a header.
2. **ffmpeg has no header to print and is not asked to print one.** `-headers` appears **zero
   times** in `src/`; `config.py` passes no `-loglevel`/`-v`/`-verbose`. `_build_ffmpeg_concat_command`
   is the **only** ffmpeg command builder and it drives the concat demuxer over **local files** —
   it makes no HTTP request at all.
3. **The only `Cookie:` values the product builds are in-process.** `_format_cookies_for_ffmpeg`
   builds a `"; "`-joined `name=value` string; its only consumer is `segment_downloader`'s
   `headers["Cookie"] = …` for an **aiohttp** request. `services/downloader.py` forwards `cookies`
   only into `download_with_ytdlp_with_resume_fallback`, which writes it to a **file**. Nothing
   hands a `Cookie:` header to a child, and no child is configured to echo one.

`Alt B` therefore adds a rule for a shape **nothing produces** — speculative, exactly as the plan
warns. **`D-5` → `Alt A`; documentation item (b) (name `Cookie:` as uncovered) therefore applies.**
Whether a third-party tool *could* print one remains plan 11's skip S-4 and stays declined;
the criterion asks what a sink **is measured** to receive, and the answer is nothing. **[read + exec]**

##### `B4-A9` — idempotency: the current transform holds, and two concrete double-apply constructions exist

Measured **[exec]** on live artefact paths (`...\Temp\vk_cookies__dir9lfm4h4w4\vk_cookies_abc123.cookies.txt`):

- Today's transform is a **fixed point on every sample tried** — signed URL, `Location:` line,
  `Cookie:`/`Set-Cookie:` line, argv echo, benign ffmpeg text, and the already-marker string
  `***REDACTED***` — because `_URL_REGEX` is gated on the literal `https?://`, and
  `_strip_auth_params`'s own output always re-emits `scheme://host/`. The URL rule re-matching its
  own output is harmless: the replacement is a fixed point, not a growth.
- `***REDACTED***` contains only `*`, `[A-Z_]`. It matches **no** rule gated on `vk_cookies_`,
  `_dir`, `.cookies.txt`, `owner.pid`, `Cookie:`. **But it does match `[^\s'\"]+`** (verified), so
  idempotency is *not* free — it depends entirely on every new rule being **literal-anchored**.

**Two constructible hazards, both measured:**

- **`B4-A9a` — a path-shaped rule whose replacement preserves a parent directory, combined with a
  second dir-shaped rule, double-applies.** This is realistic, because `B4-A7` shows the product has
  **two** artefact shapes, so a two-rule Alt A is the natural implementation. With
  `vk_cookies_[^\s'\"]+` → (parent kept) + `vk_cookies__dir[^\s'\"]*` → `***REDACTED***`: pass 1
  yields `...\Temp\vk_cookies__dir9lfm4h4w4\***REDACTED***`; pass 2 collapses it further to
  `...\Temp\***REDACTED***`. Measured `pass1 != pass2`. **Each rule is individually idempotent;
  the pair is not.** This is the "path-shaped match inside an already-redacted line" case, and it
  is the strongest argument for the plan's default: **one** prefix-anchored rule (`vk_cookies_`)
  covering both shapes, whole-token replacement, `***REDACTED***`. That was measured idempotent.
- **`B4-A9b` — a rule that can match `*` grows without bound.** `re.compile(r"\*+")` →
  `***REDACTED***` measured: pass 1 `***REDACTED***REDACTED***REDACTED***`, pass 2 grows again.
  Never reachable from `SEC-006`, but it is the concrete proof that "`***REDACTED***` must not
  itself match any rule" (plan 11 §3.4) is a real requirement, not boilerplate. **[BEST-PRACTICE]**
  the test must assert `sanitize_text_for_log(MARKER) == MARKER` and
  `sanitize_text_for_log(sanitize_text_for_log(t)) == sanitize_text_for_log(t)` for **each** rule.

Ordering measured **[exec]**: applying an artefact rule **before** or **after** the URL rule leaves
`test_transform_before_truncate_proves_sanitize_order` intact in both orders (`len == 200`,
`cdn.example.com` retained). Ordering is therefore not a hazard for the existing oracles — but the
200-char truncation at sites 2-3 means a rule that *expands* text does move that boundary.

##### `B4-A10` — tests: `TestSanitizeTextForLog` holds **8** cases, not 4, and **one is path-shaped and asserts the opposite of `B4`**

`uv run pytest tests/test_url_sanitizer.py --collect-only -q` → **16 collected** = 8
`TestStripAuthParams` + **8** `TestSanitizeTextForLog` **[exec]**. Provenance **[read]**:
`TestStripAuthParams`'s 8 are original; `TestSanitizeTextForLog`'s are 4 original
(`test_redacts_url_in_text`, `test_redacts_multiple_urls_in_text`,
`test_preserves_text_without_urls`, `test_redacts_url_in_yt_dlp_output`) + 3 added by `486bfd9`
(`test_transform_before_truncate_proves_sanitize_order`,
`test_redacts_signed_cdn_url_in_merge_failure_text`, `test_preserves_plaintext_merge_failure_text`)
+ 1 added by `09f1b10`. Plan 11's "four existing cases" and `T-B4` step 6's "**there are none
today**" are both stale. **`[SPEC-DEVIATION]`.**

**The path-shaped input does exist today, and it is an inverse tripwire.**
`test_filesystem_paths_are_not_redacted` asserts `cookie_path in result` — i.e. it **pins the
non-coverage** and will **fail** under any rule broad enough to match its input. Its docstring says
it "pins the capability boundary so the redaction claim cannot silently drift back". It also uses
`/tmp/vkdownloader_cookies_8u3x.txt` — a **fictional** prefix; the product emits `vk_cookies_`, and
`"vk_cookies_"` is not a substring of `"vkdownloader_cookies_8u3x.txt"`. Measured **[exec]**: that
input therefore **passes unchanged** under a `vk_cookies_`-anchored rule and **is redacted** under
a broad one. So the oracle does not test what it claims and its outcome depends on rule width.
**`B4` must touch it** — it is the reason the "four existing cases pass unchanged" evidence is not
sufficient, and house rule 2 (production code is king) makes the choice explicit, not silent.
Recommend: **re-aim** it at the real artefact shape and the new behaviour (name, reason, in-commit),
keeping a byte-identical negative case with a *benign* path. All **7** other cases must pass
**unchanged** — that, not 4, is the evidence the rule is additive. **[SPEC-DEVIATION]**, mandatory.

To add: (a) the real `cookie_file_cleanup_failed` `path=` shape and the `cookie_file_cleaned_up`
`path=` shape, as separate named cases; (b) the artefact **directory** shape `vk_cookies__dir…`;
(c) byte-identical on text with no artefact token; (d) host still visible;
(e) double-application equals single, per rule; (f) `MARKER` is a fixed point; (g) the re-aimed
negative case. Header-shaped: **no input needed** — under `Alt A` a `Cookie:` case asserts it is
**not** covered, which is documentation-as-test (`B4-A8`).

##### `B4-A11` — replacement shape: what the artefacts look like, and what each choice costs **[read + exec]**

Measured real artefacts: file `C:\Users\<user>\AppData\Local\Temp\vk_cookies__dir<8 chars>\vk_cookies_<8 chars>.cookies.txt`;
directory `…\Temp\vk_cookies__dir<8 chars>`; plus `owner.pid` inside. The temp root on this machine
is `C:\Users\NMATVE~1\AppData\Local\Temp` **[exec]** — a **username-bearing** parent.

- **Whole token → `***REDACTED***`** (plan's default). Costs: the operator loses the fact that the
  *artefact* was involved — but the record name (`cookie_file_cleanup_failed`) already says that,
  and it removes the username, the temp root and the random tails in one step. Idempotent by
  measurement (`B4-A9`).
- **Preserve basename.** Costs more than it buys: the basename is `vk_cookies_<8 random chars>`,
  i.e. **zero triage value** — the discriminators live in the record name, not the filename. And
  a `vk_cookies_`-preserving basename **re-matches its own rule** (`B4-A9a`), so it forfeits
  idempotency for no gain. **Recommend against.**
- **Preserve parent directory.** Strictly worse: the parent *is* the other artefact
  (`vk_cookies__dir<rand>`) and its own parent is the **username-bearing** temp root — exactly the
  `C:\Users\<name>\AppData\…` case plan 11 §3.4 names as identifying. Measured to double-apply.
  **Recommend against.**
- **[BEST-PRACTICE] the suffix is the one fragment with real triage value** — `.cookies.txt`
  confirms *which* artefact. It costs nothing (it is not itself an anchor, so it cannot re-match)
  and it is what makes the `_COOKIE_ARTIFACT_SUFFIX` comment true (`B4-A6`). Priority
  **recommended, not mandatory**; it is a §9 Q2 product call, so surface it, do not decide it.

##### `B4-A12` — corrections to the `B4` block text above

| # | Correction | Class |
|---|---|---|
| 1 | "four existing cases" / "there are none today" → **8** cases, **one path-shaped** (`B4-A10`) | `[SPEC-DEVIATION]` |
| 2 | `T-B4` step 1's "a fourth is a finding" → **not triggered**; 3 sites / 3 classes confirmed (`B4-A3`) | `[DOC-UPDATE]` |
| 3 | Alt A's `vk_ffmpeg_*.args` → **phantom**; real shapes are the file **and** `vk_cookies__dir` (`B4-A7`) | `[SPEC-DEVIATION]` |
| 4 | `D-5` → **`Alt A`**, measured on three grounds (`B4-A8`); item (b) therefore **applies** | decision input |
| 5 | §2.7's "documentation duty is exactly two items" → **three**; `_COOKIE_ARTIFACT_SUFFIX`'s comment also over-claims (`B4-A6`) | `[SPEC-DEVIATION]` |
| 6 | `AC` needs: a marker-is-a-fixed-point case; the re-aimed `test_filesystem_paths_are_not_redacted`; a per-rule double-application case | `[BEST-PRACTICE]` |
| 7 | §2.5 already notes `cookie_file_cleaned_up`; **`AC-1` should name both records' exact `path=` shapes** and the **directory** shape (`B4-A4`) | `[DOC-UPDATE]` |

**Not touched by this audit:** `services/ffmpeg_utils.py`'s two sinks and every merge code path
(plan-10 `B14`'s); `_URL_REGEX`; `_strip_auth_params`; `utils/__init__.py`; all `tests/` and `src/`
files. Gates spot-checked green at `01325b4`: `ruff check src tests` "All checks passed!",
`ruff format --check src tests` "54 files already formatted", `mypy src` "Success: no issues found
in 31 source files". Full-suite and `mypy src tests` counts adopted from the task brief, not
re-derived.

#### `B4-RESEARCH` — the rule set, the idempotency proof, and the replacement shape (Researcher)

Read-only at `01325b4`. **No production code, no test, and no audit-phase file was touched**; the
only edit is this subsection. Nothing staged, nothing committed. Claims are marked **[read]**
(verified by reading the tree), **[exec]** (verified by running code on this machine,
Windows / CPython 3.12.1), **[uncertain]**. Supersedes the `B4` block's "genuine uncertainty" on
rule shape; `D-5` was already closed to `Alt A` by `B4-A8`. **Builds on `B4-AUDIT`; three of its
statements are corrected below (`B4-R12`).**

##### `B4-R1` — decision: **two named rules, URL rule first**, whole-token replacement

```python
_ARTEFACT_LEAD = r"(?<![^\s'\"<>])(?:[^\s'\"<>]*[\\/])?"
_COOKIE_FILE_ARTEFACT_REGEX = re.compile(
    _ARTEFACT_LEAD + r"vk_cookies_[a-z0-9_]+\.cookies\.txt"
)
_COOKIE_DIR_ARTEFACT_REGEX = re.compile(
    _ARTEFACT_LEAD + r"vk_cookies__dir[a-z0-9_]+"
)
```

Applied in this order, replacement the existing constant `***REDACTED***` for both:

```python
text = _URL_REGEX.sub(lambda m: _strip_auth_params(m.group(0)), text)   # 1. URL first
text = _COOKIE_FILE_ARTEFACT_REGEX.sub("***REDACTED***", text)          # 2. file artefact
text = _COOKIE_DIR_ARTEFACT_REGEX.sub("***REDACTED***", text)           # 3. dir artefact
```

**Anchor on prefix + suffix, not prefix alone.** The frozen literals are
`_COOKIE_ARTIFACT_PREFIX = "vk_cookies_"`, `_COOKIE_ARTIFACT_SUFFIX = ".cookies.txt"`,
`_ARTEFACT_DIR_SUFFIX = "_dir"` **[read]**. Keying the file rule on the **suffix** is the
load-bearing decision, for two measured reasons:

1. **It removes the false positive a prefix-only rule has.** Measured **[exec]**: a user-chosen
   output folder `C:\Users\x\Videos\vk_cookies_videos\clip.mp4` **is** matched by a prefix-only
   rule `vk_cookies_[a-z0-9_]+` and **is not** matched by the suffix-keyed rule. A user who names
   a download folder with the product's own prefix would otherwise lose that path from
   `download_failed` on every failure — the exact degradation the plan calls a regression no test
   would catch. Suffix keying makes the collision require the literal string `.cookies.txt` or
   `_dir`, which is not something a folder name acquires by accident.
2. **It makes `_COOKIE_ARTIFACT_SUFFIX`'s comment true** (`B4-A6`): that comment says the suffix
   "is what the operator-facing redaction and cleanup tooling keys on". After this change the
   redaction tooling demonstrably keys on it. "Cleanup tooling" remains an over-claim — there is
   none — so the comment should be **reworded to name the redaction rule only**, in this commit.

**The random tail is `[a-z0-9_]+`, not `{8}`** **[exec]**: `tempfile._RandomNameSequence.characters
== "abcdefghijklmnopqrstuvwxyz0123456789_"` and its docstring says "Each string is eight characters
long". Hard-coding `{8}` would couple the rule to a CPython internal; `+` is length-agnostic and
still cannot match a bare `vk_cookies_` with no name. **The drift guard must be behavioural, not
literal**: a test that calls the product's own `_create_cookie_artifact_dir()` and
`_create_temp_cookie_file()`, then asserts `sanitize_text_for_log(str(path))` contains no
`vk_cookies_`. A constant-equality test is the second line of defence, not the first — and the
constants cannot be *imported*: `utils/` imports only `config`/`exceptions`/`models`, never
`services`, while `services/ytdlp_downloader.py` imports `utils.url_sanitizer`, so importing them
would invert the layer order and create a cycle **[read]**. Duplicate the literals in the pattern
and point the comment at their source.

**Why file-before-dir.** The file rule's match span **subsumes** the directory's anchor in a nested
path, so file-first collapses `…\vk_cookies__dir<rand>\vk_cookies_<rand>.cookies.txt` to a **single**
marker, whereas dir-first yields two **[exec]**. Both orders are fixed points (below), so this is
cosmetic determinism, not safety — but it is free, so fix the order and document it.

##### `B4-R2` — `A9a` resolved: the two-rule design **is** provably idempotent, because the failure was the *replacement*, not the arity

`B4-A9a` measured a parent-preserving file rule plus a directory rule double-applying. That failure
is caused entirely by **rule 1's output containing rule 2's anchor** (`…\vk_cookies__dir<rand>\***`).
It cannot recur here, and the general condition is short enough to state as the design law:

> A set of rules applied in sequence is a fixed point if (i) every rule's replacement contains no
> anchor of any rule, and (ii) no rule's left boundary can be satisfied by a replacement.

With the constant replacement `***REDACTED***` — which contains no `vk_cookies_` — (i) holds by
inspection. (ii) is the non-obvious half and it is where `\b` fails (`B4-R3`). Measured **[exec]**:
both rule orders are fixed points on the nested path, and the two-rule table and a single combined
pattern are **byte-identical over 200 000 fuzz cases** (0 differences), so the arity choice costs
nothing functionally.

**Two named patterns, not one combined.** `T-B4` step 3 requires "named, individually testable
rules"; an alternation inside one pattern makes per-rule idempotency testable only by reading the
source. The single combined pattern `vk_cookies_(?:[a-z0-9_]+\.cookies\.txt|_dir[a-z0-9_]+)` is
**measured equivalent** and is the documented fallback if the Planner wants one constant instead —
the report to the Implementor should then say per-rule idempotency is proven by the fuzz oracle
rather than by a named test.

##### `B4-R3` — the left boundary: **not `\b`**, and the general law it reveals

**`\b` is wrong here, and it is wrong in the one way that matters.** Measured **[exec]**, with the
full rule set and a 400 000-case fuzz over an alphabet of every dangerous character:

| Left guard | fixed-point violations / 400 000 |
|---|---|
| none | **0** |
| `\b` | **3** |
| `(?<![^\s'\"<>])` (**chosen**) | **0** |

Minimal counterexample **[exec]** — `dir\vk_cookies_a.cookies.txtvk_cookies_b.cookies.txt`:

```
\b guard :  p1 = ***REDACTED***vk_cookies_b.cookies.txt      <- left behind
           p2 = ***REDACTED******REDACTED***                 <- CHANGED
```

Mechanism: `\b` fires on a `\w`/`\W` transition, and the replacement **ends in `*`**, a non-word
character. A replacement therefore *manufactures* a boundary that the original bytes did not have,
so a name that was glued to a word character in pass 1 becomes matchable in pass 2. The general
law, worth writing into the commit message because it is easy to re-introduce:

> **A rule's left boundary must be a predicate its own replacement can never satisfy.** Any guard
> the marker satisfies is a growth path.

`(?<![^\s'\"<>])` is chosen because the marker's `*` is *inside* `[^\s'\"<>]`, so it can never
satisfy the guard **[exec]**. It is a legal pattern — the contained class has fixed length one —
whereas a variable-length lookbehind to a path separator is impossible ("The contained pattern must
only match strings of some fixed length, meaning that `abc` or `a|b` are allowed, but `a*` and
`{3,4}` are not", `docs.python.org/3/library/re.html`, `(?<=...)`) **[read]**. That prohibition is
*why* the parent must be **consumed** by the optional greedy `(?:[^\s'\"<>]*[\\/])?` group rather
than asserted by lookbehind: consumption is the only way left, and consuming is also what removes
the username.

**The trailing boundary must not consume the terminating separator**, and the match must end at
the end of the artefact *name*. Three reasons, all measured **[exec]**: separators are the run
delimiters, so consuming one would fuse the marker to the following path component
(`***REDACTED***\owner.pid` becomes `***REDACTED****owner.pid`, destroying structure); the last
component of a path has no terminating separator to consume ("If a component of a path is a file
name, it must be the last component", Microsoft, *Naming Files, Paths, and Namespaces*) **[read]**;
and a left-behind `\` carries no anchor, so it is harmless and idempotent. Measured shape:
`C:\…\vk_cookies__dir<rand>\owner.pid` → `***REDACTED***\owner.pid`.

**Why the positive `[a-z0-9_]` tail rather than a "Windows-forbidden-complement" class.** The
latter (`[^<>:"/\\|?*\s'…]`) is the set Microsoft forbids in a name **[read]**, and it is the
natural instinct — but it widens the tail to every legal filename character, including uppercase
and every Unicode letter, for a tail that `tempfile` draws from a **26+10+1 = 37-character ASCII
alphabet** **[exec]**. The positive class is strictly tighter on the only inputs the product can
produce.

##### `B4-R4` — case sensitivity: **no `re.IGNORECASE`**, on two independent grounds

1. **Every string this rule must match is built by this process from a frozen lowercase literal.**
   The three sinks receive child output; the artefact path they echo arrives via `--cookies
   <path>`, and the `path=` fields are `str(cookie_file)` — all derived from `_COOKIE_ARTIFACT_PREFIX`
   **[read]**. No code path lets a user choose the artefact name; `mkstemp`/`mkdtemp` are the only
   producers **[exec]**. So the case is known, exactly, and lower-case matching is complete.
2. **`re.IGNORECASE` widens a character class in a way that is documented and non-obvious.**
   "when the Unicode patterns `[a-z]` or `[A-Z]` are used in combination with the IGNORECASE flag,
   they will match the 52 ASCII letters and **4 additional non-ASCII letters**: 'İ' (U+0130),
   'ı' (U+0131), 'ſ' (U+017F) and 'K' (U+212A)" (`docs.python.org/3/library/re.html`, `re.I`)
   **[read]**. Measured **[exec]**: `re.compile(r"[a-z0-9_]+", re.IGNORECASE).fullmatch("K")` is
   `True` for all four. An `IGNORECASE` tail would therefore match a path component containing a
   Kelvin sign — and `IGNORECASE` also matches `VK_COOKIES_A.cookies.txt`, which is a *broader*
   false-positive surface bought for **zero measured coverage gain**.
   **[uncertain]** — whether yt-dlp or ffmpeg ever echo a path with re-cased components was not
   measured; plan 11's skip S-4. It is not reachable through the product's own argv, and the cost
   of being wrong is a *missed* match, not a leak.

##### `B4-R5` — **rule order is load-bearing**; `B4-A9`'s "ordering is not a hazard" is corrected

`B4-A9` measured ordering against artefact-free oracles and concluded it is not a hazard. That is
true only for those inputs. Measured **[exec]** with the artefact path **inside** a URL:

| input | URL first (**chosen**) | artefact first |
|---|---|---|
| `GET https://cdn.example.com/proxy?p=C:/…/vk_cookies_x.cookies.txt` | `GET https://cdn.example.com/***REDACTED***` — **host kept** | `GET ***REDACTED***` — **host lost** |

The greedy lead clause spans the whole whitespace-delimited run, so run artefact-first and the
lead swallows `https://cdn.example.com/proxy?p=C:/Users/…`, destroying the host visibility that
`AC-5` requires and that makes `download_failed` readable. **URL-first is mandatory and needs a
named test** — this is a regression no existing oracle can see, because every current test input
either has no artefact or no URL containing one.

##### `B4-R6` — idempotency: proof by construction, then measurement

**By construction.** (a) Every rule's replacement is the constant `***REDACTED***`, which contains
no `vk_cookies_`, so no rule can re-match its own or a sibling's output **[read]**. (b) The
left guard `(?<![^\s'\"<>])` is unsatisfiable by that replacement, so a substitution cannot create a
new match start (`B4-R3`). (c) `re.sub` replaces "the leftmost non-overlapping occurrences", a
single left-to-right pass, so a match can never straddle a replacement it just made
(`docs.python.org/3/library/re.html`) **[read]**. (d) The URL rule's own output re-emits
`scheme://host/`, so it reproduces itself — the property `B4-A9` already established.

**By measurement [exec].** `***REDACTED***` matches **no** rule (`FILE_RULE.search(MARKER)`,
`DIR_RULE.search(MARKER)`, `_URL_REGEX.search(MARKER)` all `None`), while
`re.match(r"[^\s'\"]+", MARKER)` is truthy — so safety is **not** free, exactly as `B4-A9` said.
Fixed-point violations: **0 / 400 000** random cases (alphabet includes `\ / : . _ * ' " < >` and
the literals), **0 / 16 777 216** exhaustive 6-character strings over `v k _ . \ / : a 0 1 9 * ' " < >`,
and **0 expansions** (`len(f(x)) > len(x)` never occurs). Adversarial corpus, `d1` = pass-1 length
delta, `d2` = pass-2 delta; **a rule with `d2 != 0` is a failure**:

| case | fp | `d1` | `d2` | unchanged vs today |
|---|---|---|---|---|
| signed CDN URL **and** artefact path, one line | yes | −96 | **0** | no |
| nested `…\vk_cookies__dir<rand>\vk_cookies_<rand>.cookies.txt` | yes | −78 | **0** | no |
| artefact path + `)` `,` `'` `"` `;` adjacency | yes | −203 | **0** | no |
| artefact path at the very start of a line | yes | −78 | **0** | no |
| artefact path at the very end of a line | yes | −78 | **0** | no |
| forward-slash separators throughout | yes | −124 | **0** | no |
| benign line mentioning "cookies", no artefact shape | yes | 0 | **0** | **yes (byte-identical)** |
| text already containing `***REDACTED***` | yes | −78 | **0** | no |
| artefact path immediately adjacent to a marker | yes | −92 | **0** | no |
| `***REDACTED***` alone | yes | 0 | **0** | **yes** |
| `…\vk_cookies__dir<rand>\owner.pid` | yes | −46 | **0** | no |
| unquoted `key=value` (`path=…`) | yes | −83 | **0** | no |
| URL whose query carries the artefact path | yes | −86 | **0** | **yes (URL rule already won)** |
| user folder `vk_cookies_videos`, `vk_cookies__downloads` | yes | 0 | **0** | **yes (not matched)** |
| bare `vk_cookies_` mention, no artefact name | yes | 0 | **0** | **yes (not matched)** |
| mid-token substring `foovk_cookies_a.cookies.txt` | yes | 0 | **0** | **yes (not matched)** |

**Every case's pass-1 output fed back in is byte-identical (`d2 = 0` everywhere).**

**Accepted collateral, stated rather than hidden [exec].** An unquoted `key=value` run collapses
whole: `path=C:\…\vk_cookies_x.cookies.txt` → `***REDACTED***`, so the `path` **key** is consumed
along with the identifying parent. This is the price of consuming the parent, and it does **not**
reach production: `B6` applies the transform to structlog *dict values*, and a value never
contains `key=`; the three child-output sinks receive whitespace-delimited argv
(`yt-dlp --cookies <path> --no-warnings …` → `yt-dlp --cookies ***REDACTED*** --no-warnings …`
**[exec]**). Quoted and JSON renderings keep the key: `path='***REDACTED***'`,
`{"path": "***REDACTED***", "error": "boom"}`.

**Second accepted residual [exec].** The run-start guard buys idempotency with a coverage gap:
in a *separator-less* concatenation such as `dir\vk_cookies_a.cookies.txtvk_cookies_b.cookies.txt`
the second name is left unredacted (`***REDACTED***vk_cookies_b.cookies.txt`) — and stays
unredacted, which is what makes it a fixed point. Unreachable from the product: every value that
reaches a sink is either a `str(Path)` built from `mkstemp`/`mkdtemp` (always preceded by a
separator or a run start) or whitespace-delimited child argv. What could remain is a **bare
artefact basename with no path**, which is already inside the accepted disclosure of the default
replacement (`B4-R8`).

##### `B4-R7` — interaction with the 200-character truncation: monotone non-expansion makes it safe

The replacement is 14 characters and every artefact match is at least
`vk_cookies__dir<rand>` (18) or `vk_cookies_<rand>.cookies.txt` (25), and the lead clause only ever
**adds characters that are then removed**. So this rule is **monotonically non-expanding**, which is
the property the two `ffmpeg_utils` sinks need: `sanitize_text_for_log(x)[:200]` can only get
*shorter or stay equal* **[exec]** — measured `len` today 131 → new 53 on
`<artefact> https://cdn.example.com/s.ts?t=SECRET`, and 200 → 185 when the artefact sits inside
the window. Consequences, all measured **[exec]**:

- **No leak can be moved into view.** Sanitisation runs on the whole string before the cut, so any
  secret inside the first 200 characters of `f(x)` was inside the sanitised region and survived
  because *no rule matched it* — a property this rule does not change.
- **No host can be pushed out of view.** Shrinking brings later content *earlier*, so it can only
  add redaction coverage. An **expanding** rule (a parent-preserving replacement) would do the
  opposite, which is the concrete reason `B4-R8`'s replacement choice is load-bearing.
- `test_transform_before_truncate_proves_sanitize_order` still holds: input 226 chars, both today
  and new produce `len == 200` with `cdn.example.com` retained and `SECRET123` absent **[exec]**.
- `f(f(x))[:200] == f(x)[:200]` on all four probes **[exec]**.

##### `B4-R8` — replacement shape: recommend **whole token → `***REDACTED***`**; and §9 Q2's option **B is not implementable as written**

Measured **[exec]**: today's transform leaves `NMATVE~1` (the username-bearing temp root,
`C:\Users\NMATVE~1\AppData\Local\Temp`) in the output; the recommended rule does not. CWE-532 is
directly on point: "Logging sensitive user data, **full path names**, or system information often
provides attackers with an additional, less-protected path to acquiring the information" **[read]**.

- **Whole token → `***REDACTED***` — recommended, and it is the §9 Q2 default (option A).** Costs:
  the operator cannot correlate the record with a run. That is cheap here, because the **record
  name** (`cookie_file_cleanup_failed`, `cookie_file_cleaned_up`) already says which artefact was
  involved, and the basename `vk_cookies_<8 random chars>` carries zero triage information
  (`B4-A11`). It is the only option whose idempotency proof is immediate, and the only one that
  removes the username, the temp root and the random tails in one step.
- **§9 Q2's recommended option B ("keep the folder, remove the file name") is not available.** The
  "folder" here is `C:\Users\<name>\AppData\Local\Temp` — **username-bearing** — and the product's
  own artefact folder is `vk_cookies__dir<rand>`, i.e. the *other* artefact's anchor, which the dir
  rule would re-match (`B4-A9a`). Keeping it either re-discloses the account name or forfeits
  idempotency. **§9 Q2 must be re-opened on this point**; this is its most consequential input and
  the plan's own recommendation is unimplementable without giving up the CWE-532 property.
- **Preserve the suffix (`***REDACTED***.cookies.txt`)** — the only fragment with real triage
  value, and it cannot re-match a prefix-anchored rule. Its cost: a second redaction-bearing token
  in the vocabulary, which `B6` will stamp onto *every* record it processes, plus one more entry
  in the marker-is-a-fixed-point test. Surface it as §9 Q2's revised option; do not implement it.
- **Preserve a basename** — rejected: zero triage value, and a `vk_cookies_`-bearing basename
  re-matches its own rule.
- **Preserve the parent directory** — rejected: it is the other artefact, and its own parent is the
  username-bearing root.

**Implementation note [exec]:** the replacement must be the **literal constant**, not text derived
from the match — `re.sub` processes backslash escapes in a *string* replacement
(`docs.python.org/3/library/re.html`) **[read]**. `***REDACTED***` contains none, so a literal repl
is safe, and a derivation bug is a `re.error` at runtime (reproduced while measuring this report).
The URL rule's lambda form is untouched and `_strip_auth_params`'s behaviour is preserved exactly.

##### `B4-R9` — sources consulted

| Source | Used for | Confidence |
|---|---|---|
| `cwe.mitre.org/data/definitions/532.html` | "full path names" as a CWE-532 impact → redact the parent, not just the basename | HIGH **[read]** |
| `cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet` | "Data to exclude": session identification values, access tokens — must be "removed, masked, sanitized"; de-identification "where the individual's identity is not required" → whole-token default | HIGH **[read]** |
| `cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet` | secrets must "never be logged (must implement either an encryption or **masking** approach)" → reuse the existing marker vocabulary | HIGH **[read]** |
| `docs.python.org/3/library/re.html` — `(?<=...)`, `\b`, `re.sub`, `re.I`, `re.escape` | lookbehind is fixed-width-only (hence consuming the parent); `\b` is a `\w`/`\W` transition; `sub` replaces leftmost non-overlapping occurrences; `IGNORECASE` adds 4 non-ASCII letters | HIGH **[read]** |
| `learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file` | reserved characters `< > : " / \ | ? *`; "If a component of a path is a file name, it must be the last component" | HIGH **[read]** |
| `docs.github.com/…/secret-scanning-patterns` + `…/about-push-protection` | precision-over-recall as the operating principle: patterns are gated on "low false positive rate" to avoid blocking "when a result may be a false positive"; tightening via "additional match requirements" | MEDIUM **[read]** — industry practice, not a normative spec |
| `tempfile._RandomNameSequence` source, `inspect.getsource` | `characters = "abcdefghijklmnopqrstuvwxyz0123456789_"`, "eight characters long" | HIGH **[exec]** |
| `src/vkdownloader/services/ytdlp_downloader.py` constants + import graph | the three frozen strings; `utils/` never imports `services/` | HIGH **[read]** |

##### `B4-R10` — corrections to `B4-AUDIT` and to the `B4` block text

| # | Correction | Class |
|---|---|---|
| 1 | `B4-A9`'s "ordering is not a hazard" holds only for artefact-free inputs. **URL-first is mandatory**: artefact-first loses the host when the path is inside a URL (`B4-R5`). Needs a named test. | **[SPEC-DEVIATION]** mandatory |
| 2 | `B4-A10`'s "`test_filesystem_paths_are_not_redacted` … will fail under any rule broad enough to match its input" — **measured: it passes unchanged** under the recommended rule (its fictional `vkdownloader_cookies_` prefix is not a match, and the rule is suffix-keyed anyway). It must still be **re-aimed, but for truthfulness, not for green**: its docstring pins "filesystem paths pass through unchanged; only URLs are redacted", which becomes false. Recommended: re-aim at the **real** artefact shape plus the new behaviour, and keep a byte-identical negative case with a *benign* path (a user-chosen output path, e.g. `C:\Users\x\Videos\clip.mp4`). **All 16 existing cases pass unchanged — measured, not asserted** (`B4-R11`). | **[SPEC-DEVIATION]** mandatory |
| 3 | `B4-A9a`'s recommendation of a *single prefix-anchored* rule is **superseded**: a prefix-only rule matches a user-chosen folder `vk_cookies_videos`. Two suffix-keyed named rules are both safer and individually testable (`B4-R1`, `B4-R2`). | **[SPEC-DEVIATION]** |
| 4 | §9 **Q2's recommended option B is unimplementable** without re-disclosing the username (`B4-R8`). Q2 needs re-asking with this input. | decision input |
| 5 | `B4-A6`'s "`_COOKIE_ARTIFACT_SUFFIX` … cleanup tooling keys on" — half the claim becomes true; the "cleanup tooling" half must be dropped in the same commit. | `[DOC-UPDATE]` |
| 6 | `AC` needs: a marker-is-a-fixed-point case; a **real-artefact oracle** built from `_create_cookie_artifact_dir()` / `_create_temp_cookie_file()`; a URL-first-ordering case with the path inside a URL; the re-aimed `test_filesystem_paths_are_not_redacted`; a separator-less-concatenation case pinning the accepted residual; a `path=C:\…` case pinning the accepted key-consumption collateral. | `[BEST-PRACTICE]` |

##### `B4-R11` — measured baseline facts the Planner and Implementor need

- **All 16 cases in `tests/test_url_sanitizer.py` pass unchanged** under the recommended rule set,
  verified by executing `TestStripAuthParams` and `TestSanitizeTextForLog` against it in-process
  **[exec]** — 8 + 8, zero failures. This is stronger than plan 11's "four existing cases" and than
  `B4-A10`'s claim that one of them must be re-aimed to stay green.
- Real artefact shapes on this machine **[exec]**:
  file `C:\Users\NMATVE~1\AppData\Local\Temp\vk_cookies__dir<8>\vk_cookies_<8>.cookies.txt`;
  dir `C:\Users\NMATVE~1\AppData\Local\Temp\vk_cookies__dir<8>`. Both rules match the **full**
  path span, ending exactly at the artefact name.
- `***REDACTED***` matches `[^\s'"]+` but no rule **[exec]** — the load-bearing detail.
- No new file, no new dependency, `utils/__init__.py` untouched, `sanitize_url_for_log` and
  `_strip_auth_params` behaviour unchanged, `_URL_REGEX` keeps its URL-only scope.

##### `B4-R12` — risks this design carries

1. **Silent coverage loss if `tempfile` changes its name alphabet.** Mitigated only by the
   behavioural oracle (`B4-R1`); a constant-equality test cannot catch it. This is the one failure
   mode with no error and no test — the same class as `R1-R4`'s sweep-`startswith` warning.
2. **The frozen literals are now duplicated in two modules**, and `utils/` cannot import them from
   `services/`. The behavioural oracle is the mitigation; the comment must name both sources.
3. **A future rule author re-introducing `\b`** would silently break idempotency for `B5` and `B6`,
   which both apply the transform twice by design. The fuzz oracle is the mitigation, and the law
   in `B4-R3` belongs in the module comment.
4. **Accepted information loss**: the artefact basename, and the record key on an unquoted
   `key=value` child line. Both measured, both bounded, neither reachable through `B6`'s dict-value
   path.
5. **Accepted residual**: separator-less concatenations are not redacted past the first name.
6. **`cookie_file_cleaned_up`'s `path=` is not routed through this transform at all today** — it is
   product-generated text, not child output, and reaches the log unsanitised. This rule makes it
   *matchable*; `B6` is what actually routes it. `B4` alone does not close that instance, and the
   commit message should say so rather than implying otherwise.

#### `B4-DESIGN` — implementor task (Planner)

The design is **settled** by `B4-RESEARCH` (`B4-R1`…`B4-R12`). Implement it as written: do not
re-derive the rule set, do not widen it, do not "improve" the left boundary. The Research
**supersedes three `B4-AUDIT` statements** — rule **order** (URL-first is mandatory, not cosmetic),
the fate of `test_filesystem_paths_are_not_redacted` (**passes unchanged**; re-aim it for
*truthfulness*, not for green), and the case count (**8**, of which **7** must stay unchanged).

````yaml
id: EB-B4
title: "Widen sanitize_text_for_log to redact the product's own cookie-artefact paths"
priority: medium
depends_on: []

source_reference: .ai/plans/17-credentials-secrets-audit-fixes-execution.md
source_section: "`B4` block; `#### B4-RESEARCH` (`B4-R1`…`B4-R12`) supersedes `B4-AUDIT` on rule order, the re-aimed test, and the case count"
source_file: .ai/plans/11-credentials-secrets-audit-fixes.md
source_blocks: ["B4 — Widen the transform so the redaction claim is true (`SEC-006`)"]
source_task: "`T-B4` (§6) and §3.4; the §7 `SEC-006` row"

description: >
  sanitize_text_for_log matches https?:// and nothing else, so the product's own cookie
  artefact path - C:\Users\<name>\AppData\Local\Temp\vk_cookies__dir<rand>\
  vk_cookies_<rand>.cookies.txt - passes through byte-identical while the module comments
  claim the tooling keys on that suffix. D-5 is closed to Alt A (B4-A8: no sink is
  measured to receive a Cookie: header from a child). B4-R1 settles the shape: two named,
  suffix-keyed rules applied AFTER the URL rule, each replacing the whole matched token -
  the parent path included - with ***REDACTED***. Idempotency is load-bearing, not
  cosmetic: B5 and B6 both apply the transform twice by design, and two of the three
  existing call sites already do today.

goals:
  - An artefact path in sanitised text is redacted: both the cookie_file_cleanup_failed and cookie_file_cleaned_up `path=` shapes, the artefact directory shape, and the nested file-inside-directory shape.
  - The URL rule runs FIRST, so an artefact path inside a URL costs the path, never the host.
  - f(f(x)) == f(x) for every rule, including text that already contains ***REDACTED***, and ***REDACTED*** matches no rule.
  - Text with no artefact shape stays byte-identical; a user-chosen folder that merely resembles the prefix is NOT redacted.
  - The docstring and the `_COOKIE_ARTIFACT_SUFFIX` comment claim only what is true.

files:
  - path: src/vkdownloader/utils/url_sanitizer.py
    targets:
      - {type: module_constant, name: _URL_REGEX, action: no-change}
      - {type: constant, name: _ARTEFACT_LEAD, action: add}
      - {type: constant, name: _COOKIE_FILE_ARTEFACT_REGEX, action: add}
      - {type: constant, name: _COOKIE_DIR_ARTEFACT_REGEX, action: add}
      - {type: function, name: sanitize_text_for_log, action: modify}
      - {type: function, name: _strip_auth_params, action: no-change}
      - {type: function, name: sanitize_url_for_log, action: no-change}
      - {type: module_all, name: __all__, action: no-change}
    semantic_anchors:
      insert_after:
        type: module_constant
        value: _URL_REGEX
      insert_before:
        type: function
        value: _strip_auth_params

  - path: tests/test_url_sanitizer.py
    targets:
      - {type: class, name: TestSanitizeTextForLog, action: modify}
      - {type: method, name: test_filesystem_paths_are_not_redacted, action: rewrite-for-truthfulness}
      - {type: class, name: TestArtefactAlphabetOracle, action: add}
    semantic_anchors:
      insert_after:
        type: method
        value: test_preserves_plaintext_merge_failure_text

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - {type: comment, name: "the comment block above _COOKIE_ARTIFACT_PREFIX", action: reword}
      - {type: module_constant, name: _COOKIE_ARTIFACT_PREFIX, action: no-change}
      - {type: module_constant, name: _COOKIE_ARTIFACT_SUFFIX, action: no-change}
      - {type: module_constant, name: _ARTEFACT_DIR_SUFFIX, action: no-change}
      - {type: function, name: _download_with_ytdlp, action: no-change}
    semantic_anchors:
      insert_before:
        type: module_constant
        value: _COOKIE_ARTIFACT_PREFIX

changes:

  - action: add_code
    description: >
      Add three module-level constants to url_sanitizer.py after `_URL_REGEX`, plus a comment
      block recording WHY each element exists. This step alone changes no behaviour, so the
      tree stays green.
    code_hint: |
      _ARTEFACT_LEAD = r"(?<![^\s'\"<>])(?:[^\s'\"<>]*[\\/])?"
      _COOKIE_FILE_ARTEFACT_REGEX = re.compile(
          _ARTEFACT_LEAD + r"vk_cookies_[a-z0-9_]+\.cookies\.txt"
      )
      _COOKIE_DIR_ARTEFACT_REGEX = re.compile(
          _ARTEFACT_LEAD + r"vk_cookies__dir[a-z0-9_]+"
      )
    comment_must_state:
      - "The literals are duplicated from `services/ytdlp_downloader._COOKIE_ARTIFACT_PREFIX` / `_COOKIE_ARTIFACT_SUFFIX` / `_ARTEFACT_DIR_SUFFIX`; `utils/` must not import `services/` (layer rule, and it would invert the import order)."
      - "The law: a rule's left boundary must be a predicate its own replacement can never satisfy. `***REDACTED***` ends in `*`, a non-word character, so a `\\b` guard would manufacture a boundary on the second pass (measured 3 fixed-point violations in 400 000). `*` is inside the excluded set, so `(?<![^\\s'\"<>])` is unsatisfiable by the marker and measures 0."
      - "The parent is CONSUMED by the optional greedy lead, not asserted by lookbehind: a variable-length lookbehind is illegal, and consuming the parent is what removes the username-bearing temp root (`C:\\Users\\<name>\\AppData\\Local\\Temp`, CWE-532)."
      - "No `re.IGNORECASE`: every matched string is built from a frozen lowercase literal, and IGNORECASE widens `[a-z]` with U+0130/U+0131/U+017F/U+212A for zero measured coverage gain."
      - "The tail is `[a-z0-9_]+`, not `{8}`: `tempfile._RandomNameSequence.characters` is a CPython internal whose length is not contractual."
      - "The match ends at the artefact NAME; a trailing separator is never consumed, so the marker cannot fuse to the next path component (`***REDACTED***\\owner.pid`)."

  - action: update_code
    description: >
      Rewrite `sanitize_text_for_log`'s body as three substitutions in a fixed order: URL FIRST,
      then the file artefact, then the directory artefact. The order is mandatory - artefact-first
      on a URL-shaped input swallows the whole run including the host and yields `GET ***REDACTED***`.
    code_hint: |
      text = _URL_REGEX.sub(lambda m: _strip_auth_params(m.group(0)), text)
      text = _COOKIE_FILE_ARTEFACT_REGEX.sub("***REDACTED***", text)
      text = _COOKIE_DIR_ARTEFACT_REGEX.sub("***REDACTED***", text)
      return text

  - action: update_code
    description: >
      Correct `sanitize_text_for_log`'s docstring - the remaining documentation duty. State the
      shapes that ARE matched (URLs; `vk_cookies_<tail>.cookies.txt`; `vk_cookies__dir<tail>`; the
      parent path is consumed with them), the shapes that are NOT (`Cookie:` / `Set-Cookie:` header
      values - D-5 closed to Alt A per B4-A8; bare `name=value` pairs; user-chosen output paths),
      the URL-first ordering, and that an unquoted `key=value` run carrying an artefact collapses
      whole because the key is consumed with the identifying parent. Also fix the pre-existing
      inaccuracy: `Returns:` claims `scheme://host/***REDACTED***/` with a trailing slash the code
      does not emit. Keep it concise - a claim nobody can check is the defect SEC-006 names.

  - action: add_code
    description: >
      Rewrite `test_filesystem_paths_are_not_redacted` in place, keeping its name. Its docstring
      ("filesystem paths pass through unchanged; only URLs are redacted") becomes FALSE, and its
      fictional `/tmp/vkdownloader_cookies_8u3x.txt` prefix tests a name the product never emits.
      Its new job is the negative half: user-chosen paths that must stay byte-identical - a
      download output path, and folders that merely resemble the artefact prefix. Measured: the
      case PASSES UNCHANGED, so do not rewrite it to chase a failure that does not occur and do not
      delete it. The other 7 cases of the class (4 original, 3 from `486bfd9`) and
      `TestStripAuthParams`'s 8 must pass with byte-identical bodies.

  - action: add_code
    description: >
      Add the required cases to `TestSanitizeTextForLog` (see `required_tests`). Each case is
      single-purpose and named for the property it pins. No new skips, no platform guards.

  - action: add_code
    description: >
      Add a new class `TestArtefactAlphabetOracle` at module scope, AFTER `TestSanitizeTextForLog`.
      This is the oracle that does not exist yet and it closes the only silent-failure mode in the
      design (B4-R12.1): a literal-keyed rule whose source of truth changes stops matching and
      nothing else fails. The literals cannot be imported from `services/` into `utils/`, so the
      oracle must build REAL artefacts with `_create_cookie_artifact_dir()` /
      `_create_temp_cookie_file()` and assert the transform redacts them, plus a negative case with
      a similarly-shaped NON-artefact path that must stay byte-identical. Clean up in `finally`
      through the product's own helpers (`path.unlink(missing_ok=True)` then
      `_remove_cookie_artifact_dir(path.parent)`), matching the existing pattern in
      `tests/test_cookies.py`, so nothing is left behind in the temp root on Windows.

  - action: update_code
    description: >
      Reword ONE comment in `services/ytdlp_downloader.py`: the block above
      `_COOKIE_ARTIFACT_PREFIX` says the suffix "is what the operator-facing redaction and cleanup
      tooling keys on". After this block the redaction tooling demonstrably keys on it; the
      "cleanup tooling" half never existed (B4-A6). Name the redaction rule only. No constant
      value changes.

implementation_sequence:
  - "1. Add the three constants and the comment block. No behaviour change; the 16 existing cases stay green."
  - "2. Rewrite `sanitize_text_for_log`'s body (URL first). All 16 existing cases still pass - measured, B4-R11. Run them; do NOT modify a test to accommodate a failure that should not occur."
  - "3. Re-aim `test_filesystem_paths_are_not_redacted`."
  - "4. Add the new cases in `TestSanitizeTextForLog`."
  - "5. Add `TestArtefactAlphabetOracle`."
  - "6. Reword the `_COOKIE_ARTIFACT_SUFFIX` comment block."
  - "7. Run the gates; make ONE commit. Production code lands before the tests that pin it, so every test edit is green on arrival and no intermediate state needs a fix-up commit."

architectural_constraints:
  - "No new file, so `tests/test_packaging.py`'s manifests need no edit (14 passed must hold)."
  - "`utils/__init__.py` NO change; `sanitize_text_for_log` stays deliberately unexported (`T-B4` step 9)."
  - "Module `__all__` unchanged - the new names are private."
  - "`_URL_REGEX` keeps its URL-only scope; `sanitize_url_for_log` stays a public alias; `_strip_auth_params`'s behaviour is byte-identical."
  - "The replacement is the LITERAL `***REDACTED***`, never derived from the match (`re.sub` interprets backslash escapes in a string replacement). Do not introduce a second marker such as `***REDACTED***.cookies.txt`: `B6` would stamp it on every record for no security gain."
  - "Rules stay additive and literal-anchored: no token-wise fallback, no rule that can match `*`, no `Cookie:` rule (D-5 = Alt A, B4-A8)."
  - "Do NOT touch `services/ffmpeg_utils.py`'s two sinks - already pre-sanitised by `486bfd9` and owned by plan-10 `B14`. Their `[:200]` truncation stays safe because the new rules are monotonically non-expanding (B4-R7)."
  - "Do NOT re-litigate the `# SEC-002:` comment above `error_msg = sanitize_text_for_log(error_msg)` - `09f1b10` already corrected it."
  - "Three call sites exist, all passing raw child output: `_download_with_ytdlp`, `_merge_batch_segments`, `_perform_final_merge`. None needs an edit. No new dependency."

required_tests:
  unchanged_must_pass:
    - "TestStripAuthParams - all 8 cases, bodies untouched."
    - "TestSanitizeTextForLog::test_redacts_url_in_text, ::test_redacts_multiple_urls_in_text, ::test_preserves_text_without_urls, ::test_redacts_url_in_yt_dlp_output - the 4 original cases."
    - "TestSanitizeTextForLog::test_transform_before_truncate_proves_sanitize_order, ::test_redacts_signed_cdn_url_in_merge_failure_text, ::test_preserves_plaintext_merge_failure_text - the 3 from `486bfd9`."
  re_aimed:
    - name: test_filesystem_paths_are_not_redacted
      asserts: >
        A user-chosen output path (`C:\Users\x\Videos\clip.mp4`) and user folders resembling the
        artefact prefix (`...\vk_cookies_videos\clip.mp4`, `...\vk_cookies__downloads\clip.mp4`) are
        byte-identical. Its docstring states the REAL boundary: URLs and the product's own
        `vk_cookies_` artefact file/directory names are redacted; everything else passes through.
  new_cases:
    - name: test_redacts_cookie_artefact_file_path
      asserts: "Both records' real `path=` shape, quoted: `path='C:\\Users\\x\\AppData\\Local\\Temp\\vk_cookies__dirabc12345\\vk_cookies_q1w2e3r4.cookies.txt'` - no `vk_cookies_`, no `AppData`, no `Users`; the surrounding quotes and the `path=` key survive."
    - name: test_redacts_cookie_artefact_directory_shape
      asserts: "`...\\vk_cookies__dir9lfm4h4w4\\owner.pid` yields exactly `***REDACTED***\\owner.pid`. The trailing separator is NOT consumed - the marker must not fuse to the next component."
    - name: test_url_rule_runs_before_artefact_rules
      asserts: "`GET https://cdn.example.com/proxy?p=C:/Users/x/Temp/vk_cookies_a.cookies.txt` - `cdn.example.com` retained, `vk_cookies_` absent, exactly one `***REDACTED***`. This is the mandatory URL-first oracle (artefact-first yields `GET ***REDACTED***`, losing the host)."
    - name: test_glued_artefact_names_do_not_grow_on_a_second_pass
      asserts: "`dir\\vk_cookies_a.cookies.txtvk_cookies_b.cookies.txt` - the first name is consumed in ONE pass, exactly one `***REDACTED***`, and `sanitize_text_for_log(result) == result`. Docstring records the accepted residual (the separator-less second name stays unredacted; that non-redaction IS the fixed point) and that a `\\b` guard fails this case."
    - name: test_nested_directory_and_file_collapse_to_one_marker
      asserts: "The full nested path yields exactly `***REDACTED***` - one marker, not two (the file rule runs before the dir rule)."
    - name: test_artefact_path_with_quote_and_punctuation_adjacency
      asserts: "`(<artefact>)`, `'<artefact>'`, `\"<artefact>\"` each collapse to `***REDACTED***` with the wrapper characters intact."
    - name: test_artefact_path_at_line_start_and_line_end
      asserts: "Both positions in one multi-line input are redacted; the surrounding lines are untouched."
    - name: test_forward_slash_separators_are_matched
      asserts: "The file and directory shapes with `/` separators are redacted identically."
    - name: test_benign_line_mentioning_cookies_is_byte_identical
      asserts: "A plain 'cookie file missing' line and a `Cookie: a=b` header line are byte-identical - documentation-as-test for the Alt A uncovered shape (B4-A8)."
    - name: test_user_folder_resembling_the_prefix_is_not_redacted
      asserts: "`vk_cookies_videos`, `vk_cookies__downloads`, a bare `vk_cookies_` mention, and the mid-token `foovk_cookies_a.cookies.txt` are byte-identical - the over-broad-redaction regression suffix keying prevents."
    - name: test_unquoted_key_value_run_collapses_whole
      asserts: "`path=C:\\...\\vk_cookies_x.cookies.txt` yields `***REDACTED***`. Pins the accepted collateral: the key is consumed with the identifying parent. Docstring notes it does not reach `B6`'s dict-value path."
    - name: test_double_application_equals_single_for_every_rule
      asserts: "Over file artefact, dir artefact, signed URL, URL containing an artefact, unquoted `key=value`, and `***REDACTED***` alone: `f(f(x)) == f(x)`."
    - name: test_marker_matches_no_rule
      asserts: "`sanitize_text_for_log('***REDACTED***') == '***REDACTED***'` and each new pattern's `.search('***REDACTED***')` is None. Docstring notes the marker DOES match a permissive `[^\s'\"]+` run class, which is exactly why the left boundary must be one the marker cannot satisfy."
  new_class_TestArtefactAlphabetOracle:
    - name: test_real_artefact_directory_is_redacted
      asserts: "`_create_cookie_artifact_dir()` - assert `vk_cookies_` IS in `str(dir)` (non-vacuous), then `sanitize_text_for_log(str(dir)) == '***REDACTED***'`. Cleanup in `finally` via `_remove_cookie_artifact_dir`."
    - name: test_real_artefact_file_is_redacted
      asserts: "`_create_temp_cookie_file('vk=test')` - assert `vk_cookies_` IS in `str(path)`, then the transform yields `***REDACTED***` with no `Users` / `AppData`. Cleanup in `finally`: unlink, then `_remove_cookie_artifact_dir(path.parent)`."
    - name: test_similarly_shaped_non_artefact_path_is_byte_identical
      asserts: "`C:\\Users\\x\\Videos\\cookies_archive.txt`, `C:\\Users\\x\\Videos\\vk_cookies_archive.cookies.txt.bak`, and the user-folder shapes stay byte-identical. Do NOT use a `.cookies.txt` name under a `vk_cookies_` stem in this negative case - that IS an artefact match."
    - name: test_artefact_tail_uses_lowercase_ascii_digits_underscore
      asserts: "[optional, second line of defence] The created tail's characters are a subset of lowercase ASCII + digits + `_`, so an alphabet change fails here with a clear message as well as in the cases above."
  windows_requirement: >
    Every new test executes on Windows: no `pytest.mark.skipif(sys.platform...)`, no POSIX-only
    assertions, no new skips. Artefact creation goes through `tempfile`, as existing tests already do.

acceptance_criteria:
  - id: AC-1
    criterion: An artefact path in free text is redacted - the cookie_file_cleanup_failed file shape, the cookie_file_cleaned_up file shape, the directory shape, and the nested file-inside-directory shape.
    verified_by: new cases in TestSanitizeTextForLog
  - id: AC-2
    criterion: Text with no matched shape is byte-identical, including benign lines that mention "cookies", `Cookie:` headers, user output paths, and folders resembling the artefact prefix.
    verified_by: the new negative cases
  - id: AC-3
    criterion: The URL rule runs first: with an artefact path inside a URL the host survives and the path does not.
    verified_by: test_url_rule_runs_before_artefact_rules
  - id: AC-4
    criterion: Double application equals single application for every rule, and `***REDACTED***` matches no rule - a hard criterion, since B5 and B6 apply the transform twice by design.
    verified_by: test_double_application_equals_single_for_every_rule, test_marker_matches_no_rule
  - id: AC-5
    criterion: `test_filesystem_paths_are_not_redacted` is re-aimed for truthfulness (name kept, negative-only, real docstring); the other 7 cases of the class and TestStripAuthParams' 8 pass with byte-identical bodies.
    verified_by: uv run pytest tests/test_url_sanitizer.py -q
  - id: AC-6
    criterion: The behavioural alphabet oracle builds a real artefact and asserts it is redacted, plus a similarly-shaped non-artefact path that stays byte-identical.
    verified_by: TestArtefactAlphabetOracle
  - id: AC-7
    criterion: The `sanitize_text_for_log` docstring states the matched and unmatched shapes (naming `Cookie:` / `Set-Cookie:` as uncovered) and no longer claims a trailing slash the code does not emit.
    verified_by: review
  - id: AC-8
    criterion: `_URL_REGEX` keeps its URL-only scope; `_strip_auth_params` and `sanitize_url_for_log` are behaviourally unchanged; `utils/__init__.py` and the module `__all__` are untouched.
    verified_by: review
  - id: AC-9
    criterion: The `_COOKIE_ARTIFACT_SUFFIX` comment names the redaction rule and no longer claims cleanup tooling.
    verified_by: review
  - id: AC-10
    criterion: Gates green (see `gates`).
    verified_by: the gate commands

gates:
  - "uv run pytest -q - full suite green; total skips NOT above 6 (3 D-11 POSIX-permission + 3 pre-existing killpg)."
  - "uv run mypy src - clean."
  - "uv run ruff check src tests - clean."
  - "uv run ruff format --check src tests - clean."
  - "uv run mypy src tests - error count NOT above 93."
  - "uv run pytest tests/test_packaging.py -q - 14 passed."
  - "uv run pytest tests/test_url_sanitizer.py -q - green, zero skips, every new test executed."

commit_shape:
  subject: "fix(logging): redact the product's own artefact paths in sanitised child output"
  count: 1
  body_must_record:
    - "The two named suffix-keyed rules and the mandatory URL-first ordering, with the `GET ***REDACTED***` host-loss counterexample."
    - "The left-boundary law, and that `\\b` was rejected (measured 3 fixed-point violations in 400 000) in favour of `(?<![^\\s'\"<>])` (0)."
    - "Suffix keying, and the `vk_cookies_videos` user-folder regression it avoids."
    - "`D-5` resolved to Alt A (B4-A8, measured on three grounds)."
    - "The re-aimed `test_filesystem_paths_are_not_redacted` and its reason; the other 7 cases are unchanged and 16/16 pass."
    - "The accepted residuals: separator-less concatenation, and the unquoted `key=value` key consumption."
    - "That `cookie_file_cleaned_up`'s `path=` is NOT routed through this transform today - this block makes it matchable; `B6` routes it (B4-R12.6)."
    - "That `services/ffmpeg_utils.py`'s two sinks are untouched (plan-10 `B14`'s), and that the new rules are monotonically non-expanding so the existing `[:200]` truncation stays safe (B4-R7)."

staging:
  - "Explicit paths only. Never `git add -A`, `git add .`, or `git add -u`."
  - "git add src/vkdownloader/utils/url_sanitizer.py tests/test_url_sanitizer.py"
  - "git add src/vkdownloader/services/ytdlp_downloader.py - only if that comment was actually reworded."
  - "Never amend, force-push, `git reset`, or `git checkout`."
  - "The working tree carries unrelated modified and untracked files at baseline; none may enter this commit."
````

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

#### `B5-AUDIT` — block-`B5` audit findings (Auditor; at `dfcf326`, with `B4` = `ab1057e`)

**`B5-A0` — `D-10`: `OUT-007` has NOT landed. The block keeps plan 11's shape.** [verified-by-reading + verified-by-execution]
No per-line record for non-progress child output exists anywhere in `src/`: the records on this path are `ytdlp_progress_suppressed` (progress only, `echo=False`), `ytdlp_reader_line_overrun`, `subprocess_reader_failed`, `download_failed`. `_echo_ytdlp_line` still holds a live `sys.stderr.write(line)` on its non-progress branch, and its `echo=False` branch `return`s without logging a non-progress line. `OUT-007` is plan 13's `B7`, sequenced **strictly after** plan 11 `B5`. → the transform goes on **what reaches `sys.stderr`**, not on a record field; `B6`'s idempotency criterion is not exercised by `B5`.

**1 · The echo path.** [verified-by-reading] `_echo_ytdlp_line(line, *, echo=True)`: gate `if not echo:` → `_parse_ytdlp_progress(line)`; on a ratio, `logger.debug("ytdlp_progress_suppressed", downloaded=…, total=…)`; then `return` — nothing written, not even a flush. Write branches: `if _is_ytdlp_progress_line(line)` → `text = line.rstrip("\n\r")`, `width = shutil.get_terminal_size((80, 24)).columns`, `sys.stderr.write("\r" + text.ljust(width)[:width] + "\r")` + `flush()`; `else` → `sys.stderr.write(line)` + `flush()`. The docstring describes the `\r` rewrite and the `echo=False` suppression, and **no transform**.
**Predicate, stated plainly:** the write-branch predicate is **`_is_ytdlp_progress_line`**; **`_parse_ytdlp_progress` is on the `echo=False` branch** (and again inside `_monitor_progress`). Plan 11 §3.5's correction is right; this block's item 2 matches the tree.

**2 · `echo` reachability — `B5-A1` (HIGH). Plan 11 §3.5's "batch mode never reaches this sink" is FALSE.** [verified-by-reading + verified-by-execution]
Every setter of `echo` in `src/`: `batch_downloader._download_single` (`echo = not reporter.is_enabled`, passed to `download_video`); then pass-throughs `downloader.download_video(echo=True)` → `perform_download(echo=True)` → both `download_with_ytdlp_with_resume_fallback(echo=echo)` arms → `_download_with_ytdlp(echo=True)`. `_run_batch_with_progress` **always** constructs a `RichProgressReporter`, so `reporter is not None` always — but `RichProgressReporter.is_enabled` falls back to `sys.stderr.isatty()`, so **batch mode on a non-TTY stderr sets `echo=True` and reaches the sink** (CI, `> file`, pipe, `CliRunner`). Proof: live test `test_batch_echo_not_suppressed_when_reporter_disabled` asserts `call.kwargs["echo"] is True`. Live: single-download `cli.py` passes no `echo`, so `echo=True` always. Not live: batch under a TTY rich display (`echo=False`). **No undiscovered `echo=True` outside these two paths.** `[SPEC-DEVIATION]` plan 11 §3.5 reachability correction 1 is wrong and §B5 inherits it silently; correcting it **widens** the block's value, because redirected output is the capture-prone case.

**3 · `output_chunks` must stay raw — `B5-A2`.** [verified-by-reading] The decoded line serves **two** purposes at both call sites in `_monitor_progress`/`_drain_output` — `_echo_ytdlp_line(decoded, echo=echo)` and `_retain_transcript_line(output_chunks, line)` — plus a **third** in `_monitor_progress`: `_parse_ytdlp_progress(decoded)` → `progress_callback`. The buffer's **only** consumer is `download_failed`, which already applies `sanitize_text_for_log` at its own call site. Transforming at the call site would (i) stop the buffer being the child's bytes: the reader decodes with `errors="replace"` and the consumer decodes strictly, so a decode/re-encode round-trip permanently substitutes U+FFFD for undecodable bytes — the fidelity TRN-011 exists for; (ii) make `_MAX_CHILD_OUTPUT_BYTES` bound redacted text rather than bytes read; (iii) duplicate `B6`'s central processor, which owns `download_failed.error`.

**4 · `iter_process_lines` — contract unchanged.** [verified-by-reading] `services/ffmpeg_utils.py::iter_process_lines` is an `AsyncIterator[bytes]`, docstring "Yields: Raw ``bytes`` lines", no transform. `B5` must not touch it (plan 11 §4.3 row 14 lists it as permanent product surface).

**5 · `subprocess_reader_failed` is NOT in the drain loop — `B5-A3`.** [verified-by-reading] It lives in `_await_first_and_cancel_others` (called only from `_download_with_ytdlp`, twice): level ERROR, fields `error=str(exc)`, exception retrieved and never re-raised. The drain loops' own arm is `except DownloadError` → `ytdlp_reader_line_overrun` (`url`, `pid`, `error`). `B5` touches neither; `B6` covers `subprocess_reader_failed.error` through the pipeline. Pinned by `test_reader_task_failure_emits_record` (exactly 1), `test_normal_completion_emits_no_record`, `test_cancelled_pending_task_emits_no_record`, and `test_reader_line_overrun_recorded_when_no_progress_callback` (0).

**6 · `D-6` — the hazard is theoretical, not real.** [verified-by-execution] All seven real yt-dlp progress templates are returned **identical** by `sanitize_text_for_log`, and `_parse_ytdlp_progress` / `_is_ytdlp_progress_line` give identical answers before and after (e.g. `40.3% of 649.37MiB` → `(274408260, 680913797)` both ways). The URL rule keeps `scheme://host/`, and the artefact rules are keyed on `vk_cookies_…`, which cannot touch `pct` or `size`. Were it real, the existing assertions would catch it loudly: `test_ytdlp_echo_false_progress_emits_debug_log` and `test_ytdlp_echo_false_suppresses_stderr_while_callback_fires` both pin `total`/`downloaded` exactly. Caveat: they would **not** catch a transform that changed *classification* — the new tests must cover that separately.

**7 · `B5-A4` (HIGH) — the declared test change is unnecessary and pre-empts plan 13 `B7`.** [verified-by-reading + verified-by-execution] Under `Alt A′` (transform inside `_echo_ytdlp_line`, after the `echo` gate) the `echo=False` path is byte-for-byte unchanged, so `test_ytdlp_echo_false_non_progress_line_no_output_no_log` **stays green untouched** (12 echo/transcript tests pass at `dfcf326`). §B5's AC-3/AC-4/AC-5 and `changes[2]` require rewriting it to assert the record-per-line ruling — that is `OUT-007`, owned by plan 13 `B7`, sequenced *after* `B5`, and plan 13 forbids weakening a clause `B5` pinned; plan 11 §3.5 itself recommends "`B5` lands the redaction only". **Recommendation:** zero existing-test changes; AC-3/AC-5 become "no existing test was changed", and AC-4 is withdrawn. If the Owner still wants the ruling, it is a **scope move into `B7`**, not a rewrite here.

**8 · Tests the block needs.** [verified-by-reading] **New (core, none exists today — no test in `tests/` passes a URL to `_echo_ytdlp_line`, and no test in `tests/` contains `vk-cdn.net`):** a sibling of `test_one_shot_line_keeps_its_newline` asserting a non-progress line carrying a signed CDN address reaches stderr as `scheme://host/***REDACTED***` with `sig=`/`token=` absent. **Existing sibling kept as-is:** `TestEchoYtdlpLine::test_one_shot_line_keeps_its_newline` (`captured.err == line`, benign `Destination: /tmp/video.mp4` — verified unchanged by the transform). **Clause 1:** `test_progress_line_is_rewritten_in_place` + `test_shorter_progress_line_clears_the_previous_one`. **Clause 2:** `test_ytdlp_echo_false_no_callback_stderr_empty`, `test_echo_false_chatty_child_no_stderr_and_bounded`, `test_ytdlp_echo_false_suppresses_stderr_while_callback_fires`. **Clause 3:** `test_ytdlp_echo_false_progress_emits_debug_log`. **Also add:** (i) an `echo=False` case whose line *does* carry a URL, pinning gate-before-transform (AC-6); (ii) an artefact-path case on the non-progress branch, proving `B4`'s widened rules reach the terminal; (iii) in `test_ytdlp_echo_false_progress_emits_debug_log`, the `D-6` evidence (assert `sanitize_text_for_log(line) == line` for the template) — the exact `downloaded`/`total` pins are necessary but do not prove ordering on their own.

**Baseline adopted as given** (`dfcf326`): 849 passed / 6 skipped · `mypy src` clean · `ruff check` + `ruff format --check` clean · `mypy src tests` 93 in 8 files · D-11 floor 3. `[DOC-UPDATE]` plan 11 §3.5 AC-9 / `T-B5` step 12 call `tests/test_hls_downloader.py` format-red; plan 17 §4 already corrects it. Plan 11 stays untouched.

**Edits made by this audit:** this `#### B5-AUDIT` section only. No `src/`, `tests/`, or other plan file was modified; nothing staged or committed.

---

#### `B5-DESIGN` — implementor task (Planner)

Implement `Alt A′` as designed below. Three `B5-AUDIT` findings **change the block's shape**
and this design carries all three: `B5-A0` (`OUT-007` has not landed → the transform goes on
what reaches `sys.stderr`, not on a record field), `B5-A4` (**zero** existing-test changes;
the planned rewrite is dropped), and `B5-A1` (batch mode **does** reach this sink on a non-TTY
stderr, so the blast radius is wider than plan 11 §3.5 claimed). Do not re-derive them.

**Do not modify any file other than the two named below.** No new file, no new dependency,
no `tests/test_packaging.py` edit, no change to `utils/url_sanitizer.py`.

````yaml
id: EB-B5
title: "Apply the redaction transform inside the child-output echo"
priority: high
depends_on: [EB-B4]

source_reference: .ai/plans/17-credentials-secrets-audit-fixes-execution.md
source_section: "`B5` block; `#### B5-AUDIT` (`B5-A0`, `B5-A1`, `B5-A2`, `B5-A3`, `B5-A4`, `B5-A6`) supersedes the `B5` block's `changes[2]` and `AC-3`/`AC-4`/`AC-5`"
source_file: .ai/plans/11-credentials-secrets-audit-fixes.md
source_blocks: ["B5 — Transform the terminal echo (SEC-005)"]
source_task: "`T-B5` (§6.7) and §3.5; the §7 `SEC-005` row. Plan 11 §3.5 itself recommends \"B5 lands the redaction only\"."

description: >
  _echo_ytdlp_line writes raw child lines to sys.stderr with nothing applied, while the same
  bytes reach the log file through sanitize_text_for_log. Inside one run the identical input is
  treated two ways, and the untransformed surface is the one an operator is most likely to
  capture: B5-A1 proved batch mode reaches this sink whenever sys.stderr is not a TTY
  (CI, `> file`, pipe, CliRunner), because batch_downloader sets
  `echo = not reporter.is_enabled` and RichProgressReporter.is_enabled falls back to
  sys.stderr.isatty(). Alt A' applies the transform at the two write statements inside
  _echo_ytdlp_line, after the `if not echo:` early return, so classification and byte
  accounting keep seeing the raw line and the echo=False path is byte-for-byte unchanged.

goals:
  - "A signed CDN address in a non-progress line reaches sys.stderr as `scheme://host/***REDACTED***`, with the query values absent."
  - "Both write branches are transformed: the progress branch's `text` and the non-progress branch's `line`."
  - "The `echo` gate is decided before any transform runs, structurally, not by statement ordering alone."
  - "Classification (`_is_ytdlp_progress_line`) and parsing (`_parse_ytdlp_progress`) keep the raw line; the transformed line is written, never parsed."
  - "The downstream transcript buffer receives the raw bytes; `output_chunks` stays raw."
  - "Zero existing tests change. The benign pass-through case becomes a sibling of the new redaction case, never its replacement."

files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - {type: function, name: _echo_ytdlp_line, action: modify}
      - {type: docstring, name: "the _echo_ytdlp_line docstring", action: rewrite}
      - {type: import, name: "the module-level `from ..utils.url_sanitizer import _strip_auth_params, sanitize_text_for_log`", action: no-change}
      - {type: function, name: _is_ytdlp_progress_line, action: no-change}
      - {type: function, name: _parse_ytdlp_progress, action: no-change}
      - {type: function, name: _monitor_progress, action: no-change}
      - {type: function, name: _drain_output, action: no-change}
      - {type: function, name: _retain_transcript_line, action: no-change}
      - {type: function, name: _await_first_and_cancel_others, action: no-change}
      - {type: module_constant, name: _YTDLP_PROGRESS_LINE_RE, action: no-change}
      - {type: module_constant, name: _YTDLP_PROGRESS_RE, action: no-change}
    semantic_anchors:
      insert_after:
        type: assignment
        value: 'text = line.rstrip("\n\r")'
      insert_before:
        type: if_statement
        value: "if _is_ytdlp_progress_line(line):"
      gate_reference:
        type: return_statement
        value: "return"

  - path: tests/test_hls_downloader.py
    targets:
      - {type: class, name: TestEchoYtdlpLine, action: add-cases-to}
      - {type: method, name: test_one_shot_line_keeps_its_newline, action: no-change}
      - {type: method, name: test_progress_line_is_rewritten_in_place, action: no-change}
      - {type: method, name: test_shorter_progress_line_clears_the_previous_one, action: no-change}
      - {type: class, name: TestBoundedYtDlpTranscript, action: no-change}
      - {type: class, name: TestYtDlpSubprocessShutdown, action: no-change}
      - {type: method, name: test_ytdlp_echo_false_non_progress_line_no_output_no_log, action: no-change}
    semantic_anchors:
      insert_after:
        type: method
        value: test_one_shot_line_keeps_its_newline

changes:

  - action: add_code
    description: >
      Transform at the two write statements inside _echo_ytdlp_line, after the `if not echo:`
      early return. The progress branch transforms the value it assigns to `text`; the
      non-progress branch transforms the argument at the `sys.stderr.write` call itself.
      Nothing else in the module changes - sanitize_text_for_log is already imported at module
      level, so there is no import edit.
    code_hint: |
      if not echo:
          progress = _parse_ytdlp_progress(line)          # raw line, unchanged
          if progress is not None:
              downloaded, total = progress
              logger.debug(
                  "ytdlp_progress_suppressed",
                  downloaded=downloaded,
                  total=total,
              )
          return                                          # the gate; nothing below runs
      if _is_ytdlp_progress_line(line):                   # classification on the RAW line
          text = sanitize_text_for_log(line.rstrip("\n\r"))
          width = shutil.get_terminal_size((80, 24)).columns
          sys.stderr.write("\r" + text.ljust(width)[:width] + "\r")
          sys.stderr.flush()
      else:
          sys.stderr.write(sanitize_text_for_log(line))
          sys.stderr.flush()

  - action: update_code
    description: >
      Rewrite _echo_ytdlp_line's docstring. It currently describes the `\r` rewrite and the
      echo=False suppression and says nothing about a transform - that omission is how the gap
      survived. It must state, in this order: (1) what reaches the console is the TRANSFORMED
      line - `https?://` URLs reduced to `scheme://host/***REDACTED***` and the product's own
      `vk_cookies_` artefact file/directory names collapsed to `***REDACTED***` - applied once,
      at the write, by `sanitize_text_for_log`; (2) classification and the byte accounting run
      on the RAW line, so `_is_ytdlp_progress_line` and `_parse_ytdlp_progress` are unaffected
      and the `\r` rewrite and the `downloaded`/`total` figures are computed from untransformed
      text; (3) `echo=False` is evaluated BEFORE any transform, so nothing is transformed,
      written, or logged for a non-progress line; (4) the downstream transcript buffer
      (`_retain_transcript_line` / `output_chunks`) still receives the RAW line, because
      redaction here must not substitute U+FFFD for undecodable child bytes and `download_failed`
      applies the transform at its own call site; (5) why the terminal is the surface that
      needed it - it is the one most likely to be captured (redirect, pipe, CI log), and batch
      mode reaches this sink whenever stderr is not a TTY (B5-A1). Keep it factual and concise;
      a claim nobody can check is the defect SEC-006 names.
    code_hint: |
      """Echo a yt-dlp output line to the console.

      What reaches stderr is the TRANSFORMED line: ``https?://`` URLs are reduced to
      ``scheme://host/***REDACTED***`` and the product's own ``vk_cookies_`` artefact
      file and directory names collapse to ``***REDACTED***``, applied once at the
      write by :func:`~vkdownloader.utils.url_sanitizer.sanitize_text_for_log`.

      Classification and byte accounting use the RAW line: ``_is_ytdlp_progress_line``
      and ``_parse_ytdlp_progress`` both read untransformed text, so the ``\\r`` rewrite
      and the reported ``downloaded`` / ``total`` figures are unaffected by the
      transform. ``echo=False`` is evaluated BEFORE any transform, so nothing is
      transformed, written, or logged for a non-progress line.

      The transcript buffer still receives the RAW line (``_retain_transcript_line`` /
      ``output_chunks``): redaction here must not substitute U+FFFD for undecodable child
      bytes, and ``download_failed`` applies the transform at its own call site.

      Progress lines (e.g. ``[download]  40.3% of 649.37MiB ...``) are rewritten in
      place using carriage returns to restore the pre-migration behavior where yt-dlp
      used ``\\r`` for live progress updates.  Non-progress lines use newlines as-is.
      """

  - action: add_code
    description: >
      Add the five cases below to TestEchoYtdlpLine, immediately after
      test_one_shot_line_keeps_its_newline. Each is single-purpose and named for the property
      it pins. The existing pass-through method is NOT modified, NOT renamed, and NOT replaced -
      the benign case and the redaction case are siblings, and the class docstring should say
      so, because "non-progress output is passed through unchanged" is true only of content
      with nothing to redact.

implementation_sequence:
  - "1. Add the transform to both write statements in `_echo_ytdlp_line`. Production code lands first; the 12 echo/transcript tests are unaffected by construction (the `echo=False` path returns before the new lines) - run them and confirm 12 passed before touching the test file. Do NOT add the transform ahead of the gate to 'see what happens'."
  - "2. Rewrite the docstring."
  - "3. Add the five new cases to `TestEchoYtdlpLine`."
  - "4. Run `git diff --stat` and prove no existing test body changed. Run the gates. Make ONE commit."
  - "Every intermediate state is valid: step 1 is behaviour-complete for the non-progress branch with no test asserting the new behaviour yet, and step 3 only adds assertions. No fix-up commit is needed or permitted."

architectural_constraints:
  - "Apply the transform at the sink, INSIDE _echo_ytdlp_line (Alt A'). Do NOT transform at the two call sites in _monitor_progress / _drain_output - that duplicates the rule at two places and can drift from the sink."
  - "The transform statement must never be hoisted above the `if not echo:` early return. Doing so is semantically invisible today (sanitize_text_for_log is pure) and therefore unguardable by a test - it is a review criterion, and the docstring must state the ordering so the invariant is documented at the site."
  - "`output_chunks` stays RAW. Its only consumer is `download_failed`, which already applies `sanitize_text_for_log` at its own call site; transforming earlier would (i) replace undecodable child bytes with U+FFFD, destroying the fidelity TRN-011 exists for, (ii) make `_MAX_CHILD_OUTPUT_BYTES` bound redacted text rather than bytes read, and (iii) duplicate the processor B6 is building."
  - "`_is_ytdlp_progress_line` and `_parse_ytdlp_progress` are unchanged. The write-branch admission predicate is `_is_ytdlp_progress_line`; `_parse_ytdlp_progress` sits on the `echo=False` branch and again in `_monitor_progress`, and is not this predicate."
  - "`services/ffmpeg_utils.py::iter_process_lines` is untouched and its contract is unchanged: it yields raw `bytes`."
  - "`subprocess_reader_failed` lives in `_await_first_and_cancel_others`, not in the drain loop. `B5` touches neither it nor `ytdlp_reader_line_overrun`; `B6` owns `subprocess_reader_failed.error`."
  - "Unchanged, all of it: the `\r` rewrite; terminal-width padding and truncation; `echo=False` writing nothing to sys.stderr and nothing to the log for a non-progress line; the DEBUG `ytdlp_progress_suppressed` record with its `downloaded` / `total` fields; both `ffmpeg_utils` merge records (plan-10 B14's)."
  - "`sanitize_text_for_log` is the control, not `sanitize_url_for_log`: the echo surface admits any non-progress line whole, so an all-or-nothing transform would destroy the operator's diagnostic text. (Closes `B5-D2`.)"
  - "No new dependency, no new file, no `utils/url_sanitizer.py` change, no `tests/test_packaging.py` frozenset edit. structlog conventions; no `print()`; no `Any` in the new tests; English only; strict typing clean; small focused functions."

required_tests:
  unchanged_must_pass_all_12:
    note: "Measured at dfcf326 - 12 passed. Every body byte-identical; `git diff` on this file must show additions only."
    names:
      - "TestEchoYtdlpLine::test_progress_line_is_rewritten_in_place"
      - "TestEchoYtdlpLine::test_one_shot_line_keeps_its_newline"
      - "TestEchoYtdlpLine::test_shorter_progress_line_clears_the_previous_one"
      - "TestBoundedYtDlpTranscript::test_failing_child_output_capped_to_bound"
      - "TestBoundedYtDlpTranscript::test_bounded_transcript_success_returns_output"
      - "TestBoundedYtDlpTranscript::test_bounded_transcript_retains_tail_not_head"
      - "TestBoundedYtDlpTranscript::test_short_transcript_unaffected_by_bound"
      - "TestBoundedYtDlpTranscript::test_echo_false_chatty_child_no_stderr_and_bounded"
      - "TestYtDlpSubprocessShutdown::test_ytdlp_echo_false_suppresses_stderr_while_callback_fires"
      - "TestYtDlpSubprocessShutdown::test_ytdlp_echo_false_no_callback_stderr_empty"
      - "TestYtDlpSubprocessShutdown::test_ytdlp_echo_false_progress_emits_debug_log"
      - "TestYtDlpSubprocessShutdown::test_ytdlp_echo_false_non_progress_line_no_output_no_log"
  new_cases:
    - name: test_non_progress_signed_cdn_url_is_redacted_on_stderr
      asserts: >
        THE CORE ASSERTION - nothing in tests/ covers it (no test passes a URL to
        _echo_ytdlp_line and none contains the CDN host). A non-progress line carrying a signed
        CDN address (`[video] abc123: Downloading webpage: https://vk-cdn.net/video/seg1.ts?sig=A1b2C3d4e5f6&token=zzzZZZ\n`)
        leaves `captured.err` containing `https://vk-cdn.net/***REDACTED***`, and containing
        neither `sig=`, `token=`, `A1b2C3d4e5f6`, nor `zzzZZZ`. The surrounding yt-dlp prose and
        the trailing newline survive. Sibling of test_one_shot_line_keeps_its_newline, not a
        replacement for it.
    - name: test_non_progress_cookie_artefact_path_is_redacted_on_stderr
      asserts: >
        Proves B4's widened artefact rules reach the terminal, which the URL case alone does not.
        A non-progress `Destination:` line carrying a real artefact path (build it with
        `_create_cookie_artifact_dir()` / `_create_temp_cookie_file()` so the shape is genuine;
        clean up in `finally` the way `tests/test_cookies.py` does) leaves `***REDACTED***` in
        `captured.err` with none of `vk_cookies_`, `AppData`, or `Users` present.
    - name: test_progress_branch_text_is_transformed_before_padding
      asserts: >
        The second write branch has no coverage otherwise. A line that `_is_ytdlp_progress_line`
        classifies as progress AND that carries a signed CDN URL in its speed field
        (`[download]  40.3% of 649.37MiB at https://vk-cdn.net/v?sig=X ETA 06:43\n`) still
        takes the `\r` rewrite - `captured.err` starts with `\r`, ends with `\r`, contains no
        `\n` - while carrying `https://vk-cdn.net/***REDACTED***` and no `sig=`. FIXTURE
        CONSTRAINT: the transformed text must stay under 80 columns, because the branch pads and
        truncates at `shutil.get_terminal_size((80, 24)).columns`; a narrower terminal would cut
        the assertion target and make the test environment-dependent. State that in the docstring.
    - name: test_echo_false_url_line_writes_nothing_and_logs_nothing
      asserts: >
        The observable half of gate-before-transform. An `echo=False` call whose line DOES carry
        a signed CDN URL produces `captured.err == ""` and zero logger calls, proving the gate is
        evaluated before anything is transformed. Do this at `_echo_ytdlp_line` directly with
        `capsys` and a patched `logger` - do NOT modify the existing subprocess-level
        test_ytdlp_echo_false_non_progress_line_no_output_no_log, and do not duplicate it there.
    - name: test_progress_templates_are_transform_identically
      asserts: >
        The D-6 EVIDENCE, and the only honest form of it. Over all seven real yt-dlp progress
        templates (the anchored-prefix percent/estimated/byte-count/N-A forms, with and without
        the `(frag i/n)` suffix): `sanitize_text_for_log(template) == template`; and
        `_is_ytdlp_progress_line(template)` equals `_is_ytdlp_progress_line(sanitize_text_for_log(template))`;
        and `_parse_ytdlp_progress(template)` equals `_parse_ytdlp_progress(sanitize_text_for_log(template))`.
        Call the second half out in the docstring: it pins CLASSIFICATION, which the existing
        `downloaded`/`total` assertions provably do NOT cover - they would stay green through a
        transform that changed which branch a line takes. Also record WHY the identity holds, so
        a future rule author sees that the anchor is load-bearing: `_YTDLP_PROGRESS_LINE_RE` is
        anchored at `^\[download\]`, and none of B4's three rules can match the
        `[download] <pct>% of <size>` region, because the artefact lead requires a `/` or `\`
        separator that region never contains and the URL rule requires `https?://`.
  sibling_requirement: >
    test_one_shot_line_keeps_its_newline stays green with a byte-identical body and its current
    name. Its assertion `captured.err == line` is now conditional on the content having nothing
    to redact, and the new redaction case is what makes that conditionality explicit - so the two
    must sit adjacent in the class, and TestEchoYtdlpLine's docstring should say the pair proves
    the pass-through is content-dependent, not that pass-through was replaced. Editing or removing
    the existing method would violate the "zero existing-test changes" ruling of B5-A4.
  windows_requirement: >
    Every new test runs on Windows: no `pytest.mark.skipif(sys.platform...)`, no POSIX-only
    assertion, no new skip. `_echo_ytdlp_line` writes to `sys.stderr` and `capsys` captures it
    on this platform exactly as the existing three cases already do.

acceptance_criteria:
  - id: AC-1
    criterion: A non-progress line carrying a signed CDN URL reaches sys.stderr as `scheme://host/***REDACTED***` with every query value absent.
    verified_by: test_non_progress_signed_cdn_url_is_redacted_on_stderr
  - id: AC-2
    criterion: The progress write branch transforms `text` before padding and truncation, and the `\r` rewrite shape is intact.
    verified_by: test_progress_branch_text_is_transformed_before_padding
  - id: AC-3
    criterion: A real cookie-artefact path in a non-progress line is redacted on stderr, proving B4's rules reach the terminal.
    verified_by: test_non_progress_cookie_artefact_path_is_redacted_on_stderr
  - id: AC-4
    criterion: "Withdrawn by B5-A4: the planned rewrite of the non-progress echo test does not happen. Its replacement is `no existing test was changed` - and `git diff` on tests/test_hls_downloader.py shows additions only."
    verified_by: git diff
  - id: AC-5
    criterion: "`echo=False` on a URL-bearing line writes nothing to stderr and logs nothing, and the DEBUG `ytdlp_progress_suppressed` record still carries exact `downloaded`/`total`."
    verified_by: test_echo_false_url_line_writes_nothing_and_logs_nothing; the 12 unchanged tests
  - id: AC-6
    criterion: "Classification and parsing run on the raw line - all seven real progress templates are transform-identical, and classification plus parse results are identical before and after."
    verified_by: test_progress_templates_are_transform_identically
  - id: AC-7
    criterion: All 12 existing echo/transcript tests pass unchanged, 12 passed / 0 failed.
    verified_by: uv run pytest tests/test_hls_downloader.py -q -k "echo or Echo or transcript or Transcript"
  - id: AC-8
    criterion: "The `_echo_ytdlp_line` docstring states the transform, the raw-line parsing, the gate ordering, the raw transcript buffer, and the non-TTY stderr reachability."
    verified_by: review
  - id: AC-9
    criterion: "`_is_ytdlp_progress_line`, `_parse_ytdlp_progress`, `iter_process_lines`, `output_chunks`, `_retain_transcript_line`, `_monitor_progress`, `_drain_output` and `_await_first_and_cancel_others` are all unchanged; `subprocess_reader_failed` and `ytdlp_reader_line_overrun` are untouched."
    verified_by: review
  - id: AC-10
    criterion: Gates green (see `gates`).
    verified_by: the gate commands

gates:
  - "uv run pytest -q - full suite green; total skips NOT above 6 (3 D-11 POSIX-permission + 3 pre-existing killpg)."
  - "uv run mypy src - clean."
  - "uv run ruff check src tests - clean."
  - "uv run ruff format --check src tests - clean, no exception clause."
  - "uv run mypy src tests - error count NOT above 93."
  - "uv run pytest tests/test_packaging.py -q - 14 passed."
  - "uv run pytest tests/test_hls_downloader.py -q -k \"echo or Echo or transcript or Transcript\" - 12 passed, 0 failed, plus every new case executed."
  - "Every new test executed on Windows: no platform guard, no new skip."

commit_shape:
  subject: "fix(download): redact child output before it reaches the console"
  count: 1
  body_must_record:
    - "`OUT-007` had NOT landed when this was written: no per-line record for non-progress child output exists anywhere in src/ (`_echo_ytdlp_line` still held a live `sys.stderr.write(line)` and its `echo=False` branch returns without logging). That is what decided the transform goes on what reaches sys.stderr rather than on a record field; it is plan 13's `B7`, sequenced strictly after `B5`."
    - "The planned test rewrite was DROPPED as unnecessary. Under `Alt A'` the `echo=False` path is byte-for-byte unchanged, so `test_ytdlp_echo_false_non_progress_line_no_output_no_log` stays green untouched (12 echo/transcript tests pass at dfcf326). Rewriting it to assert the record-per-line ruling would have implemented `OUT-007` here, pre-empting plan 13 `B7`, and weakened a clause `B5` had pinned. Plan 11 §3.5 itself recommends \"B5 lands the redaction only\". **Zero existing-test changes; the benign pass-through case survives as a sibling of the new redaction case.**"
    - "Batch mode DOES reach this sink, contradicting plan 11 §3.5's \"batch mode never reaches this sink\". `batch_downloader._download_single` sets `echo = not reporter.is_enabled`, and `RichProgressReporter.is_enabled` falls back to `sys.stderr.isatty()`, so batch on a non-TTY stderr (CI, `> file`, pipe, CliRunner) sets `echo=True`. Proven by the live `test_batch_echo_not_suppressed_when_reporter_disabled` (`echo is True`). The setter enumeration is complete - single-download CLI (no `echo`, so always True) and non-TTY batch are the only routes - so the blast radius is WIDER than plan 11 claimed: redirected output is exactly the capture-prone case."
    - "`D-6`'s resolution: classification and parsing run on the RAW line; the transform is applied only to what is written. Its hazard was proven THEORETICAL, not real - all 7 real yt-dlp progress templates transform to identical text with identical parse and classification results. The test therefore pins the INVARIANT (identity + unchanged classification), not a failure that cannot occur, and records why it holds: `_YTDLP_PROGRESS_LINE_RE` is anchored at `^[download]` and none of B4's three rules can match that region."
    - "`output_chunks` stays RAW, and why: it is the child's bytes, its only consumer (`download_failed`) already applies `sanitize_text_for_log` at its own call site, and transforming earlier would substitute U+FFFD for undecodable bytes (destroying the fidelity TRN-011 exists for), make `_MAX_CHILD_OUTPUT_BYTES` bound redacted text rather than bytes read, and duplicate the processor `B6` is building."
    - "The write-branch admission predicate is `_is_ytdlp_progress_line`, NOT `_parse_ytdlp_progress` - the latter is on the `echo=False` branch and again in `_monitor_progress`."
    - "The transform is applied at the sink, inside `_echo_ytdlp_line`, not at the two call sites in `_monitor_progress` / `_drain_output` - one rule, one place, no drift."
    - "The `echo` gate is evaluated before any transform, by control flow; a hoisted transform would be semantically invisible today (the transform is pure) and is therefore a review constraint, not a test."

staging:
  - "Explicit paths only. Never `git add -A`, `git add .`, or `git add -u`."
  - "git add src/vkdownloader/services/ytdlp_downloader.py"
  - "git add tests/test_hls_downloader.py"
  - "Never amend, force-push, `git reset`, or `git checkout`."
  - "The working tree carries unrelated modified and untracked entries at baseline (deleted `.ai/plans/*`, a modified `17-…execution.md`, `tmp/`). None may enter this commit."
````

##### `B5-DESIGN` — the five decisions this task rests on, and why

**1 · `D-6` placement — classify and parse on the RAW line; transform only what is written.**
Confirmed. `_is_ytdlp_progress_line(line)` and `_parse_ytdlp_progress(line)` both receive raw
text; `sanitize_text_for_log` is applied to the derived value at each write. Three reasons.
The `echo=False` branch parses **before** any write and the parse feeds only the DEBUG record's
`downloaded`/`total`; feeding a transformed string to a pure numeric extractor could only lose
precision, never gain it. `_monitor_progress` uses the same decoded line a third time for
`progress_callback`, and `B5` does not touch that call site — so transforming at the call sites
would double-apply. And the identity is *structural*, not lucky: `_YTDLP_PROGRESS_LINE_RE` is
anchored at `^\[download\]`, and none of `B4`'s three rules can reach the `[download] <pct>% of
<size>` region — the artefact lead requires a `/` or `\` separator that region never contains,
and the URL rule requires `https?://`.

**The evidence test pins the invariant, not a failure that cannot occur.**
`test_progress_templates_are_transform_identically` asserts, over all seven real templates,
`f(t) == t` **and** that classification and parse results are identical before and after. That
second half is the part that matters: `B5-A6` measured that the existing `downloaded`/`total`
assertions would stay green through a transform that changed which branch a line takes. The test
must therefore assert classification explicitly, and its docstring must record the `^[download]`
anchor as the reason — so the next rule author sees that the anchor is load-bearing.

**2 · Both write branches, at exactly these two places.** The progress branch transforms the
value it assigns to `text`, immediately after the `rstrip` and **before** `width`/`ljust` — so
the padded, truncated text is the redacted one (the transform-before-truncate order plan 10
already pinned). The non-progress branch transforms the argument **at the `sys.stderr.write`
call itself**, so there is no named local that a later edit could write to instead.

**3 · The gate is structural, not incidental.** `sanitize_text_for_log` is pure, so hoisting the
transform above the `if not echo: … return` would change **nothing observable** — it cannot be
guarded by a test, and a test that claims to guard it would be theatre. The guarantee is
therefore made structural: the transform appears **only** inside the two write arms, `text` is
assigned inside the progress arm, and the docstring states the ordering so the invariant is
written down at the site. The observable half *is* tested
(`test_echo_false_url_line_writes_nothing_and_logs_nothing`), and it is the half that would break
if `B6`'s central processor later made the transform impure or logging.

**4 · The docstring** states, in order: the console receives the transformed line; classification
and byte accounting use the raw line; `echo=False` is evaluated before any transform; the
transcript buffer still receives the raw line and why; and that a non-TTY stderr routes batch
mode here (`B5-A1`). Its current omission of any mention of a transform is the reason this defect
survived, so the omission is the defect.

**5 · Sibling, never replacement.** `test_one_shot_line_keeps_its_newline` keeps its name and its
byte-identical body. Its assertion `captured.err == line` is now conditional on the content
having nothing to redact; `test_non_progress_signed_cdn_url_is_redacted_on_stderr` is what makes
that conditionality explicit. The two sit adjacent in `TestEchoYtdlpLine`, and the class
docstring says the pair proves pass-through is content-dependent — not that pass-through was
replaced. Editing or removing the existing method would violate `B5-A4`.

**No existing test is modified anywhere in this block.** That is `B5-A4`'s recommendation and
this design adopts it: the rewrite plan 11 required would have implemented `OUT-007`, which
belongs to plan 13's `B7` and is sequenced strictly after `B5`. If the Owner still wants the
record-per-line ruling, it is a scope move into `B7`, not a rewrite here.

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

#### `B6-AUDIT` — block-`B6` audit findings (Auditor; read-only at `48d0efa`)

**Baseline re-measured at `48d0efa`, adopted as given:** 854 passed, 6 skipped · `mypy src` clean (31 files) · `ruff check src tests` clean · `ruff format --check src tests` clean (54 files) · `mypy src tests` 93 errors in 8 files · `tests/test_packaging.py` 14 passed. [verified-by-execution] Nothing was staged or committed; no `src/`, `tests/`, or audit-phase file was touched.

**`B6-A1` (MANDATORY, `[SPEC-DEVIATION]`) — the enumeration is 27 sites / 22 names, not 21 / 24. The count differs, so the closure claim changes.** Per plan 11 §3.6's own rule this is a finding, not implementer discretion. Census method: AST walk of every `logger.*` call in `src/`, keeping any call with an `error=`, `path=`, `exc_info=` keyword or an `.exception()` receiver. [verified-by-execution]

- **31 sites / 26 names** carry exception text. **4 sites / 4 names are excluded** as plan 11 directs: `infrastructure/network_monitor.py`'s `playlist_body_read_error`, `hls_select_error`, `response_body_error`, `response_json_error` — all `error=str(e.__class__.__name__)`, confirmed class-name-only. ⇒ **27 sites / 22 record names in scope.**
- Of those 27: **2 sites** are pre-sanitised and owned by plan-10 `B14` (`batch_merge_failed`, `final_merge_failed`, both `error=sanitize_text_for_log(...)[:200]`) — **do not touch**; **1 further site** is pre-sanitised and owned by **nobody**: `ytdlp_downloader.py`'s `download_failed` sets `error=sanitize_text_for_log(error_msg)` on the assignment line immediately above the record. ⇒ **24 sites / 19 names carry untransformed exception text.**
- **`download_failed` is a name collision across two files and two carriers** — `cli.py` (`logger.exception`, `url=sanitize_url_for_log(url)`, guarded by `_logging_configured`) and `ytdlp_downloader.py` (`error=error_msg`, pre-sanitised). Any test or count that treats "the 21 records" as one-to-one with call sites is wrong here. This single collision is the most likely source of the prior counts' drift.
- **Plan 11's `yt_dlp_not_found` does not exist.** The emitted name is **`ytdlp_not_found`** [verified-by-reading]. A test written from plan 11's table would assert on a record the product never emits.
- **`cookie_file_cleaned_up` sits outside the exception-text boundary**: it carries `path=str(cookie_file)` at DEBUG and **no** exception text [verified-by-reading]. It is in scope for `D-7`'s key choice and for AC-3, but it must be added to the enumeration explicitly or the closure claim silently omits a record that fires on **every successful download**.

**`B6-A2` — the eight traceback-carrying records: confirmed, 8 / 8, and the decisive argument survives.** Five `exc_info=True` — `browser_launch_failed` (`browser.py`), `browser_close_failed` (`browser.py`, also `error=str(exc)`), `playwright_stop_failed` (`browser.py`, also `error=str(exc)`), `video_player_click_failed` (`extractor.py`, DEBUG), `ytdlp_not_found` (`ytdlp_downloader.py`, also `path=exc.filename`) — plus three `logger.exception` — `download_failed` (`cli.py`), `batch_download_failed` (`cli.py`), `unexpected_error_in_batch_download` (`batch_downloader.py`). [verified-by-reading] `exc_info` takes an exception or traceback object, not text, so **there is no text to wrap at a call site**; a call-site-only remedy is structurally incapable of closing `SEC-007`. The five `exc_info` records and the three `.exception` records are **eight distinct call sites**, one per record.

**`B6-A3` (MANDATORY, `[SPEC-DEVIATION]`) — the `path=` inventory is 8 sites / 7 names, and one of plan 17's cited `path=` sites is not a log record.** [verified-by-execution]

| Set | Record | File | Carrier | Classification |
|---|---|---|---|---|
| artefact (3 sites / 2 names) | `cookie_file_cleanup_failed` (dir) | `ytdlp_downloader.py` | `path=str(cookie_dir)` + `error=str(failure)` | **redact** |
| artefact | `cookie_file_cleanup_failed` (file) | `ytdlp_downloader.py` | `path=str(cookie_file)` + `error=str(exc)` | **redact** |
| artefact | `cookie_file_cleaned_up` | `ytdlp_downloader.py` | `path=str(cookie_file)`, DEBUG, every success | **redact** |
| benign (5 sites / 5 names) | `env_file_resolved` | `cli.py` | `path=str(env_file.resolve())` | do not redact |
| benign | `output_path_inside_repository` | `utils/security.py` | `path=str(resolved)` (also `repo_root=str(...)`) | do not redact |
| benign | `failed_to_cleanup_partial_file` | `ytdlp_downloader.py` | `path=str(validated_output)` | do not redact |
| benign | `download_interrupted_switching_to_segments` | `ytdlp_downloader.py` | `path=str(output_file)` | do not redact |
| benign | `ytdlp_not_found` | `ytdlp_downloader.py` | **`path=exc.filename`** | do not redact |

Two corrections. (a) `ytdlp_not_found`'s carrier is `exc.filename`, **not** `str(...)`, and `FileNotFoundError.filename` is `str | None` — so `path` can legitimately arrive as **`None`**, which is exactly AC-8's non-string case and must not be a special path in the processor. (b) Plan 17's `D-7` criterion list names "`infrastructure/browser.py`'s `add_init_script`" as a `path=` site: that is **`await page.add_init_script(path=str(self._stealth_path))`, a Playwright API call, not a log record** [verified-by-reading]. It must be struck from the `D-7` input. Four further records carry output paths under a **different key**, `output=str(...)` (`starting_download`, `starting_ytdlp_download`, `starting_segment_download`, `merge_completed`) [verified-by-execution] — outside plan 17's `path` set, and they decide the `D-7` question below.

**`B6-A4` — the processor chain, measured and confirmed.** `config.setup_logging`'s `structlog.configure(processors=[...])` at `48d0efa`, in order: `structlog.contextvars.merge_contextvars` → `structlog.stdlib.add_log_level` → `structlog.processors.TimeStamper(fmt="iso", utc=True)` → **`structlog.processors.format_exc_info`** → `structlog.processors.UnicodeDecoder()` → `structlog.processors.JSONRenderer() if settings.log_file else structlog.dev.ConsoleRenderer()`. [verified-by-reading + verified-by-execution] `wrapper_class=structlog.stdlib.BoundLogger`, `logger_factory=structlog.stdlib.LoggerFactory()`, `cache_logger_on_first_use=True`. **structlog 26.1.0**, Python 3.12.1 [verified-by-execution].

- **`format_exc_info` confirmed to consume `exc_info` and write the rendered traceback into the `exception` key.** Driving the configured chain with `exc_info=True` produced `{"path": …, "event": …, "level": …, "timestamp": …, "exception": "Traceback (most recent call last):\n  File …\nValueError: sig=…"}` — `exc_info` **absent**, `exception` a **single `str`** with embedded newlines [verified-by-execution]. `D-7`'s candidate allowlist `error` + `exception` (+ `path`) is therefore correct.
- **Refinement to "exactly one free slot, position 5".** There are **two** insertion points after `format_exc_info` and before the renderer — before or after `UnicodeDecoder()`. "Position 5" (before `UnicodeDecoder`) is the correct choice and the safe one; `UnicodeDecoder` only decodes `bytes` values, so the two orders are behaviourally equivalent for redaction, but last-before-renderer is what AC-4 should pin.
- **A stdlib `logging` record bypasses the processor entirely.** Driving a plain `logging.getLogger(...)` record with `exc_info=True` through the same configuration emitted raw stdlib output (`'plain_event\nTraceback (most recent call last):\n … ValueError: sig=…\n'`) — no structlog renderer, no processor [verified-by-execution]. `config.py` does call `logging.basicConfig(format="%(message)s", …)` with a `StreamHandler`/`FileHandler`, and installs **no** `structlog.stdlib.ProcessorFormatter`, so stdlib records are rendered by stdlib, not structlog. **Measured mitigation: `src/` contains zero `logging.getLogger(...)` module loggers** — every one of the 16 module loggers is `structlog.get_logger(__name__)` [verified-by-execution]; only `services/progress_display.py` touches the *root* logger, to repoint handler streams. **Residual, `[BEST-PRACTICE]`, advisory:** third-party libraries (`playwright`, `yt_dlp`, `aiohttp`, `urllib3`) log through stdlib to that same root handler and are **not** covered by a structlog processor. If a future library logs a signed URL or an artefact path, the central control does not see it. Effort: small; value: one `structlog.stdlib.ProcessorFormatter` (or a root-level filter) closes it. Not this block's scope — record it and hand onward.
- **There is exactly one `structlog.configure` in `src/`** [verified-by-execution].

**`B6-A5` (MANDATORY, `[SPEC-DEVIATION]`) — `cli.py` has no pre-`setup_logging` console path, so plan 17's instruction 2 is unexecutable and must be struck.** Plan 17 §`B6` item 2 says "`cli.py` gets the same wiring for its own pre-`setup_logging` console path". Measured: the preamble calls `setup_logging(settings)` and sets `_logging_configured = True`; both `cli.py` records are wrapped in `if _logging_configured:`; `_render_preamble_failure`'s `preamble_failed` record is likewise gated. **There is no logging path in `cli.py` that exists before `setup_logging` returns** [verified-by-reading]. `cli.py` needs **zero** wiring, and plan 11 `T-B6` step 5's "`cli.py` is not edited" is the correct instruction. Recommend deleting plan 17's clause rather than implementing a stub.

**`B6-A6` — the layer constraint, stated precisely.** `docs/STRUCT.md` lists `config.py` in the package tree ("Settings model, logging, env validation") but names it in **no** layer bullet: the Entry layer is `cli.py`, `__main__.py` ("No business logic or **private-symbol imports** from service/utils layers"), the Service layer is `services/` ("Imports private symbols from `utils/` internally"), and `config.py` is in neither [verified-by-reading]. So plan 11's "entry-adjacent must be a public name" is an **inference, not a documented rule**, exactly as plan 17 §2.8 states. Confirmed: `config.py` imports only `vkdownloader.models.enums` (`CookieSource`, `LogLevel`) and has **zero** `logger.` calls [verified-by-execution]. And "public" is **not** the package's own convention — `utils/__init__.py::__all__` exports `_strip_auth_params` and `_resolve_output_file`, both underscore-named [verified-by-reading]. **What it requires:** the processor must be reachable under a public name **only if** the project adopts "entry-adjacent means public" as a rule. That is `B6-D3`, a plan-level decision, and it is not forced by `STRUCT.md` as written.

**`B6-A7` (`D-7`) — the criterion is answered by measurement, and it points at `Alt B`.** Criterion: *can the rule set match a field the product logs for benign purposes?* `sanitize_text_for_log` matches exactly two shapes: any `https?://` run, and the two `vk_cookies_*` artefact literals [verified-by-reading]. I enumerated every record keyword in `src/` (56 distinct keys, `url` × 53, `path` × 8, `error` × 25, …) and every URL-bearing field's expression [verified-by-execution]:

- **No benign field matches.** A path never matches: the URL rule needs `https?://`, the artefact rules need the frozen literals. `output`, `url_file`, `repo_root`, `working_dir`, `hint`, `reason`, `next_action`, `quality` are all unmatched.
- **Every `url=` field in every record is already `_strip_auth_params`'d** — all 53 sites inspected; the two apparent exceptions (`downloader_throttle.py`'s `download_cancelled | url = url`, `browser.py`'s `stealth_asset_missing | hint = msg`) are a parameter documented "Sanitized URL for logging" whose only caller passes `sanitized_url`, and a package-relative asset path [verified-by-reading].
- **The one benign value that *does* match is a verified fixed point.** `sanitize_text_for_log("https://host/***REDACTED***")` → unchanged, and unchanged again on pass 2. I ran two passes over 9 measured shapes (already-redacted url, bare marker, `str(aiohttp.ClientResponseError)` carrying a signed CDN url, `path=C:\…\vk_cookies_*.cookies.txt`, a directory artefact, a mixed child line, `Unknown yt-dlp error`, `_MERGE_HINT`): **every one a fixed point** [verified-by-execution].

⇒ **On the measured facts, `Alt B` (every string value) is the safe and complete choice**, and its cost is lower than plan 11 assumed. **Residual of `Alt B`:** it is not literally key-agnostic — `event`, `level`, `timestamp` are string values, and transforming `event` would rename records and break log queries, so `Alt B` needs a small **denylist** of structural keys. Under the measured rule set the denylist is never *needed* to prevent a false redaction (no record's `event` name contains `http` or `vk_cookies_`), but it is needed to prevent a *semantic* corruption. Plan 17's claim that `Alt B` "will eventually redact a legitimate operator-facing message" is **not supported by any measured instance** — worth softening. **Residual of `Alt A` (allowlist `error`/`exception`/`path`):** every text-bearing key outside the three, i.e. `url_file` (cli.py's `batch_download_failed`, a user-chosen urls-file path), `output` × 4, `repo_root`, `working_dir`, `hint` × 5, `reason` × 8, `urls` (a **list**, `captured_m3u8_urls`) — plus, decisively, **any future record that names its payload something else**. `Alt A` buys today's completeness and gives up the property that makes this block worth its risk. Recommend `Alt B` with an explicit structural-key denylist, and record the residual as "a future record whose payload is a **list** or **mapping** is not transformed" (the `urls` list is covered today only because its elements are pre-sanitised at the call site).

**`B6-A8` — the `B4` gap: measured, it does NOT materialise. `D-5`'s justification holds, and `B6` should record that rather than close it.** The concern is right in principle — a structlog event dict is not a child sink, and `_format_cookies_for_ffmpeg` returns a flat session string (`"; ".join(f"{name}={value}")`) that becomes an in-process `headers["Cookie"]` (`segment_downloader.py`, two sites). I checked every record field in `src/` for a `Cookie:` header, a flat session string, `headers`, `cookies`, or `policy` [verified-by-execution]: **the only cookie-adjacent record fields in the whole product are the three artefact `path` values.** `headers` is never logged; `request.cookies` (`B7`'s carrier) never reaches a record; `DownloadPolicy` is never logged. **Answer: no record in the measured enumeration carries a `Cookie:` header value or a flat session string, so the processor alone will redact nothing here and `D-5`'s "no child emits a `Cookie:` header to a sink" reasoning is not what protects the event dict — the protection is "the product never logs one".** That is a *different* and *stronger* claim, and it is the one `B6` should record. **Do not widen `B4`'s rule set.** Options, in order of cost: (1) record the structural fact and pin it with a test that asserts no log record field name is `headers`/`cookies`/`policy` and no value contains `Cookie:` — cheap, and it makes the residual self-checking; (2) hand the residual to `B7`, whose `SecretStr`/`repr=False` work makes a future `logger.debug(policy)` unable to render the session at all — that is the durable fix and needs no processor change; (3) add a `Cookie:` rule to `B4`'s set — **not recommended**, it is the broadening `D-5` declined and no instance justifies it.

**`B6-A9` — alternatives, characterised (no choice made).**

- **Central processor after `format_exc_info`** — covers all 27 in-scope sites, all 8 traceback records, and every future record; no call site edited. Cost: one global transform on every record, which is why `AC-4` (chain position) and `AC-5` (event-name-agnosticism) are mandatory.
- **Wrapping `error=str(e)` at every site** — **structurally incomplete.** It cannot reach the eight traceback records: `exc_info` takes an exception or traceback object, not text. Reporting `SEC-007` closed on this basis leaves the largest leak open. Rejected; it survives only as the idempotency fixture `486bfd9` already created.
- **Central processor *plus* per-site wrapping** — redundant, and two transforms in the path must then be idempotent. `sanitize_text_for_log` **is** a verified fixed point on every measured shape (`B6-A7`), so this is survivable today — but it buys nothing and adds a second place to forget. Rejected.
- **A stdlib `logging.Filter`** — **plan 11 §3.6's stated reason is factually wrong.** Measured: a handler-level filter *does* run for structlog's own records, and it sees `record.msg` = the **already-rendered JSON string**, with `record.args == ()` and **zero** extra record attributes [verified-by-execution]. So it is not that structlog "bypasses handler-level filters"; it is that the filter sees the **rendered wire format**, not the event dict. It therefore cannot be key-aware, cannot distinguish `error` from `path` from `event`, needs a *different* regex per renderer (`JSONRenderer` vs `ConsoleRenderer`'s box-drawing output), and would break the moment the product adopts `ProcessorFormatter` (where the handler receives an unrendered `LogRecord`). **Recommend correcting the reason, not the verdict** — `[SPEC-DEVIATION]`, one sentence in plan 11 §3.6 and one in plan 17's `changes` block.
- **A further option, better than the filter and worth naming:** wrap the renderer instead of inserting a sibling processor — i.e. subclass `JSONRenderer`/`ConsoleRenderer`. **Rejected by measurement:** the renderer is chosen by a conditional expression *inside* the same list, so wrapping it means two renderer classes and the chain-position assertion becomes "is the wrapper last", which no longer distinguishes before/after `format_exc_info`. A sibling processor before the renderer is strictly more assertable.

**`B6-A10` — `B5` did land, and its output never reaches a record, so `B5` is not a live pipeline input.** Confirmed at `48d0efa`: `_echo_ytdlp_line` applies `sanitize_text_for_log` and writes the result with `sys.stderr.write(...)` — **no logger call on either write branch**; its only record is `ytdlp_progress_suppressed`, carrying `downloaded`/`total` integers and no line text; and its `echo=False` branch returns before either write [verified-by-reading]. **The redacted echo text is written to `sys.stderr` and nowhere else, so `B5`'s call site is not a processor input and the double-transform concern it raises is theoretical, not live.** The *live* idempotency exposure is a different one neither plan names: `ytdlp_downloader.py`'s `download_failed` sanitises `error_msg` at the call site, so a value **does** reach the record pre-sanitised — alongside `B14`'s two. **The idempotency fixture set is three records, not two** (`batch_merge_failed`, `final_merge_failed`, `download_failed`), and the third is the one that exercises the pipeline path a `B6` test can drive end-to-end.

**`B6-A11` — the tests this block needs.** All against the **configured** chain (call `config.setup_logging`, then `structlog.get_logger`), never a hand-built dict. Beware `cache_logger_on_first_use=True`: `structlog.get_config()["processors"]` is the correct assertion target for position, but a logger bound before a reconfigure keeps its cached chain.

1. **Enumeration oracle.** Assert the measured set — 22 record names / 27 sites — by AST-scanning `src/` for `error=`/`path=`/`exc_info=`/`.exception(` calls, minus the four `network_monitor` names, plus `cookie_file_cleaned_up`. This is the AC-7 re-count as an executable oracle, and it is the only thing that stops the count drifting a fourth time.
2. **Rendered-traceback test (the criterion that distinguishes this block from the rejected call-site alternative).** Drive an `exc_info=True` record through the chain with a signed CDN url in the exception message; assert `exception` contains `***REDACTED***` and the original signature is absent.
3. **`cookie_file_cleanup_failed`, both fields.** One test, `path=` a real artefact built via `_create_cookie_artifact_dir()`/`_create_temp_cookie_file()` and `error=` carrying the same shape; assert **both** are redacted. (Behavioural, not literal: `B4` duplicated the artefact literals in `utils/`, so a literal in the test is the only drift guard.)
4. **`cookie_file_cleaned_up`'s `path`** — the success-path instance; assert redacted.
5. **Chain-position test.** Read `structlog.get_config()["processors"]`; assert the processor's index is **strictly greater** than the index of the `structlog.processors.ExceptionRenderer` instance and **strictly less** than the renderer's. Identify members by **type or identity, not `__name__`** — measured: `TimeStamper` and `format_exc_info` are instances (`ExceptionRenderer`), and only the plain functions expose `__name__`. A reorder that moves the processor before `format_exc_info` must fail here.
6. **Event-name-agnosticism.** Two records with **different** names and the **same** value; assert identical redaction and that no branch keys on a name. Also assert the processor source/bytecode contains none of the enumerated record names — the Decision B constraint made mechanical, so plan 13's `code=1`→`code=3` re-coding of `cli.py`'s configuration arm cannot change which record is covered.
7. **Idempotency against all three pre-sanitised sites.** `batch_merge_failed`, `final_merge_failed`, **and** `ytdlp_downloader`'s `download_failed`: a value passed through `sanitize_text_for_log` then the processor must equal the value passed through the processor alone.
8. **Never-raises.** `None` (the real `ytdlp_not_found` `path=exc.filename` case), an `int`, a nested `dict`, a `list` of strings, and an absent key — assert the record renders and no exception escapes.
9. **`D-7` scope oracle.** Whichever scope is chosen, assert it explicitly: for `Alt B`, that `event`/`level`/`timestamp` come out **byte-identical**; for `Alt A`, that a novel key is left untouched **and that this residual is written down**.

**Edits made by this audit: one.** `#### B6-AUDIT` inserted into this file, in the `B6` region immediately before `### `B7``. No code, test, plan-11, or other audit-phase file was read-modified; nothing staged or committed; `tmp/`, `tmp_old_sec*.md`, `.ai/plans/00_*`…`07_*`, `.ai/problems/PROBLEM.md`, `.kilo/commands/implement/implement-plan-multiagent.md`, untracked plans 05–08, `.gitignore`, and every `src/`/`tests/` file are untouched.

---

#### `B6-RESEARCH` — block-`B6` research findings (Researcher; read-only at `48d0efa`)

Sources (all authoritative, all read): structlog **26.1.0** installed source — `_base.py::_process_event`, `processors.py::{ExceptionRenderer, UnicodeDecoder, _figure_out_exc_info}`, `stdlib.py::ProcessorFormatter`, `typing.py::{Processor, EventDict}`; structlog 26.1.0 narrative docs `processors.html` / `standard-library.html`; the product's `config.py::setup_logging`, `utils/url_sanitizer.py`, `utils/__init__.py`, and an AST census of all `logger.*` calls in `src/`.

**`B6-R1` — a fresh event dict per record is contractual; only its *values* are shared. In place, assign — never mutate a value. [verified-by-reading + verified-by-execution]**
`BoundLoggerBase._process_event` does `event_dict = self._context.copy(); event_dict.update(**event_kw)` **per call**, then threads that one dict through the chain. The 26.1.0 docs state it outright: *"You're explicitly allowed to modify the `event_dict` parameter, because a copy has been created before calling the first processor."* Measured through the configured chain with a probe holding a strong reference to each dict: two records from one bound logger get **distinct dict objects**; dict-level mutation (add/replace keys) does **not** leak back into `bound._context`; **but the bound `list` value is the same object in every record**, and appending to it inside the processor leaked straight into the bound context *and* into later records. ⇒ **the copy is shallow, so in-place mutation of the dict is safe and in-place mutation of a value is a real bug.** `cache_logger_on_first_use=True` caches the *proxy logger and the processor tuple*, not the dict — it does not change this. **Shape:** iterate `event_dict.items()`, and only ever **rebind** `event_dict[key] = ...`; never `.append`, never `value[k] = …`, never insert into a collection. This is also structlog's own idiom — `UnicodeDecoder`, `TimeStamper`, `add_log_level`, `merge_contextvars` and `ExceptionRenderer` all mutate in place and return the same dict, and `UnicodeDecoder.__call__` is the exact shape (iterate, rebind `str` values, return `event_dict`). A new-dict comprehension is equally legal (`Processor` allows `Mapping`) and would also be safe; in place is preferred for idiom-matching, and the typing cost is nil either way.

**`B6-R2` — `format_exc_info` removes `exc_info` **by key** and writes a `str`; it is an `ExceptionRenderer` **instance**, not a function. [verified-by-reading]** `ExceptionRenderer.__call__` is `event_dict.pop("exc_info", None)` → `_figure_out_exc_info(...)` → `event_dict["exception"] = self.format_exception(exc_info)`. So: the key is **removed from the dict** (by key, not by reference — nothing downstream can see `exc_info`); `exc_info=False` is popped too; `_figure_out_exc_info` accepts a `BaseException`, a 3-tuple, or truthy (→ `sys.exc_info()`); the default `_format_exception` returns **one `str`** with embedded `\n`. `structlog.processors.format_exc_info` is the module-level singleton `ExceptionRenderer()` — so a chain-position test must identify it by `type(...) is ExceptionRenderer` or identity, never `__name__` (confirmed: instances expose no `__name__`; `merge_contextvars` / `add_log_level` / `format_exc_info` are the only plain functions).

**`B6-R3` (MANDATORY, `[SPEC-DEVIATION]`) — the slot is **after `UnicodeDecoder()`**, not before it. The audit's recommendation is refuted by measurement; "last before the renderer" is the load-bearing slot, not a cosmetic one.** The audit calls the two orders "behaviourally equivalent for redaction" and pins position 5. **They are not equivalent.** `UnicodeDecoder` turns `bytes` → `str`. A processor placed **before** it sees `bytes`, is not a `str`, and is skipped — so a `bytes` secret passes through **unredacted**. Measured on the configured chain with `blob=("https://cdn/x.ts?sig=SUPERSECRET").encode()`: **pre-`UnicodeDecoder` → secret present in output, `***REDACTED***` absent; post-`UnicodeDecoder` → secret absent, marker present.** ⇒ **Insert last, immediately before the conditional renderer.** Three reasons, in order: (1) it is the only slot in which every value has reached its final textual form, which is the slot the redaction rule is defined over; (2) it makes the position assertion maximally informative — three inequalities (`> ExceptionRenderer`, `> UnicodeDecoder`, `< renderer`) distinguish *all three* possible mis-orderings, whereas a pre-`UnicodeDecoder` assertion cannot distinguish "before `UnicodeDecoder`" from "before `format_exc_info`" unless it also pins `UnicodeDecoder`; (3) there is no cost — `UnicodeDecoder` has no ordering interaction with the redaction rule. **Update AC-4 to assert all three inequalities**, and correct plan 17's "exactly one free slot, position 5".

**`B6-R4` — the conditional-expression renderer has no consequence. [verified-by-reading + verified-by-execution]** `structlog.configure(processors=[…, JSONRenderer() if settings.log_file else ConsoleRenderer()])` evaluates the conditional **once, at `setup_logging` call time**, producing a plain list; `structlog.get_config()["processors"]` is a `list` and there is exactly **one** `structlog.configure` in `src/` [measured]. A processor inserted before that element is an ordinary list element; the expression is evaluated before `configure` ever sees the list. Nothing about it constrains, reorders, or hides the insertion. (The reason it *matters* is different and is `B6-A9`'s: it is what makes renderer-subclassing strictly less assertable than a sibling processor — it forces two renderer classes and collapses AC-4 to "is it last", which cannot distinguish before/after `format_exc_info`.)

**`B6-R5` — `ProcessorFormatter` is the correct remedy for the third-party gap and is **out of scope for `B6`**. Reject with reason, not by default. [verified-by-reading + verified-by-execution]** It *works*: measured, a foreign `logging.getLogger("third.party").exception(...)` carrying a signed CDN url came out `***REDACTED***` under `ProcessorFormatter(processors=[TimeStamper, format_exc_info, <redactor>, JSONRenderer()], foreign_pre_chain=[add_log_level])`. But adopting it requires **three** things, none of which is "insert one processor":
- **It replaces the renderer.** `ProcessorFormatter.wrap_for_formatter` *must be the last processor* in the structlog chain (docstring, verbatim), so `config.py`'s `JSONRenderer()/ConsoleRenderer()` expression is **deleted** and moved into the formatter — a structural change to the renderer's identity and location, which is precisely the assertability `B6-A9` chose a sibling processor to preserve.
- **It requires handler wiring `logging.basicConfig` does not do.** `basicConfig(format="%(message)s", …)` installs a plain `logging.Formatter`, not a `ProcessorFormatter`; `config.py` must stop relying on `basicConfig`'s formatter or call `handler.setFormatter(…)` on the root handler after the fact.
- **It leaks `_record` unless you remember `remove_processors_meta`.** Measured with the formatter's *own* structlog record and no `remove_processors_meta`: the JSON gained `"_record": "<LogRecord: m.pf, 40, <stdin>, 24, \"{'url': 'https://a?sig=SUPERSECRET', …}\">"` and `"_from_structlog": true` — **the unredacted kwargs, verbatim, inside the serialised `LogRecord` repr.** A naive adoption would *introduce* a `SEC-007` leak.

⇒ **Verdict: out of scope; hand onward.** The reason is not "it is a different block" — it is that every change it forces lands on records **this product does not emit** (foreign records) and on the **wire format of records it does** (renderer identity + schema), while `B6`'s mandate is one inserted processor and no other change. It also carries a live regression surface this plan cannot test for free (`progress_display._repoint_log_handlers` iterates root `StreamHandler`s). `B6-A4`'s residual stays open; record it with the measured `_record` leak as the cost of getting it wrong, and note that `B7` (marked carriers) already shrinks the exposure from the other side.

**`B6-R6` — `D-7` confirmed at **`Alt B`** (every `str` value), and the structural-key set is **four** keys, not three. [verified-by-execution]** Census of all `logger.*` calls in `src/`: **132 calls / 60 distinct keys** (the audit's 56 has drifted by four — the re-count oracle must assert against a fresh census). The **complete** set of keys structlog itself injects into an event dict is measurable, and it is: `event` (every call), `level` (`add_log_level`), `timestamp` (`TimeStamper`), `exception` (only when `exc_info` was present, post-`format_exc_info`), and **`correlation_id`** — injected by `utils/correlation.py::bind_correlation_id` via `structlog.contextvars.bind_contextvars`, an 8-char lowercase hex `str`. There are **zero** `logger.bind()` sites and **zero** logger calls with more than one positional arg, so `positional_args` never appears. ⇒ **The denylist is `{"event", "level", "timestamp", "correlation_id"}`** — a **frozen `frozenset` module constant beside the processor.** `correlation_id` must be in it for the *same reason* as `event`: log queries group by it, and transforming it would break trace correlation — a semantic corruption, not a false redaction (an 8-hex-char string matches none of the three rules; the audit's `event`/`level`/`timestamp` entry is needed for exactly the same reason, and it is needed).
**Deny-list vs structural exclusion:** a denylist is the **only** shape compatible with `Alt B`. Excluding those keys "by construction — never visited" is not available: a processor cannot know which keys a preceding processor added except by name, and iterating a fixed key set *is* `Alt A`. So: denylist, expressed as the comprehension/rebind guard `if key not in _STRUCTURAL_KEYS`. Make it checkable by asserting the denylist equals the measured injected set — that test fails the moment a fifth processor that adds a key lands, which is the drift alarm this block needs.
**Keys the audit's `Alt A` allowlist (`error`/`exception`/`path`) misses that carry filesystem paths:** **`output`** × 5 (`starting_download`, `starting_ytdlp_download`, `starting_segment_download`, `merge_completed`, `ytdlp_download_completed`), **`url_file`** × 1 (`batch_download_failed`), **`repo_root`** × 1, **`working_dir`** × 1. **`output` and `url_file` are user-chosen** — a user can legitimately name an output file `vk_cookies_x.cookies.txt` or a batch file a URL-shaped string, and `Alt A` would log it verbatim. That is a *concrete present-day* argument for `Alt B`, not only the abstract "a future record may name its payload something else". `Alt B`'s cost on those keys is bounded and already accepted by `B4`: it only fires when the value literally bears an `http(s)://` run or the artefact shape. **Allowlist confirmed as complete for exception text: `error` × 25, `exc_info` × 5 → `exception`, `path` × 8 — and nothing else in the 60 keys carries exception text.** [verified-by-reading]

**`B6-R7` — non-`str` values: gate on `isinstance(value, str)`, and `None` is a real input. [verified-by-execution]** Measured through the configured chain on the candidate processor shape, **never raises** on `None`, `int`, `bool`, `float`, `bytes`, or an arbitrary `object`; silently passes through `list`, `dict`, `tuple`. `None` is not hypothetical: `ytdlp_not_found::path=exc.filename` (`FileNotFoundError.filename` is `str | None`), `primary_error` (`exc_type.__name__ if … else None`, × 2), `height`, `width`. No special-casing, no `try`. One named side effect: **`isinstance` is `True` for `StrEnum` members** (`playlist_type`, `reason`, `status.value`), and `re.sub` returns a plain `str`, so the field's *type* narrows from the enum member to `str`; the rendered output is byte-identical (measured: `S(R.A) == R.A`, both render `all_addresses_non_hls`). Accepted, and name it in the docstring rather than guarding against it.

**`B6-R8` — the residual: list/mapping payloads are not recursed into, and exactly one live instance exists. [verified-by-execution]** Only **one** enumerated record carries a collection: **`captured_m3u8_urls`** (`extractor.py`), `urls=[_strip_auth_params(u) for u in monitor.m3u8_urls]` — a `list[str]`, elements pre-sanitised at the call site, and each element is a verified fixed point. Other collections in the census are inert: `hosts` (netloc only), `available` / `qualities` (quality labels), `failed_indices` (ints). **There is no `dict`-valued record field anywhere in `src/`** — the mapping half of the residual has **zero** live instances. `cli.py`'s `valid_vars` is **not** a record field: it is a local list consumed by `typer.echo` in the preamble, never logged. ⇒ **Decide: close the residual by *recursion*, not by hand-on.** A depth-1 recursion that rebinds `str` elements of `list`/`tuple` and `str` values of `dict` (building **new** containers — never in place, per `B6-R1`) is ~6 lines, makes the residual empty for every shape the census can produce, and costs nothing measurable. **If the Planner declines recursion, the residual must be recorded as "a record whose payload is a list or mapping is not transformed; the one live instance is covered only because its elements are pre-sanitised at the call site" — which is a coverage claim resting on 33 call sites staying correct, i.e. exactly the per-site property this block exists to eliminate.** My recommendation is recursion, on that ground.

**`B6-R9` — event-name-agnosticism is structural, and mechanically checkable. [verified-by-execution]** The candidate function's body iterates `event_dict.items()` and rebinds values; it receives `event_dict` and never reads `["event"]` (denylisted), so **there is no name to branch on** — plan 13's `code=1`→`code=3` re-coding changes *which record is emitted*, not *how any record is transformed*, so coverage is invariant by construction rather than by intent. Make it checkable three ways: (1) **behavioural** — two records with *different* names and the *same* value produce identical output; (2) **differential** — the 60-key census's names are irrelevant to the transform, so a synthetic novel key must be redacted (this is the property `Alt A` fails, and the test must exist to keep the choice honest); (3) **source/bytecode** — `inspect.getsource` of the processor plus its module contains **none** of the enumerated record names. Measured: **all 30 audited names are absent from `utils/url_sanitizer.py` today**, so the assertion passes as written. Caveat to state in the test: assert the *enumerated record names*, not the bare word `event` — `url_sanitizer.py` already contains `event` as a substring in prose, and a naive assertion would false-positive.

**`B6-R10` (MANDATORY, `[SPEC-DEVIATION]`) — `[:200]` truncation is **not** a fixed point, AC-6 as written is **false**, and `sanitize_text_for_log` is **monotonically non-expanding but not truncation-stable**. [verified-by-execution]** `B4-R7` justified the `[:200]` truncation on the grounds that the rules are monotonically non-expanding. That holds for untruncated input; **it does not hold across a truncation boundary**, which is a new input shape the `B4` corpus did not contain, exactly as suspected.
- **Measurement 1 — exhaustive:** `S(raw)[:n]` for every truncation point of 5 secret-bearing shapes × 8 fillers → **7812 cases, 3384 (43%) not fixed points.** Every single violation comes from the **URL** rule and **every one expands the value**: cutting inside a redacted run `https://host/***REDACTED***` leaves a shorter *still-valid* `https?://` run, so the next pass appends `/***REDACTED***`. **Zero artefact-rule violations** — the `***REDACTED***` marker and the artefact shapes are truncation-stable, so `B4`'s artefact reasoning survives intact and the exposure is **URL-only**.
- **Measurement 2 — the real shape:** `error=sanitize_text_for_log(x)[:200]` on **400 randomly generated realistic ffmpeg transcripts** (artefact temp path + 1–6 signed-CDN `GET` lines + artefact dir) → **373 / 400 (93%) are changed by one processor pass, and 373 exceed 200 characters** (up to 215).
- **Safety is not compromised; the acceptance criterion is.** The change is *strictly* in the direction of more redaction — no secret is ever revealed. And the processor output is **convergent**: a third pass changes nothing in **400 / 400**. So the pipeline is stable after one processor pass; it is simply not a **no-op** on pass 1 for a truncated URL.
⇒ **AC-6 must be reworded, and this is a spec correction the Planner owes, not an implementation detail.** As written ("`batch_merge_failed` and `final_merge_failed` come out **unchanged**") AC-6 is **93% false** on realistic input. Replace it with the three claims that are actually true and testable: **(a)** the processor never *reduces* redaction — for any input `x`, `S(x)` contains no rule-match that `x` did not; **(b)** the processor output is a **fixed point** — `S(S(x)) == S(x)` for the processor's own output; **(c)** the value's length may exceed 200 — assert the *pre-processor* input is bounded, not the output, and state that `[:200]` is an input bound. Keep a positive idempotency fixture too, on the one pre-sanitised value that is **not** truncated — `ytdlp_downloader`'s `download_failed` (`error=sanitize_text_for_log(error_msg)`, no slice) — where AC-6 holds as written and the double-transform property is genuinely exercised.

**Corrections to `B6-AUDIT` carried by this section:** `B6-A4`'s "behaviourally equivalent, position 5 is safe" → **`B6-R3`**, refuted; the slot is after `UnicodeDecoder()`. `B6-A7`'s denylist of `event`/`level`/`timestamp` → **`B6-R6`**, incomplete: `correlation_id` is a fourth structural key. `B6-A7`'s 56-key census → **60** keys, 132 logger calls. `B6-A11`'s test 7 ("idempotency against all three pre-sanitised sites") → **`B6-R10`**: the two `[:200]` records cannot be idempotency fixtures in the literal sense; reword per (a)/(b)/(c) above. `B4-R7`'s "the `[:200]` truncation stays safe" is **true for artefacts and false for URLs** and needs that qualifier wherever it is cited. Nothing in `B6-A1`–`A3`, `A5`, `A6`, `A8`–`A11` is contradicted.

**Module and visibility — I concur with the constraint, with one addition. [verified-by-reading]** Extend `utils/url_sanitizer.py`: it already owns the whole redaction policy (the three regexes, the marker, the ordering law, the idempotency proof) and `sanitize_text_for_log` is the function the processor *is*; a second module splits one policy in two and forces a `tests/test_packaging.py` frozenset edit in the same commit. The "naming debt" objection is real but small, and it is answered by naming the function for what it does — `redact_log_event` / `sanitize_event_dict_for_log` — and by one docstring line stating that the module now holds both the text transform and the event-dict transform over that same policy. **On visibility: do not re-export from `utils/__init__.py`.** `config.py` imports `from vkdownloader.utils.url_sanitizer import …` by module path; `utils/__init__.py` currently re-exports only *call-site* helpers (`sanitize_url_for_log`, `validate_output_path`, …) and is not the aggregator `config.py` uses — adding a pipeline-config symbol there would put it in the package's public surface for every importer, and `utils/url_sanitizer.py::__all__` already exists as the module's own declaration point, which is where the new name belongs. So the name is **public on the module path** and simply not re-exported: `B6-D3` resolves as *public name, module-path import, no `__init__.py` change*. **"Public" here is a plan-level decision** (`B6-A6`: `config.py` is in no layer bullet; `__all__` already lists two underscore names) — recording that a non-underscore name on the module path satisfies both the entry-adjacent reading and the package's existing convention, at zero re-export cost.

**Risks.** (1) **Over-redaction of an operator message** — measured zero instances across 60 keys / 132 calls, and bounded to values literally bearing a URL or the artefact shape; the accepted case is a user-chosen `output`/`url_file` name that looks like an artefact, which is the shape the control exists to hide. (2) **`StrEnum` type narrowing** (`B6-R7`) — rendered output unchanged, type of the field changes. (3) **Cost on the hot path** — three `re.sub` passes per string value on every record; the patterns are anchored and short, and the product logs at human rates, so this is a non-issue, but it is a real per-record cost that `Alt A` would have paid 25 times less often. (4) **`[:200]` growth** (`B6-R10`) — a redacted merge error can render ~215 chars; cosmetic, but it means "200" is no longer a true bound on the logged field. (5) **The third-party gap stays open** (`B6-R5`) until someone adopts `ProcessorFormatter` correctly, with `remove_processors_meta`. (6) **Test fragility from `cache_logger_on_first_use=True`** — `B6-A11`'s warning stands: assert on `structlog.get_config()["processors"]`, and bind loggers *after* `setup_logging`.

**Edits made by this research: one.** `#### B6-RESEARCH` inserted into this file, in the `B6` region immediately after `#### B6-AUDIT` and before `### `B7``. No code, test, plan-11, or other audit-phase file was read-modified; nothing staged or committed; every `src/` and `tests/` file is untouched.

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

#### `B7-AUDIT` — block-`B7` audit findings (Auditor; read-only at `3778e13`)

**Baseline re-measured at `3778e13` and adopted as given:** 887 passed, 3 skipped (all three named `killpg`) · `mypy src` clean (31 files) · `ruff check src tests` clean · `ruff format --check src tests` clean (54 files) · `mypy src tests` 93 errors in 8 files. [verified-by-execution] **The D-11 oracle floor is 0 — `B3` converted all three.** Nothing staged or committed; every `src/`, `tests/` and other audit-phase file untouched. All measurements below were made either by reading the live tree or by applying the candidate change to a **discarded copy** of `src/` under `.audit-scratch/` (since deleted; `git status` restored to its briefed state).

**`B7-A1` (MANDATORY, `[SPEC-DEVIATION]`) — the site count is 1 construction, not 2, and the "second site" does not exist. `T-B7` step 1 and plan 17 §`B7` item 3 both say "two `HLSDownloadRequest` constructions".** AST census of every `ast.Call` whose callee is `HLSDownloadRequest`, across all 31 `src/` files [verified-by-execution]:

| Symbol | Site | Class |
|---|---|---|
| `HLSDownloadRequest` | class def, `models/dtos.py` | declaration |
| `HLSDownloadRequest` | **1** construction, `services/ytdlp_downloader.py::_attempt_segment_resume` | **construction** |
| `HLSDownloadRequest` | 0 constructions in `services/downloader.py` | — |
| `DownloadPolicy` | class def, `services/segment_downloader.py` | declaration |
| `DownloadPolicy` | **1** construction, `services/segment_downloader.py::_run_download_session` | **construction** |

**Cause, dated:** `d572d96` ("TRN-001: Remove FFMPEG download transport") deleted `downloader.py`'s `HLSDownloadRequest` construction — it lived inside the `case DownloadMethod.FFMPEG:` arm of `perform_download`, whose fallback path called `download_hls_with_resume(HLSDownloadRequest(...))`. `git log -S "HLSDownloadRequest(" -- src/vkdownloader/services/downloader.py` returns `d572d96`, `665c6ac`, `9d7896c` — the last of which *added* it. `downloader.py` today contains **zero** references to the class; it only re-exports `download_hls_with_resume` and `_attempt_segment_resume` as backward-compat names. ⇒ **`files` must drop `src/vkdownloader/services/downloader.py` entirely** (it is currently `targets: modify` with anchor "the `HLSDownloadRequest` construction site", which does not exist), and the four-site figure becomes **three**: one construction, one `DownloadPolicy` construction, one consumer. Per plan 11 §6.4's own rule — "a different count is an `Auditor` finding" — this is recorded as one. It also **reduces** the block's risk: the finding's stated worst case ("a missed construction site is a `TypeError` at runtime on the primary download path") is half the measured surface.

**`B7-A2` (MANDATORY, `[SPEC-DEVIATION]`) — `T-B7` step 1's "the value read at **1** consumer" is wrong in a way that matters: the read is at **two** sites, and they are not the same kind of site.** [verified-by-execution] AST walk of every `ast.Attribute` named `cookies`/`headers` in `src/`:

| # | Site | Kind |
|---|---|---|
| 1 | `segment_downloader.py::download_hls_with_resume` — `if request.cookies:` | **truthiness test** |
| 2 | `segment_downloader.py::download_hls_with_resume` — `headers["Cookie"] = request.cookies` | **pass-through into an aiohttp headers mapping** |
| 3 | `segment_downloader.py::_download_segment_concurrent` — `policy.headers` (positional arg to `_download_segment`) | **pass-through** |

Sites 1 and 2 are adjacent lines in one function and are really one consumer, but plan 11's "1" does not distinguish the **truthiness test** from the **assignment**, and those two have different semantics under `SecretStr` (see `B7-A4`). Site 3 is a site plan 17 §`B7` item 3 omits entirely: `policy.headers` is read at `_download_segment_concurrent` and forwarded into `_download_segment(..., policy.headers, ...)`, which threads it through four further functions (`_download_segment_parallel`/`_sequential` → `_try_single_download_attempt` → `_run_parallel_download_with_backoff` → `session.get(segment_url, headers=headers, ...)`). **`DownloadPolicy.headers` is therefore not read at one place; it is read once and passed through four hops to the wire.** Under the chosen remedy (`field(repr=False)`) none of that changes — but the enumeration in `files.semantic_anchors` must name `_download_segment_concurrent` and `_download_segment`, or an Implementor will edit the wrong function.

**`B7-A3` — the complete carrier enumeration, and which fields are genuinely session values.** `models/dtos.py` declares **one** model; `models/enums.py` declares **nine** enums and **none carries a session** [verified-by-reading, verified-by-execution]:

| Class | Field | Current annotation / default | Genuinely a session? |
|---|---|---|---|
| `HLSDownloadRequest` | `video_url` | `str` (required) | **No** — page URL, and every log site already `_strip_auth_params`'s it |
| `HLSDownloadRequest` | `m3u8_url` | `str` (required) | **No** — CDN address; signed, but a *URL*, already `B4`/`B5`/`B6`'s subject, and `SEC-006`'s |
| `HLSDownloadRequest` | `output_file` | `Path` (required) | **No** — user-chosen filesystem path |
| `HLSDownloadRequest` | `quality` | `str = "best"` | **No** — user selection token |
| `HLSDownloadRequest` | **`cookies`** | **`str \| None = None`** | **YES** — a flat session string, `"; ".join(f"{name}={value}")` by `extractor.py::_format_cookies_for_ffmpeg` |
| `HLSDownloadRequest` | `progress_callback` | `Callable[[str, int, int], None] \| None = None` | **No** |

| Class | Field | Current annotation / default | Genuinely a session? |
|---|---|---|---|
| `DownloadPolicy` (`@dataclass`) | `session` | `aiohttp.ClientSession` | **No** — the connection pool |
| `DownloadPolicy` | `semaphore` | `asyncio.Semaphore` | **No** |
| `DownloadPolicy` | **`headers`** | **`dict[str, str]`** (required, no default) | **YES, conditionally** — carries `"Cookie"` *only when* `request.cookies` was set at construction; otherwise it is `{"User-Agent", "Referer"}` |
| `DownloadPolicy` | `max_concurrent_downloads` … `progress_callback` (9 more) | see `B7-A2` | **No** — none is credential material |

Two consequences the plan does not state. (a) **`headers` is a mixed-tenant field**: it holds credential material on the authenticated path and no credential material on the anonymous path, so it is not "a secret field" so much as "a field that sometimes holds one" — which is precisely the case a blanket `repr=False` handles and a blanket `SecretStr` could not (a `dict` cannot be one). (b) `models/enums.py` carries **no** session, so plan 11's enumeration is complete: there is no third carrier hiding in an enum. `CookieSource` (`NONE`/`BROWSER`) and `DownloadMethod` select *how* to acquire a session; they never hold one.

**`B7-A4` — the breakage surface, measured on the installed pydantic. The headline: it is far smaller than plan 11 assumes, and one site the plan calls "a type error" is not.** Installed: **pydantic 2.13.4** (declared `pydantic>=2.0.0`), Python 3.12.1, structlog 26.1.0, aiohttp 3.14.1. [verified-by-execution]

**Serialisation — the subtle class, answered plainly.** `model_dump()` (python mode) returns a **`SecretStr` object**, not a `str`:

| Call | `cookies` field returns | Literal secret present? |
|---|---|---|
| `repr(m)` | `SecretStr('**********')` | **No** |
| `str(m)` | `SecretStr('**********')` | **No** |
| `m.model_dump()` | **`<class 'pydantic.types.SecretStr'>` instance** | **No** |
| `m.model_dump(mode="json")` | `'**********'` (plain `str`) | **No** |
| `m.model_dump_json()` | `"**********"` (plain `str`) | **No** |

⇒ **Yes, a consumer that round-trips through `model_dump()` would start emitting a `SecretStr` object where it previously emitted a `str`.** And on 2.13.4 that is the *safer* direction: the object's `repr` is masked, so a CLI that printed the dumped request would print `**********`, **not** the secret. (`model_dump_json()`'s masking is version-sensitive across 2.x minors — the `SecretStr` docstring's own `model_dump_json()` example shows `"password":"IAmSensitive"` in clear — so a JSON consumer's behaviour is not guaranteed stable across the declared range. The python-mode `model_dump()` behaviour measured here is stable for `SecretStr` and is the one that matters, because it is the one that would surprise a consumer.) **Note also that pydantic's `model_dump_json()` masking is unconditional: no `field_serializer` is needed to keep the JSON clean, and `model_dump(mode="json")` is likewise masked.**

**The other classes, each measured, not assumed:**

| Class of breakage | Measured result |
|---|---|
| truthiness (`if request.cookies:`) | **Works, but the semantics change.** `bool(SecretStr(""))` is `False` (it defines `__len__`); `bool(Secret(""))` is `True` (it does **not**). `SecretStr` is therefore safe here — but note the trap: `SecretStr` gets truthiness from `__len__`, not `__bool__`, and `Secret` would have been silently always-truthy. Measured `if request.cookies:` is `False` for both `None` and `SecretStr("")`, matching today's `if request.cookies:` for both `None` and `""`. **No behaviour change.** |
| `headers["Cookie"] = <SecretStr>` | **Assigns fine** (a `dict` is untyped at runtime) but **fails at the wire**: driving a real `aiohttp.ClientSession` against a local server, a `SecretStr` header value raises `TypeError: Cannot serialize non-str key SecretStr('**********')`. `str`-typed `dict` annotations are not enforced at runtime, so this is a **latent** failure that mypy — not the runtime — is what catches. |
| subprocess `argv` | **Not applicable to this block.** No session value reaches `argv`: `_build_ytdlp_cli_command` passes `--cookies <path>` (a `str(cookie_file)`), never the value; the value goes into the Netscape temp file via `_cookies_to_netscape(cookies).encode()` — a `str` parameter on `_create_temp_cookie_file`, **not** a carrier this block touches. |
| temp cookie file | **Not applicable.** Same reason: `_create_temp_cookie_file(cookies: str \| list[Cookie])` receives a plain `str` from `extractor.extract_streams_with_cookies`, upstream of the DTO. |
| equality / hashing / set membership | **Breaks silently, and this is the real hazard.** `SecretStr("a") == "a"` → **`False`**; `hash()` works but is unrelated. No site in `src/` compares `request.cookies` to anything, so nothing breaks today — but a future `if request.cookies == expected:` would compare `False` with no error. `repr=False` has none of this. |
| `+` / `in` / slicing / `.encode()` / `.startswith()` / `join` / `%` | All raise `TypeError` on a `SecretStr`. **Zero sites in `src/` perform any of these on `request.cookies`** — measured by AST attribute enumeration (`B7-A2`): the only two reads are a truthiness test and an assignment. |
| **f-string / `str()` interpolation** | **Silently emits the mask.** Measured: `f"{m.cookies}"` → `**********` (via `__str__`). No site exists. |

**`B7-A5` — the mypy consequence, which is the one real cost and which the plan does not anticipate at all.** Applying the change to a copy of the tree and running `mypy` produced, first pass:

```
ytdlp_downloader.py:1024: error: Argument "cookies" to "HLSDownloadRequest" has
incompatible type "str | None"; expected "SecretStr | None"  [arg-type]
```

`mypy src` goes **clean → 1 error**, and it is at the **construction site**, not the consumer. Plan 17 §`B7`'s AC-5 and `T-B7` step 2 both assume construction is source-compatible ("`str` is coerced" — true at *runtime*, false to a *type checker*; pydantic's coercion happens inside `validate_python`, which mypy cannot see). Plan 11 §5.4 item 2 makes the same claim. **The fix is one expression, not a redesign:** `cookies=SecretStr(cookies) if cookies else None` at the single construction site. Measured: with it applied, `mypy` on the patched copy returns **`Success: no issues found in 31 source files`**, and `ruff check` / `ruff format --check` stay clean. **This is not optional** — it is the difference between AC-5 passing and failing, and it is the specific thing an Implementor will hit first.

**`B7-A6` — the "no serialisation consumer" criterion is VERIFIED, not refuted.** [verified-by-execution] AST+regex scan of `src/` **and** `tests/` for `model_dump`, `model_validate`, `model_copy`, `model_json_schema`, `model_fields`, `.dict(`, `parse_obj`, `parse_raw`, `json.dumps`. Every hit is `Settings.model_fields[...]` (a class-level default lookup, 12 sites in `config.py`/`downloader_throttle.py`/`tests/`) and one `test_settings.model_copy(update=...)` in `tests/test_hls_downloader.py`. **Zero** call sites dump or serialise `HLSDownloadRequest`. Independently: the only `BaseModel`s in `src/` are `Settings`, `HLSDownloadRequest`, `QualitySpec`, `Video`, `Stream`; none is a Typer command parameter, an API response model, or a CLI-printed object (`cli.py`'s `typer.echo` calls take `str`/`Path` only). ⇒ **The criterion holds; `B7` is not blocked.** Report it as **verified**, with the caveat that it holds *today* and `B7` is what keeps it true — adding a `--debug-print-request` or a JSON diagnostic would be the first consumer, and under `SecretStr` it would emit a mask (safe) while under `repr=False` it would emit the secret in clear. **That asymmetry is the whole argument for `SecretStr`, and it is measurable, not speculative.**

**`B7-A7` — RECOMMENDATION: `SecretStr` on `cookies`, `field(repr=False)` on `headers`. Keep both. Do not substitute `repr=False` for `SecretStr`.** This is the block's decision point and the recommendation is unchanged from plan 11's default — but it now rests on measurement rather than on "Pydantic-native":

1. **`repr=False` alone does not close `SEC-008`'s stated scope.** Measured: `Field(repr=False)` leaves `cookies` a plain `str`, so `repr`/`str` are clean but **`model_dump()` and `model_dump_json()` both emit the secret in clear** (verified: `"SUPERSECRETVALUE" in repr(m.model_dump())` → `True`; same for `model_dump_json()`). Plan 17's own `Goal` names `model_dump_json()` as one of the three renderings that currently leak. `repr=False` closes one of the three.
2. **`repr=False` does not survive the one careless act the finding is about.** Measured against the **real configured chain** (`B6`'s `redact_log_event` at position 6, `JSONRenderer`): `logger.debug("field_dump", cookies=<the field>)` emits `{"cookies": "remembmer_me=abc123def; sid=9876zyxw"}` under `repr=False` — the session, in clear, in the log file. Under `SecretStr` the same call emits `{"cookies": "SecretStr('**********')"}`. **`B6` cannot catch it**: measured, `sanitize_text_for_log("remembmer_me=abc123def; sid=9876zyxw")` is the **identity** — its only two rules are an `https?://` run and the two `vk_cookies_*` artefact literals, and a flat session string matches neither. So a future `logger.debug(..., cookies=request.cookies)` is leaked in full by `repr=False` and masked by `SecretStr`. **`repr=False` protects the container; `SecretStr` protects the value.** Only the value can be logged by accident.
3. **The breakage surface does not argue the other way.** Every string operation, the `argv` path, the temp-file path, equality and hashing are **unused today** (`B7-A4`), and the full suite measured **887 passed / 3 skipped — byte-identical to baseline** against the patched copy. The only real cost is one typed `SecretStr(...)` wrapper at one construction site (`B7-A5`). That is a **trivial** effort, not a medium one.
4. **House rule 11 (Pydantic for all models) makes `SecretStr` the idiomatic choice**, and `field(repr=False)` is the correct choice for `headers` **precisely because a `dict` cannot be a `SecretStr`** — that half of plan 11's `D-8` is right and should not be re-litigated.

⇒ Verdict: **the breakage is acceptable, and the change is smaller than plan 11 estimated** (1 construction, not 2; 3 sites, not 4). Effort **trivial**. Priority **recommended** (advisory, per `SEC-008`'s own classification). Reject the plan's stated alternative `"Field(repr=False) on cookies - rejected: hides the field but leaves a plain str"` only in its *reasoning*: the reason is not "Pydantic-native", it is **"`Field(repr=False)` leaves `model_dump()`/`model_dump_json()` in clear and leaves the value loggable in full, and `B6`'s transform provably does not match a flat session string."** Record that, so the choice survives the next reader.

**`B7-A8` — `B6`'s finding is confirmed independently, and it materially narrows this block's value proposition. Say so honestly.** [verified-by-execution] I re-derived `B6-A8` rather than trusting it: full census of every `logger.*` keyword in `src/` (60 distinct keys, 132 calls, matching `B6-R6`), then filtered every key **name** and every value **expression** for `cookie|session|auth|token|header|policy` and for `request.cookies`/`policy.headers`. **Total hits: 0.** The only `request`/`policy`-touching record is `starting_segment_download`, which reads `request.video_url` (already `_strip_auth_params`'d), `request.output_file` and `request.quality` — **not** `request.cookies`. **No log record anywhere in `src/` carries a session, and `B6`'s landed processor is not what prevents one: the product simply never logs one.** ⇒ **The "log line" half of `SEC-008` is already closed, and was already closed before `B6` landed.** What remains for `B7` is (i) the **repr** half, and (ii) **defence in depth for future records** — and `B7-A7` item 2 is precisely the evidence that (ii) is real and is the part `B6` cannot supply. **So the block is materially narrowed but not hollow:** it is reduced from "close a leak" to "make a leak structurally unavailable", and that is the honest framing for the commit message. Do **not** let the Implementor write a commit message claiming a log-line leak was closed.

**`B7-A9` — `ProcessorFormatter`: `B7` must NOT absorb it. Leave it, and record it with its measured cost.** `B6` has **landed** (`200ae51` `fix(logging): redact secret-shaped text on the log pipeline`, plus `3f1edf5`, `3b5f517`), so the premise is live, not hypothetical: `config.setup_logging` still calls `logging.basicConfig(format="%(message)s", handlers=[StreamHandler|FileHandler])` and installs **no** `structlog.stdlib.ProcessorFormatter`; `src/` contains **zero** `logging.getLogger(...)` module loggers, so the product's own records are unaffected, while `playwright`/`yt_dlp`/`aiohttp`/`urllib3` log to that same root handler unprocessed. The remedy **works** (structlog 26.1.0's `ProcessorFormatter` accepts `foreign_pre_chain` and a processor list), but it is a **structural** change, not a one-line insertion, and `B6-R5`'s three costs are confirmed on the installed version: `ProcessorFormatter.wrap_for_formatter` must be the **final** processor (so `config.py`'s conditional `JSONRenderer()/ConsoleRenderer()` expression is deleted and relocated, changing the renderer's identity and location — the very assertability `B6` chose a sibling processor to preserve); `basicConfig` installs a plain `logging.Formatter`, so the handler must be re-wired after the fact; and **`remove_processors_meta` is not optional** — without it the JSON gains a `_record` key carrying the serialised `LogRecord` repr, **including unredacted kwargs**, which would *introduce* a `SEC-007` leak. ⇒ **Verdict: out of `B7`'s scope, for the reason `B6-R5` gave and not by default.** Blast radius: it changes the rendering of **every** third-party log line in the product and the wire format of every record the product emits, against a block whose stated scope is two field annotations in two files. It also collides with `progress_display._repoint_log_handlers`, which iterates root `StreamHandler`s. **Action: `B7` records the residual in its commit message and hands it onward as its own block.** Effort when scheduled: **medium**. Do not schedule it inside this plan without a Product decision.

**`B7-A10` — the tests, specified precisely.** Three new tests, all in files that already carry `mypy src tests` errors (so the ≤ 93 delta gate applies to them).

1. **The repr oracle — the property the block exists to establish, and it must fail if `repr=False`/`SecretStr` is removed.** Build an `HLSDownloadRequest` with a **literal, distinctive** secret and assert its **substring** is absent from **each** of the three renderings named in the plan's own `Goal`: `repr(request)`, `str(request)`, `request.model_dump_json()`. Use a literal like `"B7CANARY-SESSION-VALUE-DO-NOT-LOG"` and assert `assert CANARY not in repr(request)` (and the same for the other two) — **not** `assert "cookies" not in repr(...)`, which would pass vacuously if the field were merely renamed, and **not** a "no field appears" check. Add the same shape for `DownloadPolicy`, asserting the canary is absent from `repr(policy)` **and** that `policy.headers["Cookie"] == CANARY` still holds — one test, two properties, so the field cannot be satisfied by deletion.
2. **The log-record oracle.** Through the **configured** chain (`config.setup_logging(settings)`, then `structlog.get_logger`), emit a record that carries the carrier as context — `logger.debug("b7_probe", request=request)` — and assert the canary is absent from the rendered output. This is the test that fails under `repr=False` and passes under `SecretStr` (`B7-A7` item 2), so it is what makes the choice between the two mechanisms **executable** rather than argued. Assert on the canary substring, and capture with a handler attached to the root logger (`B6-A11`'s warning applies: `cache_logger_on_first_use=True` means a logger bound before `setup_logging` keeps its cached chain — configure first).
3. **The retrievability oracle, and it is not optional.** Assert `request.cookies.get_secret_value() == CANARY` and that the segment path still sends it: drive `download_hls_with_resume` (or its narrowest seam — the existing tests already stub `_fetch_playlist_with_retry` / `_download_segment_concurrent`) and assert the captured `headers["Cookie"]` equals the canary exactly. **This is what makes the change unsatisfiable by destruction** — a block that blanked the field would pass tests 1 and 2 and fail this one. I verified this end-to-end against a live local `aiohttp` server: with the patched copy, the server received `'sid=SUPERSECRET_WIRE; a=b'` byte-for-byte. Note the `mypy` consequence of the unwrap — `request.cookies` is `SecretStr | None`, so `mypy` requires the truthiness test to precede the unwrap or it reports `union-attr` (measured).

**Existing tests that construct these models — full inventory. Measured: `B7` breaks NONE of them.** AST census of every `ast.Call` to either class in `tests/` [verified-by-execution]:

| File | Line | Enclosing test | kwargs passed |
|---|---|---|---|
| `tests/test_batch_downloader.py` | 274 | `test_segment_layer_does_not_acquire_caller_video_semaphore` | `video_url, m3u8_url, output_file` |
| `tests/test_hls_downloader.py` | 77 | `test_preserves_segments_on_playlist_fetch_failure` | `video_url, m3u8_url, output_file` |
| `tests/test_hls_downloader.py` | 113 | `test_preserves_segments_on_segment_download_failure` | same |
| `tests/test_hls_downloader.py` | 165 | `test_resume_with_all_segments_present_merges_without_download` | same |
| `tests/test_hls_downloader.py` | 1414 | `test_semaphore_limits_concurrent_downloads` | same |
| `tests/test_hls_downloader.py` | 1466 | `test_parallel_download_uses_gather` | same |
| `tests/test_hls_downloader.py` | 1531 | `test_shared_semaphore_parameter` | same |
| `tests/test_hls_downloader.py` | 1697 | `test_sequential_mode_applies_delay_after_semaphore` | same |
| `tests/test_hls_downloader.py` | 1776 | `test_sequential_mode_triggers_backoff_on_429` | same |
| `tests/test_hls_downloader.py` | 1855 | `test_parallel_mode_no_inter_segment_delay` | same |
| `tests/test_hls_downloader.py` | 1975 | `test_download_hls_with_resume_logs_segment_method` | same |
| `tests/test_hls_downloader.py` | 2793 | `test_manifest_base_url_used_for_segment_resolution` | same |
| `tests/test_segment_downloader.py` | 1246 | `test_t7_quality_threaded_from_request` | `+ quality` |
| `tests/test_segment_downloader.py` | 1451 | `TestBoundCheck`/`_make_policy` (**`DownloadPolicy`**) | `+ headers={}` (empty dict) |

⇒ **13 `HLSDownloadRequest` constructions and 1 `DownloadPolicy` construction in `tests/`; not one passes a session value.** All 13 rely on the `cookies=None` default, and the single `DownloadPolicy` passes `headers={}`. Measured full-suite result against the patched copy: **887 passed, 3 skipped, 1 warning** — identical to `3778e13`, so the "mid-flight breakage discovery" this inventory exists to prevent **does not occur**. **Zero existing tests require updating.** `tests/test_hls_downloader.py` already carries one pre-existing mypy error class; the new tests land there and count against the ≤ 93 gate, so keep them fully annotated (`-> None`, typed params).

**Edits this block needs to its own record** (all in this file; nothing else):
1. §`B7` **item 3**: "All **four** sites" → **three**; drop `services/downloader.py` from the sentence and from `files`.
2. §`B7` **item 1**: keep `SecretStr`, but replace the stated reason (`"hides the field but leaves the value a plain str"`) with the measured one (`B7-A7`): `repr=False` leaves `model_dump()`/`model_dump_json()` in clear **and** leaves the value fully loggable, and `B6`'s transform is the identity on a flat session string.
3. §`B7` **item 2**: unchanged (`field(repr=False)`), plus the `headers`-is-mixed-tenant note from `B7-A3`.
4. §`B7` **item 4**: the refresh path is `_attempt_segment_resume`'s own construction, now the **only** construction — say so.
5. §`B7` **item 5**: add the third rendering (`model_dump_json()`) to the test list, and the retrievability oracle.
6. §`B7` **AC-1**: add `model_dump_json()` and the "value still retrievable" clause.
7. §`B7` **AC-4**: "All four sites" → three; add the `SecretStr(cookies) if cookies else None` requirement — **without it AC-5 fails**, measured.
8. §`B7` **`files`**: remove `src/vkdownloader/services/downloader.py`; add `_download_segment_concurrent` and `_download_segment` to `segment_downloader.py`'s `semantic_anchors`.
9. New open decision `B7-D2` — whether to record the `ProcessorFormatter` residual in this block's commit message (recommend: yes, one sentence, hand onward per `B7-A9`).
10. Add to the commit-message obligations: `B7`'s value proposition is **defence in depth**, not a closed log-line leak (`B7-A8`); claiming otherwise would misreport `SEC-008`'s closure.

**Edits made by this audit: one.** `#### B7-AUDIT` inserted into this file, in the `B7` region immediately before `### `B8``. No code, test, plan-11, or other audit-phase file was read-modified; nothing staged or committed; `tmp/`, `tmp_old_sec*.md`, the deleted `.ai/plans/00_*`…`07_*`, `.ai/problems/PROBLEM.md`, `.kilo/commands/implement/implement-plan-multiagent.md`, untracked plans 05–08, `.gitignore`, and every `src/`/`tests/` file are untouched. The `.audit-scratch/` measurement copy and its `.out_segments/`/`out.mp4` residue were deleted; `git status` is byte-identical to its pre-audit state.

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

#### `B8-AUDIT` — block-`B8` audit findings (Auditor; read-only at `209bd77`)

**`B8-A1` (MANDATORY, `[SPEC-DEVIATION]`) — the brief's "handed to `aiohttp`" is half wrong, and the correction changes what the comment must say. The flat string has TWO consumers with opposite domain semantics; only one of them is `aiohttp`.** [verified-by-reading + verified-by-execution] Tracing `cookies_str` out of `_extract_with_browser` at `209bd77`:

1. `_extract_with_browser` returns `(streams, cookies_str, raw_cookies)`; `extract_streams_with_cookies` forwards both; `downloader.py::perform_download` binds both and passes them as `cookies=` / `raw_cookies=` to `ytdlp_downloader.download_with_ytdlp_with_resume_fallback`.
2. **`cookies_str` → yt-dlp.** `_download_with_ytdlp` builds the argv in `_build_cmd`: `if raw_cookies:` → `_create_temp_cookie_file(raw_cookies)`; `elif cookies:` → `_create_temp_cookie_file(cookies)`. `_create_temp_cookie_file` calls `services/cookies.py::_cookies_to_netscape`. On the **list** arm `_cookies_to_netscape` **preserves each cookie's own `domain`** and derives `include_subdomains` from the leading dot; on the **string** arm it writes the **hardcoded** `.vkvideo.ru` for every pair. ⇒ **yt-dlp already scopes by domain**: the Netscape file carries per-cookie domains, so `--cookies` sends a `.userapi.com` cookie only to `.userapi.com`. The string arm's hardcoding is a separate (real, but out-of-scope) fidelity bug, **not** an over-send.
3. **`cookies_str` → aiohttp.** The only place the *flat, domain-less* string becomes a wire header is `ytdlp_downloader.py::_attempt_segment_resume`: `HLSDownloadRequest(cookies=SecretStr(cookies) if cookies else None)` → `segment_downloader.py::download_hls_with_resume`: `headers["Cookie"] = request.cookies.get_secret_value()` → `_run_download_session` → `DownloadPolicy.headers` → `_download_segment_concurrent` → `_download_segment` → `session.get(segment_url, headers=headers)`. Separately, `segment_downloader.py::_fetch_playlist_with_retry` does `headers["Cookie"] = new_cookies` from `_handle_token_refresh`/`_refresh_token_and_retry` (`return address, new_cookies or ""`) — a **plain `str`**, never a `SecretStr`, so the `B7` carrier is bypassed on the 403/410 refresh path [informational only; `B8` must not touch it].

⇒ **Consequence for `B8`: the answer to "does the CDN need cookies for other domains?" is different per consumer.** The yt-dlp path **already filters by domain** and needs no decision. The aiohttp segment path sends the flat string to **whatever host the playlist resolves to** and is where an unscoped credential actually goes on the wire. The recorded decision must say **which** consumer it governs; a comment that says "the CDN" unqualified is the apology `B8` exists to prevent. §9 Q3's premise ("one undifferentiated header sent to whatever server the next media request resolves to") is accurate for consumer 3 only.

**`B8-A2` — the bounding fact re-verified, unchanged at `209bd77`. [verified-by-execution]** Tree-wide over `**/*.py`: `storage_state` **0**, `launch_persistent_context` **0**, `user_data_dir` **0**, `new_context` **exactly 1** — `infrastructure/browser.py` in `BrowserManager.create_stealth_page`, `await self.browser.new_context(...)` with `viewport`/`user_agent`/`locale`/`timezone_id` (the `# type: ignore[union-attr]` is plan-10's, untouched). The six other `new_context` hits are `AsyncMock` assignments and one docstring in `tests/test_browser_infrastructure.py`. ⇒ **The stop condition does not fire.** The context is ephemeral: created per acquire, discarded at run end, so the harvested store is **exactly what this run's own page visit set** — no persisted profile, no operator-carried cookies, no accumulation across runs. **This, and only this, is what makes "no filtering needed" defensible** — it bounds *what can be in the store*, not *what is sent*. The comment must not conflate them.

**`B8-A3` — the seam, by symbol. The harvest call cannot express a domain decision, so the only insertion point is `_format_cookies_for_ffmpeg`.** [verified-by-reading] In `services/extractor.py::VKVideoExtractor`:

| Step | Symbol | What happens |
|---|---|---|
| harvest | `_extract_with_browser` | `raw_cookies = await page.context.cookies()` — **no argument**, whole store; then `cookies_str = self._format_cookies_for_ffmpeg(raw_cookies)` inside a `try/except Exception` that logs `failed_to_capture_cookies` and continues |
| compose | `_format_cookies_for_ffmpeg` | iterates `cookie.get("name")`/`cookie.get("value")`, strips CR/LF from both, appends `f"{name}={value}"`, `return "; ".join(cookie_parts)`. **Reads only `name` and `value` — the `domain` key is present on every input dict and is never read.** |
| to aiohttp | `ytdlp_downloader._attempt_segment_resume` → `segment_downloader.download_hls_with_resume` → `_run_download_session` → `_download_segment` → `session.get` | `headers["Cookie"] = request.cookies.get_secret_value()` |

⇒ **The seam is `_format_cookies_for_ffmpeg`**, and it is the *only* correct one. `_extract_with_browser` receives the domain too, but inserting the filter there would split the logic across two functions and change what `raw_cookies` (the third return value, consumed by `_cookies_to_netscape` and by yt-dlp's domain-correct arm) contains — a behaviour change to a **different** consumer. `_format_cookies_for_ffmpeg` is a pure function of `list[Cookie]` → `str` with **one** caller (`_extract_with_browser`), so a filter added there is provably scoped to consumer 3. **The comment must name `VKVideoExtractor._format_cookies_for_ffmpeg` as the seam and say that `cookies_str`'s third consumer already scopes by domain.**

**`B8-A4` — the three options, assessed. `Alt A` lands; `Alt B` cannot be validated here; `Alt C` is now redundant and should be recorded as such.**

- **`Alt A` (the Product Owner's §9 Q3 answer — keep current behaviour, record the reason). RECOMMENDED.** Costs nothing behaviourally and closes the finding the way the store itself permits ("stating the dependency is a legitimate answer"). Its one real obligation, and the reason this audit exists: the statement must name the **seam** (`_format_cookies_for_ffmpeg`) and the **consumer** (the aiohttp segment path), or it is an apology rather than a record (`B8-A1`, `B8-A3`).
- **`Alt B` (narrow the flat header by domain suffix). REJECTED, and the rejection is structural, not a preference.** Two independent blockers, both re-verified: (i) the platform — §2's own skip **S-6** is the live-origin skip, so there is **no way to exercise a narrowed set**; the suite cannot distinguish "correctly narrowed" from "narrowed past a cookie the CDN needed", because `tests/test_extractor.py` mocks `page.context.cookies()` and asserts only string composition. A wrong narrowing therefore **breaks authenticated downloads with no local signal** — the exact failure mode §9 Q3 warns about. (ii) the evidence — no owner statement of the CDN's cookie-domain dependency exists, and `B8-A2` bounds *what can be in the store* without saying *what is sent*. `Alt B` would additionally need a `Validator` review (`EB-B8`'s roster) and a `Researcher` pass, and it would change behaviour on the one path that cannot be tested. **Do not start it.**
- **`Alt C` (add a `Cookie:` redaction rule). REDUNDANT — record it as redundant, do not land it.** Re-derived rather than inherited: `B6-A8` measured **zero** record fields in `src/` carrying a `Cookie:` header or a flat session string; `B7-A8` re-censused 60 distinct keys / 132 calls and got **0** hits for `cookie|session|auth|token|header|policy`; `models/dtos.py` now marks `HLSDownloadRequest.cookies` with `SecretStr` **and** `field(repr=False)`, so the single carrier cannot render in clear through `repr`, `str`, `model_dump()`, or a `logger.debug(request=…)`. My own sweep agrees: the only cookie-adjacent records are `extracting_streams_with_cookies` (`video_id` only), `failed_to_capture_cookies` (`error=str(e)`), `cookie_file_cleaned_up` (`path` only) — **no record carries a session**, and `url_sanitizer.py`'s docstring already states `Cookie:`/`Set-Cookie:` are **not matched** by rule, by design. ⇒ **There is nothing for the rule to redact.** `Alt C` would add a regex and a policy claim that no instance justifies — the broadening `D-5` declined and `B6-A9` recommended against. **Record: "`Alt C` was considered and is redundant given `B6`'s measurement and `B7`'s `SecretStr`; a `Cookie:` rule would match nothing today."**

**`B8-A5` — where it must be recorded, and the forbidden-file boundary. It must not go in any of the four, and it needs none of them.** [verified-by-execution] Recording location: **`_extract_with_browser`'s harvest site** (an inline comment immediately above the `try:` that wraps `raw_cookies = await page.context.cookies()`) **plus** `_format_cookies_for_ffmpeg`'s docstring. Both are in `services/extractor.py`, which `EB-B8` already declares `modify`. Nothing goes in plan 11 (historical record), nothing goes in `.ai/audit/**` (§6.6), nothing goes in `config.py` — **the decision is not a setting; there is no flag, and adding one would create the `Alt B` behaviour change under a name that reads as a no-op.**

Forbidden-file check, each verified against `209bd77` and against `B3`–`B7`'s landed commits:

| Forbidden file | Would `B8` need it? | Why not |
|---|---|---|
| `services/ffmpeg_utils.py` | **No** | Locked read-only plan-wide (§4.3, §6.4). Contains no cookie logic; `iter_process_lines` and both merge records are other blocks'. Nothing in `B8`'s scope lives there. |
| `infrastructure/network_monitor.py` | **No** | Its four record names are `B6`'s deliberate exclusion (class-name-only). `NetworkMonitor.select()` chooses the **stream URL**, not cookies — `B8` records which host that URL resolves to, which is a statement in `extractor.py` about a value this module produces. No edit. |
| `services/ytdlp_downloader.py` (cookie-lifecycle section) | **No** | `_create_temp_cookie_file`/`_build_cmd`'s `--cookies` arm is **domain-correct** for the list input (`B8-A1` step 2). The only reason to write here would be to note that fact — and it belongs in `extractor.py`, where the reader arrives. Writing it here would also collide with `B2`'s confinement of the `vk_cookies_*` artefacts. **Untouched.** |
| `config.py` | **No** | No setting is added (see above). Also already carries `B6`'s processor + `B7`'s logging work; a fourth unrelated edit there is the coupling the file-lock table exists to prevent. |

⇒ **File set admitted by the evidence: `services/extractor.py`, `tests/test_extractor.py`. None of the four. The boundary holds after `B3`–`B7`.**

**`B8-A6` — the test. Existing coverage does NOT construct a multi-domain set through `_format_cookies_for_ffmpeg`, and that is the whole gap.** [verified-by-execution] Inventory in `tests/test_extractor.py`:

- `test_format_cookies_for_ffmpeg` — 6 sub-cases (single, multiple, empty, empty name/value, CRLF ×2). **Every input dict has `name`/`value` only — no `domain` key on any of them.**
- `test_format_cookies_for_ffmpeg_all_cookies_included` — 50 synthetic cookies `{"name","value"}`, asserts `count("=") == 50`. Pins *count*, not *provenance*; again no `domain`.
- `test_browser_extraction_*` (harvest path) — two cookies, **both `domain: ".vkvideo.ru"`**. Single-domain.
- `test_cookies_to_netscape_preserves_domain` — the **only** multi-domain fixture in the file (`".vk.com"`, `".userapi.com"`, `"vkvideo.ru"`), and it tests `_cookies_to_netscape`, **not** `_format_cookies_for_ffmpeg`.
- `_extract_with_browser` tests at the capture site — `.vkvideo.ru` only.

⇒ **Missing, precisely:** no test feeds a cookie set spanning **two or more distinct domains** into `_format_cookies_for_ffmpeg`, so nothing today would fail if someone added a domain filter there — the CR/LF sanitisation and the no-truncation tests would keep passing. **`Alt B` could land today with the suite fully green**, which is the strongest available argument for the pinning test. Add exactly one, in the existing `class TestVKVideoExtractor` beside the other two:

```python
    def test_format_cookies_for_ffmpeg_keeps_cookies_from_every_domain(self) -> None:
        """SEC-010 / B8: this test PINS CURRENT BEHAVIOUR, which is the point of it.

        A cookie set spanning several domains is formatted into one flat header
        with no per-domain filtering, because no consumer has been able to state
        that the media host needs a cookie set for another domain (§9 Q3, Alt A).
        The harvest is bounded instead: BrowserManager.create_stealth_page uses
        new_context(...) with no storage_state / launch_persistent_context /
        user_data_dir, so the store holds only what this run's page visit set.

        If a future change filters by domain this test is SUPPOSED to fail. Do
        not "fix" it by narrowing the fixture or relaxing the assertion: the
        failure is the signal that a decision changed, and it must be made
        deliberately. Two consumers already scope by domain on their own
        (services/cookies.py::_cookies_to_netscape preserves each cookie's own
        domain for the yt-dlp --cookies file), so narrowing the flat header
        would change only the aiohttp segment path — and it could not be
        validated without a live run.

        See VKVideoExtractor._format_cookies_for_ffmpeg, the seam this pins.
        """
        extractor = VKVideoExtractor()
        cookies: list[Cookie] = [
            {"name": "session_id", "value": "abc123", "domain": ".vkvideo.ru"},
            {"name": "remixdsid", "value": "xyz789", "domain": ".vkvideo.ru"},
            {"name": "tracker", "value": "track-me", "domain": ".userapi.com"},
            {"name": "sid", "value": "cross-site", "domain": ".example.com"},
        ]

        result = extractor._format_cookies_for_ffmpeg(cookies)

        # Every cookie survives, regardless of domain: no filter exists here.
        assert result == (
            "session_id=abc123; remixdsid=xyz789; tracker=track-me; sid=cross-site"
        )
        # The domain never reaches the header at all - which is why the filter,
        # if one is ever added, belongs in this function and nowhere upstream.
        assert "vkvideo" not in result
        assert "userapi" not in result
        assert "example" not in result
```

The exact-equality assertion is deliberate: it pins **order and membership**, so a filter cannot pass by accident. `assert "example" not in result` is the line that fails first under `Alt B`, and it says so in the docstring.

**`B8-A7` — the comment wording I would land.** Two sites, both in `services/extractor.py`; **docstring/comment only, no executable path touched.** At `_extract_with_browser`, immediately above the `try:` that wraps the harvest:

```python
            # SEC-010 / B8. The harvest is the WHOLE context store
            # (page.context.cookies() with no argument) and is deliberately
            # NOT filtered by domain. Recorded decision (§9 Q3, Alt A):
            # "no consumer of this header has stated that the media host needs
            # a cookie set for a domain other than its own, and the absence is
            # not a licence to invent one."
            #
            # WHY THAT IS SAFE, bounded by evidence, not preference:
            #   - BrowserManager.create_stealth_page builds this context with
            #     new_context(viewport=..., user_agent=..., locale=...,
            #     timezone_id=...) and the tree contains no storage_state, no
            #     launch_persistent_context and no user_data_dir. The context is
            #     ephemeral, so this store holds ONLY what this run's own page
            #     visit set - no persisted profile, nothing carried in from the
            #     operator's browser, no accumulation across runs.
            #   - The origin genuinely needs whatever it set; narrowing on a
            #     guess is the failure mode, and this header cannot be narrowed
            #     and validated on any platform available here (no live origin).
            #
            # WHICH CONSUMER THIS GOVERNS (the two are not the same):
            #   - yt-dlp: cookies.py::_cookies_to_netscape preserves each
            #     cookie's own domain for the --cookies file, so that path
            #     already scopes by domain.
            #   - aiohttp segments: cookies_str reaches the wire as one flat
            #     "name=value; ..." header via HLSDownloadRequest.cookies ->
            #     download_hls_with_resume's headers["Cookie"], sent to whatever
            #     host the playlist resolves to. THAT is the unscoped path.
            #
            # THE SEAM, if a future phase ever narrows this: the filter belongs
            # in _format_cookies_for_ffmpeg (below) - the one pure function that
            # sees the domain and drops it. Do not filter here instead: raw_cookies
            # also feeds yt-dlp's domain-correct arm, so filtering here would
            # change a consumer that is already right.
            #
            # REVISIT IF: storage_state / launch_persistent_context /
            # user_data_dir appears anywhere in the tree (the store stops being
            # ephemeral and this reasoning expires), OR an owner or a live
            # observation states which cookie domains the media host actually
            # requires - either one replaces this comment with the narrow set and
            # a test that demonstrates what is kept and what is dropped.
```

And in `_format_cookies_for_ffmpeg`'s docstring, replacing the current bare sentence *"Includes all cookies to ensure proper CDN authentication."* — which names a **consumer** and not a **dependency**, and is the actual defect:

```
        Includes every cookie from the browser context store, from every domain,
        with no per-domain filtering - see SEC-010 / B8 and the harvest site in
        _extract_with_browser for the recorded decision, the evidence bounding
        it, and the conditions that would invalidate it. The cookie's ``domain``
        key is available here and is deliberately not read: this is the seam a
        future narrowing would be inserted at, and this function is the only
        place the domain is available to it. The method name references the
        retired ffmpeg transport and is a known misnomer; the rename belongs to
        the removal track and is out of scope here (§6.11).
```

**`B8-A8` — verify-afterwards checklist, each item and how `B8` satisfies it.** (1) *Answerable from code* — `B8-A7`'s comment answers it with the answer ("deliberately not filtered"), the reason (no stated dependency), and the seam (`_format_cookies_for_ffmpeg`). (2) *Names evidence* — ephemeral context, no persistence, no cross-origin requirement observed; **not** a preference, per `B8-A2`. (3) *States invalidation* — the REVISIT-IF block names both triggers. (4) *No behaviour changed* — the file set is `extractor.py` + `test_extractor.py`; the edits are two comments/docstrings and one new test; **no statement, no expression, and no call in either file moves.** Verified now: `tests/test_extractor.py` is **47 passed** and `ruff check` / `ruff format --check` are clean on both files at `209bd77`, so the delta gates hold. (5) *Test pins behaviour and says why* — `B8-A6`'s docstring states outright that the test is supposed to fail under `Alt B` and must not be "fixed". (6) *No forbidden file touched* — `B8-A5`'s table; **none of the four is needed.**

**Edits made by this audit: one.** `#### B8-AUDIT` inserted into this file, in the `B8` region immediately before `### \`B9\``. No code, test, plan-11, or other audit-phase file was read-modified; nothing staged or committed; `tmp/`, `tmp_old_sec*.md`, the deleted `.ai/plans/00_*`…`07_*`, `.ai/problems/PROBLEM.md`, `.kilo/commands/implement/implement-plan-multiagent.md`, untracked plans 05–08, `.gitignore`, and every `src/`/`tests/` file are untouched.

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

#### B9-AUDIT

**Severity table, verbatim** (`## 8. Severity Taxonomy`; second column is `Condition in this phase`, singular):

| Severity | Condition in this phase |
|----------|-------------------------|
| CRITICAL | A cross-phase conflict, or a rollout-safety blocker: two phases assert incompatible facts about the same subject; or a fix that cannot be ordered safely because a prerequisite of it is itself a finding. |
| HIGH | A finding whose technical correctness or current applicability failed verification; or a rejected finding whose rejection changes a conclusion the report would otherwise carry. |
| MEDIUM | A reclassified finding (its `Type` changed) or a merged finding (its content moved under another ID). The subject survives; the framing changes. |
| LOW | A `DOC-UPDATE` candidate; any advisory finding with no security, data-loss or correctness consequence. |

**Decision-application row, verbatim** (`## 11. Reporting`): `| **Validated** | Keep as-is. **The severity is re-derived from this phase's own verification, and is not changed by this decision.** |`

**Constraining sentences.** (a) `**The findings template is the authority.**` … the `severity` row "fixes `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW` as the severity of a **defect**". (b) "**The four severity words are not redefined here**, and this file adds no fifth. Every sibling phase states the same sentence and then gives only the conditions that are specific to its own subject." (c) "**The per-finding decision is not a severity.**" (d) "**A decision never changes the severity column.** A rejected finding keeps the severity it carried, and a reclassified finding keeps it". (e) "**These conditions are a classification vocabulary, not a verdict.** Every severity is composed by this phase from its own run (binding rule 1) … the consequence must be **observed** … not observed is filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an observed severity." (f) binding rule 1: severities are "re-derived from this phase's own verification … **none is changed because of the decision recorded against it**" and nothing is "inherited".

**The trap the plan did not name.** `CRITICAL` and `LOW` are keyed on what a finding **is** (a conflict/blocker; a `DOC-UPDATE` or consequence-free advisory) and are therefore already reachable by a `validated` finding today. Only `HIGH` ("verification **failed**") and `MEDIUM` ("reclassified or merged") are keyed on decision/outcome, and they *exclude* `validated`. So the uncovered case is narrow and specific: a finding whose verification **passed**, whose decision is `validated`, and which is neither a conflict/blocker nor a doc-candidate/no-consequence advisory. Its band must be **composed**, and the table has no row that says so. `VAL-601`'s own draft (`HIGH or MEDIUM | a validated finding, composed from the consequence…`) introduces no fifth *word*, but it reads as a decision→band assignment, which (d) forbids in substance, and it silently excludes `LOW`.

**Sibling sweep — twelve files, one table, no copies.** All twelve carry a four-row `| Severity | … |` table and the same `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW` authority sentence. The eleven auditor phases `01`–`11` use header `| Severity | Conditions |` and their rows are **product conditions in that phase's own subject** — every condition describes a defect. The strings `Validated` / `Reclassified` / `Rejected` occur **only** in `99-audit-validate.md` (0 hits across all eleven siblings), and an auditor phase cannot produce "a finding that passes verification" because every finding it files is by construction a defect it verified. **Verdict: the gap is unique to `99`; these are not copies and need no fix.** AC-3 is discharged by this report; AC-4 holds — exactly one file.

**Corpus dependency (read-only, nothing changed).** The gap is load-bearing today: `.ai/audit/99-validation/06-credentials-secrets-validated-findings.md` quotes the four rows verbatim inside `VAL-601`, and its `### Severity movements recorded in place` table cites the table as `` `:369` `` for `SEC-001`/`SEC-002`, while `SEC-007`'s basis is comparative prose against `SEC-005` — because no row covers a passing verification. Nine artifacts carry `| Validated (unchanged) |` tallies totalling **98 findings that passed verification** (`06` alone: 7 of 10 — `SEC-005` and `SEC-009` sit at HIGH with no row source). `02-config-validated-findings.md` records `CFG-001` as `Action: validated` with "**Severity re-derived … CRITICAL → HIGH** … HIGH is the strongest severity the observed consequence supports" — the improvised rule, verbatim. Editing the phase doc invalidates none of these (they quote the table to argue for the fix); it gives every future run a source. Two out-of-scope observations: `08` and `10` do not carry the four-row action tally at all, and `06` duplicates the tally across `## Findings summary after validation` and `## Validation Summary`.

**Recommendation: Alt A, with the row's first cell as a derivation, not a band.** Alt B is rejected as the plan states — `## 11`'s table describes an *action* ("Keep as-is"), not a band, and cannot carry the composition source. Alt C is rejected as the plan states — an unsourced prose sentence is precisely what produced `CFG-001` and `SEC-007`. Alt A is the only option that puts a band and its source in the place a reader looks. **Deviation from the finding's draft, and why:** the finding proposes the Severity cell read `HIGH or MEDIUM`. Keep a disjunction there and the row reads as *the decision picks one of two bands* — the thing (d) prohibits — and it drops `LOW`, which a validated `DOC-UPDATE` finding already earns under the existing row. Write the cell as a non-band derivation instead; it names no new severity word, so AC-2 holds.

**Draft row to land** (single table row appended after `LOW`, inside the existing `## 8` table; **no prose changed — sentences (a)–(f) all remain accurate**):

```markdown
| *composed — not fixed by the decision* | A finding whose verification **passed** and whose decision is `validated`. No band is assigned here: the band is composed from the finding's own consequence on the declared platform, as binding rule 1 requires. `CRITICAL` and `LOW` where the condition that row already names holds; otherwise the strongest band this run's verification established for the consequence it observed — the same rule `## 11`'s `Validated` action re-derives under, and it is stated here because no row above covers a verification that passed. A consequence that was **not** observed takes the template's `verification` path instead: the structural fact under the owning phase's own severity table, never an observed severity. **This row defines no fifth severity word.** |
```

**Acceptance test — does Alt A alone make the question answerable from the table?** Yes, **provided the row carries the composition source in its own cell** rather than delegating. Check by three reads of the table alone, with `## 11` closed: (1) name the trigger — "verification passed and decision `validated`"; (2) name the band — *composed, not fixed*, `CRITICAL`/`LOW` by their existing conditions, otherwise the strongest band the observed consequence supports; (3) confirm no fifth word was minted — the `Severity` cell contains a derivation phrase, and `CRITICAL | HIGH | MEDIUM | LOW` still appears exactly four times in `## 8`. The row **does** cite `## 11`'s `Validated` action — as the place the band is *re-derived*, not as the place it is *set*, so the answer stands without opening it. If the row is instead shortened to the finding's `HIGH or MEDIUM | a validated finding, composed from the consequence…`, criterion (2) fails: `LOW` is unreachable and the answer requires reading `## 11` and the artifact's own improvised rule.

**Edits made by this audit: one file, one insertion, no code, no test, no new file.** `.ai/plans/17-credentials-secrets-audit-fixes-execution.md` — `#### B9-AUDIT` appended at the end of the `B9` region (after the `EB-B9` yaml, before the `---`). Nothing under `.ai/audit/**`, `.kilo/**`, `src/`, or `tests/` was touched; nothing staged or committed. **The fix itself still has an unedited file set: `.kilo/commands/audit/phases/99-audit-validate.md`, one table, one row.**

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

#### B10-AUDIT

**1. The template as it actually reads** (`.ai/audit/templates/audit-findings.md`, 86 lines, anchored by heading).

`## Summary`, verbatim — **four pre-filled numbers, all zero**: `| CRITICAL | 0 |` · `| HIGH | 0 |` · `| MEDIUM | 0 |` · `| LOW | 0 |`. The three action lists, verbatim: `## Mandatory Fixes` → `{List all findings classified as mandatory}` · `## Advisory Recommendations` → `{List all findings classified as advisory}` · `## Doc Updates Needed` → `{List all findings classified as DOC-UPDATE type}`. Each gives one instruction and no rule for **what** to count, so the placeholder is both pre-answered and under-specified.

**Cross-references: none exist today.** Nothing in the template points at any of the four sections — the only other occurrences of the words are `Classification | {mandatory\|advisory}` inside the per-finding field table and the two `Classification Guide` bullets, which are about the *field*, not the sections. AC-3 is therefore **vacuously satisfied now and becomes load-bearing only if a section is removed**. The nearest external near-miss is `.kilo/agents/validator.md` `### Required Fixes` / `### Advisory Recommendations`, which is the validator role file's own report skeleton, not a pointer into this template — **not in scope, not a required fix**.

**Must stay untouched, confirmed present.** `## Findings` block: `### {ID}: {Title}`, the `**Decision:** {validated | reclassified | merged | rejected} · {decision_detail}` line, the nine-row field table (`ID`, `Severity`, `Type`, `Affected Modules`, `Classification`, `Verification`, `Description`, `Evidence`, `Recommendation`). Field-reference table: 12 rows including `verification` (`observed` · `unverified`), `decision`, `decision_detail`, plus `## Classification Guide`. **Both `Decision` and `verification` exist and are out of scope — they must not change.**

**2. Evidence re-derived at `4207d78`. Plan 11's claim is falsified twice over, and the block's own Correction 5 is wrong on two facts.** Twelve files tracked under `.ai/audit/99-validation/`; census taken fence-aware, because `06` quotes the template **inside a ````markdown` block** and a naive heading grep reads that quote as live sections.

| Artifact | Keeps / deletes | What it actually puts there |
|---|---|---|
| `01-entry-architecture-validated-findings.md` | `## Advisory Recommendations` kept; `## Required Fixes` kept (**renamed** Mandatory); Summary and Doc Updates deleted | Real ID-keyed tables composed from this run's decisions |
| `02-config-validated-findings.md` | **all four kept** | Summary = re-derived `HIGH 2 / MEDIUM 4 / LOW 2` + prose naming `CFG-001` re-derived `CRITICAL → HIGH`; the three lists are real tables |
| `03-network-resilience-validated-findings.md` | all four deleted | States the deletion and its reason in prose |
| `04-…-CON-002-verification-record.md` | all four deleted | Not a findings report (a verification record) |
| `04-…-validated-findings.md` | all four deleted | — |
| `05-subprocess-browser-validated-findings.md` | all four deleted | Header states the omission |
| **`06-credentials-secrets-validated-findings.md`** | **all four deleted** | **The block's Correction 5 is false.** `## Summary` and the three lists at `:1543-1560` sit **inside a fenced `markdown` block quoting the template as evidence** inside `VAL-603`'s Description. There is **no live zero-table and no live instance of the defect in the corpus.** |
| `07-filesystem-artifacts-validated-findings.md` | `## Summary` kept, repurposed | A 14-row findings index (`ID · Severity · Type · Classification · One line`) — **not a tally at all** |
| `08-cli-observability-validated-findings.md` | **all four kept** | Summary = the **source report's** `HIGH 1 / MEDIUM 9 / LOW 7` "kept as filed", with a blockquote deferring re-derived severities to `### Severity tally` (`CRITICAL 1 / HIGH 0 / MEDIUM 6 / LOW 6`, 4 not bucketed). The lists are real tables |
| `09-code-quality-validated-findings.md` | all four deleted | — |
| `10-test-coverage-validated-findings.md` | Summary deleted; **all three action lists kept** as `###` under `## Validation Summary` | Real content; prose states the deliberate de-duplication |
| `11-supply-chain-validated-findings.md` | all four deleted | Prose states the deletion |

So: **4 of 12 keep ≥1 section in substance** (`01`, `02`, `08`, `10`), `07` keeps the heading for a different purpose, and **no artifact keeps a pre-filled zero**. The name `13-cli-observability-validated-findings.md` cited in Correction 5 **does not exist**; the artifact is `08-cli-observability`. And "real **re-derived** tallies" is true of `02`, not of `08`, which keeps the *source's* numbers and defers its own.

**The larger falsification the block missed: the template's primary consumer was never measured.** `.ai/audit/{NN}-{slug}/findings.md` — the eleven **auditor** reports the template exists for — **seven keep all four sections with genuine tallies**: `01` `0/3/10/1`, `02` `1/1/4/2`, `04` `1/3/5/0` **plus a fifth row `| none (UNVERIFIED, not executed) | 1 |`**, `08` `0/1/9/7`, `09` `0/2/7/4`, `10` `3/4/6/3`, `11` `0/3/10/3`. Only `03` and `05` omit them; `06` repurposes Summary as prose and `07` as an index. `04`'s extra row is the strongest single piece of evidence: the tally is genuinely computed, extends past the template's four rows, and needs an instruction saying what to count.

**3. The decisive question: does `99`'s decision-tally requirement already carry the template's `## Summary`? No — and `99` says so in terms.** `.kilo/commands/audit/phases/99-audit-validate.md` §4 R3: *"per-finding decision tally (Validated / Reclassified / Merged / Rejected). **A decision tally, not a severity tally.**"* The §11 *Validation Summary* block is an `Action | Count | Details` table whose rows are `Validated (unchanged)`, `Reclassified`, `Merged`, `Rejected`, `VAL-` — **no severity column anywhere**. `Alt B`'s stated premise (*"require the tally to live in the validation summary the validate phase already mandates"*) is therefore **factually false**: `99` mandates a *decision* tally, not a *severity* tally. **`Alt B` deletes a section that seven of eleven producers and two validators fill, and hands it to a requirement that explicitly disclaims carrying it.**

**Recommendation: `Alt A`.** Not by default, but on the measured evidence: (a) `Alt B`'s premise fails on `99`'s own words; (b) the sections are used correctly by `7/11` producers and `2/12` validators; (c) the "everyone deletes them" evidence is `7/12`, and even those deletes are partial and name-based (`01` keeps a renamed Mandatory list, `10` keeps all three action lists) — so the shape is wanted, the **pre-answering** is the defect.

**One conflict `B10` cannot close, recorded not hidden.** `99` §5 (i) carries the check row *"Pre-answered sections deleted — Does the artifact still carry a summary, appendix or placeholder section the format supplies pre-answered? … **A section every phase must delete is a defect of the format.**"* Under `Alt A` that row's premise is retired, but the row itself stays in `99` and instructs the next validator to strip the now-fillable Summary. **`B10` is forbidden from touching `99`, so this cannot be fixed here.** Land `Alt A` and file `99` §5 (i) as a **required companion change for its own block**; the alternative — leaving the row and expecting `Alt A` to survive the next run — is the defect recurring with a new name. `Alt C` (optional sections) is rejected for the plan's stated reason: the summary would still ship pre-answered.

**4. Is the spec store's zero-table in scope? No — and the premise does not hold.** `06` has no live zero-table; the four headings and all four zeros are a **fenced quotation of the template used as `VAL-603`'s evidence**. Editing it would delete the evidence for the very finding this block implements, and `06` is a historical judgment record. **Recommendation: record it as evidence, change nothing, and close `B10-D1` as not-required** — there is no instance to correct. Corollary worth stating plainly: **the defect is confined to the template**; no artifact in the repository is a live instance of it.

**5. Draft replacement wording** — the whole `## Summary`…`## Doc Updates Needed` tail, all four sections **fillable**, nothing removed:

```markdown
## Summary

{Tally the findings above by severity. Count each finding once, under the `Severity` it
carries after this report's own decisions; a finding that was merged or rejected is not
counted here. A severity with no findings is written as `0`. Add a row for a severity the
owning phase's table defines and this format does not.}

| Severity | Count |
|----------|-------|
| CRITICAL | {count} |
| HIGH | {count} |
| MEDIUM | {count} |
| LOW | {count} |

## Mandatory Fixes

{Every finding classified `mandatory`, by ID, with what must change and why.}

## Advisory Recommendations

{Every finding classified `advisory`, by ID, with what to change and why.}

## Doc Updates Needed

{Every finding of type `DOC-UPDATE`, by ID, with the document and the claim to correct.}
```

**6. Verification to run afterwards.** (1) `git grep -n "| 0 |" -- .ai/audit/templates/audit-findings.md` returns nothing — no pre-filled count anywhere. (2) Each of the four sections stated **fillable**, per section, in the commit message: Summary, Mandatory Fixes, Advisory Recommendations, Doc Updates Needed — **none removed**, so AC-3 has nothing to check and AC-5 is satisfied by leaving `## Findings` and the field-reference table byte-identical. (3) `git status --porcelain -- .ai/audit/` → **empty**, verified at audit time and again before commit; `.ai/audit/99-validation/**` is evidence, never an edit target. (4) `git status --porcelain` shows exactly one staged path: `.ai/audit/templates/audit-findings.md`. (5) `Decision` and `verification` rows unchanged (`git diff` shows no hunk touching them).

**Verdict: land `Alt A`.** Evidence supports it, `Alt B`'s premise is falsified by `99` §4 R3 and §11, and the block's Correction 5 must be corrected on three points before the Implementor starts: `13-cli-observability` does not exist (`08` does), `06` keeps **no** section (its four headings are a fenced quotation), and `08` keeps the **source's** tally rather than a re-derived one. The companion change to `99` §5 (i) is required for `Alt A` to hold across runs.

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