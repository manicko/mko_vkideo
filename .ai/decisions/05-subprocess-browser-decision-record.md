# Decision Record — Phase 05 Subprocess & Browser Audit Fixes (Plan 10)

**Scope:** The closure of the two cross-phase validation findings `phase05/VAL-501` and
`phase05/VAL-502`, the disposition of `TRN-010`, and the recording of the `B10`
commit-message gap.

**Decision dates:** 2026-10-03 — `D1`–`D5` (Product Owner), `D6`–`D7` (Tech Lead).

**Companion to:** `.ai/plans/10-subprocess-browser-audit-fixes.md` §9 (Decisions taken),
which records `D1`–`D7` verbatim with the owner's words and dates. This record does **not**
reproduce the owner's verbatim words; it states the **outcome** of the chains, the
**outstanding** correction owed to phase 06, and the `B10` commit-message gap. Cross-reference
§9 for the decisions themselves.

**Read-only boundary:** `.ai/audit/**` was **not modified** by this engagement. Phase 06's
`findings.md` and validated-findings file are stated here as outstanding, not corrected here.
This record is the durable repository-facing companion that §3 `B9` of the plan calls for.

---

## 1. Both chains of `phase05/VAL-502` are closed

`phase05/VAL-502` (filed against the audit inputs as a Check-point-4 / R4 rollout-safety
conflict between `TRN-001` and `TRN-002`) had two chains. Both are now settled, in opposite
directions.

### Chain 2 — the shape of the `TRN-001` fix — CLOSED by `D2`

`phase05/VAL-502` chain 2 posed the question: "the shape of the `TRN-001` fix is a decision
phase 06's `SEC-004` already owns." Decision `D2` (2026-10-03, Product Owner) **answers** it:
the ffmpeg download transport is **deleted**, not repaired. The owner's words, verbatim in §9
`D2`: *"No you can delete it for now. If it will be needed we will add it in future."*

There is no remaining shape question for phase 06 to adjudicate about the fix — the fix *is*
the deletion. `D2` discharged chain 2.

### Chain 1 — `TRN-001` and `TRN-002` must land together — EVAPORATED

`phase05/VAL-502` chain 1 asserted an ordering constraint: fixing `TRN-001` would activate the
latent argfile-destroy ordering defect in `TRN-002`, so the two had to land together. This
chain **evaporated** with the argfile, rather than being satisfied by ordering.

The coupling existed because repairing one member made the other worse: repairing `TRN-001`'s
concealment (the `@argfile` invocation) would have activated the ordering hazard in
`TRN-002`'s `finally:` (a failed destroy sitting outside the child-termination guarantee).
There is **nothing left to couple**:

- `TRN-001` is **disposed** — its subject (`@argfile` invocation, `--method ffmpeg`
  transport) is deleted outright by `D2`. `D2` **is** the answer to `TRN-001`; it is not left
  open and not carried forward.
- `TRN-002` is **re-scoped** to a different statement in a different module:
  `_download_with_ytdlp`'s cookie-file `finally:`, not `_temp_argfile`'s. The orphan half
  (a failed destroy leaving a child un-reaped) is moot — its only instance was
  `_temp_argfile`'s `finally:`, deleted with the transport. The surviving half (a failed
  destroy replacing the outcome) is a narrower, lower-severity residue: it cannot orphan a
  process, it can only mask a return value.

The former edge `E1` in §4.1 is marked **retired**. The ordering obligation is discharged by
the deletion itself, not by commit ordering.

### `TRN-010` is moot

`TRN-010`'s asymmetry was between **two transports** — the ffmpeg transport passed `--cookies
<path>` via argfile, the yt-dlp transport passed it in argv. With one transport remaining
(yt-dlp), there is no asymmetry. Its residue — yt-dlp still passes `--cookies <path>` and the
media URL in argv, and `sanitize_text_for_log` still cannot match a path — is **phase 06's
`SEC-006`**, and `D1` makes the exposure moot for this deployment. No block carries it.

---

## 2. `phase05/VAL-501` is now doubly wrong — correction outstanding, owned by phase 06

`phase05/VAL-501` filed against phase 06's `SEC-004`, asserting in its R5(d) table that the
ffmpeg transport's concealment was **`MET (argfile)`**, and in its subject line claiming the
ffmpeg transport *"satisfies the product's own stated intent."* Both statements are wrong
**twice over** now:

1. **The concealment was never achieved.** The installed muxer supports neither `@file` nor
   `-/opt`. `ffmpeg "@<argfile>"` treated the token as a literal output filename, produced
   nothing, and exited non-zero. `TRN-001` was a silent no-op behind the concealment claim.
   (Verified at §2.7: `ffmpeg -h` search for `@file` or `-/opt` → no match for either; the
   control experiment in §2.7 showed `output_created = False` with the argfile and
   `output_created = True` with direct arguments.)

2. **The transport no longer exists.** Decision `D2` deleted `--method ffmpeg` and every symbol
   that served it. `SEC-004` now describes a transport that is gone — its ffmpeg column is
   not merely vacuous, it describes nothing.

`.ai/audit/**` is **read-only** for this engagement, so this record states the correction and
does **not** perform it. Phase 06 needs a separate pass to:

- **Replace both `MET (argfile)` cells** in `SEC-004`'s R5(d) table. Neither concealment mode
  was achieved: the argfile path was never functional (the muxer does not support `@file`), and
  the direct-argument path was deleted. No `MET` cell should remain for the ffmpeg column
  without an explicit re-derivation against a re-instated mechanism.
- **Rewrite the subject line** so it does not name a deleted transport (`--method ffmpeg`).
- **Record `D1`** as the reason the exposure argument no longer distinguishes the transports:
  on a single-user desktop the user can already read their own process list.

This record states **what is wrong and who owns the correction**. It does **not** state what
`SEC-004` should become — that is phase 06's re-derivation. `B9` and this record do not re-file
`SEC-004`, do not change its severity, and mark nothing "fixed" that is not.

---

## 3. `D2` deletes the transport — authorised as a breaking change

`D2` does **not** repair the `TRN-001` argfile mechanism. Repairing it would have required an
unmeasured mechanism (a muxer that supports response files), which the codebase cannot
guarantee. The Product Owner's decision was removal.

A script passing `--method ffmpeg` now receives Typer's invalid-choice error and exit `2`
(the documented usage-error code). No deprecation shim, no feature flag, no tombstone enum
member, and no alias was left behind — `DownloadMethod.FFMPEG` is removed outright, because a
dead `StrEnum` member violates project rule 10.

**Preserved** (binding, verified by grep after the deletion — the commit body should have
stated this but did not): `--method`/`-m`, `DownloadMethod.YTDLP`, `DownloadMethod.AUTO`, the
`case _:` arm with its `unknown_download_method` record, `check_ffmpeg_available` and its
single bare call in `perform_download` (still live — segment merging still needs the muxer),
the merge transport (`iter_process_lines`, `cancel_subprocess`/`cancel_ffmpeg_process`,
`_await_ffmpeg_with_timeout`, `_check_merge_space`, `_merge_segments_batched`,
`_merge_batch_segments`, `_perform_final_merge`, `_build_ffmpeg_concat_command`,
`_required_merge_bytes`), `sanitize_text_for_log`/`_strip_auth_params`/`sanitize_url_for_log`,
**every** dependency in `pyproject.toml`, and `artifacts = ["src/vkdownloader/stealth.min.js"]`.

**`--method auto` semantics after the deletion:** `DownloadMethod.AUTO` and
`DownloadMethod.YTDLP` now resolve to the same transport (`download_with_ytdlp_with_resume_fallback`).
The only difference: `AUTO` skips `_resolve_cookies` when `settings.cookie_source == NONE`, while
`YTDLP` always resolves. Precise statement: **`--method auto` means: resolve cookies according
to `cookie_source` — skipping browser resolution when it is `none` — then download via yt-dlp
with segment-level resume as the fallback.**

---

## 4. `D1` retires the exposure argument

On a single-user desktop deployment, the user can already read their own process list.
Command-line token exposure is therefore **moot** for this deployment. This retires the entire
`SEC-004` exposure argument as a reason to prefer indirection. See §9 `D1` and §1.4.

This is why the residue of `TRN-010` (argv exposure in the yt-dlp transport) and the
`SEC-004` concealment comparison are both moot for this deployment, even though the
concealment was never achieved in the first place.

---

## 5. The console-encoding ownership gap — still unowned by any finding, adopted by `D7`

No finding in any phase owns the console-encoding defect. Phase 01's `ENT-001`/`ENT-002` are
sink-*routing* findings and deferred encoding to phase 08; phase 08 never filed it; a corpus
search for `cp1251` finds it only as evidence inside `ENT-001`, `ENT-002` and `OUT-002`. This
absence of an owner is precisely why it survived two audits.

`D7` (Tech Lead, 2026-10-03) adopted it here in block `B16` as option (A). The adoption and its
option choice are recorded in §9 `D7`. `Q6` is closed by `D7`.

---

## 6. The `B10` commit-message gap

Commit `d572d96`'s subject was:

```
TRN-001: Remove FFMPEG download transport (DownloadMethod.FFMPEG)
```

This **does not follow** the repository's `type(scope): description` convention. The commits
before and after it follow the convention:

```
refactor(downloader): keep private helpers out of the public facade      ← 1b8c339 (HEAD)
fix(logging): give the console sink an encoding-safe error handler        ← 183d40f
feat(config): gate the stealth posture behind stealth_enabled, default off ← c6d0214
```

Commit `12d97d4` (`Establish the minimum platform-appropriate boundary keyword
at every asyncio subprocess spawn site, with the Windows residual documented honestly.`)
also lacks a `type(scope):` prefix and is recorded nowhere else.

The `B10` subject instead uses a finding-id prefix (`TRN-001:`) and names the deleted enum
member as a suffix. History is **not rewritten**; the substance is recorded here so the
repository's record is complete.

The commit body lists changes made but **omits** three things the plan required in the commit
body:

1. **The preservation list.** The body enumerates deletions and edits but does **not** state
   what was deliberately kept (`DownloadMethod.AUTO`, `check_ffmpeg_available` and its bare
   call, the full merge transport, all `pyproject.toml` dependencies, and the
   `stealth.min.js` artefact declaration). A reader cannot tell from the commit body alone what
   survived by design.
2. **The `--method auto` semantics statement.** The body does **not** state that `AUTO` and
   `YTDLP` now resolve to the same transport, and that the only difference is auto skips
   `_resolve_cookies` when `cookie_source == CookieSource.NONE`. Without this, the
   behavioural change to `--method auto` scripts is invisible in history.
3. **The `SEC-004` re-adjudication statement.** The body does **not** name that phase 06's
   `SEC-004` must be re-derived because it now describes a transport that no longer exists.
   The subject line ("Remove FFMPEG download transport") is accurate for the code change but
   does not carry the cross-phase consequence.

These omissions are recorded here, not in a commit rewrite, because the plan prohibits history
modification. The durable record stands in the gap.

---

## 7. Every correction this plan entered against the code context (§1.7) and the mojibake observation (§1.8)

To spare the next reader inheriting them, the full list is in §1.7 and §1.8 of the plan. The
six corrections, re-derived against the live tree at `HEAD = 1b8c339`:

1. **`TRN-008` arm (c) is misidentified** in both the code context and the artifact. There is
   no `ModuleNotFoundError` arm in `_download_with_ytdlp`; the live arm is
   `except FileNotFoundError:` logging **`ytdlp_not_found`**, and a missing *module* surfaces
   as the child's non-zero exit through the ordinary `returncode != 0` arm.
2. **The api-reference documentation site** that asserts the argv is only
   `['ffmpeg', '@<argfile>']` is at `docs/01-tools/api-reference.md`, **not**
   `docs/99-reference/api-reference.md`. (`B10` edits the live path.)
3. **The documentation site count is seven, not six.** `docs/99-reference/cli-reference-clean.md`
   is a second copy of the CLI reference and also carries the `--method` option table and the
   worked `--method ffmpeg` example.
4. **Three test class names in the code context's inventory do not exist:** `TestDownloadWithFFmpeg`
   → `TestHLSDownloaderDownload`; `TestFormatArgfile` → `TestTempArgfile`; `TestCheckFFmpegAvailable`
   → `TestFfmpegAvailabilityCheck`.
5. **Two tests the code context lists as pins do not exist at all:** `test_download_with_ffmpeg_failure`
   and `test_download_with_ffmpeg_file_not_found`. The returncode-≠-0 fallback arm is pinned by
   `TestHLSDownloaderDownload::test_error_handling_ffmpeg_failure`; the `FileNotFoundError` arm has
   **no test**. `TRN-008`'s arm (a) is unpinned, not pinned.
6. **`TRN-005`'s hazard-amplifier for `B2` is retired by `D2`.** `B3` was deleted; `iter_process_lines`
   keeps exactly its two yt-dlp consumers and the exposure is unchanged from what `B2` was scoped
   against.

The mojibake observation: `docs/99-reference/cli-reference-clean.md` is the same document as
`cli-reference.md` with **every non-ASCII character mis-decoded** — the em dash appears as `вЂ”`, the
cp1251 misreading of UTF-8 `E2 80 94`. It is 283 lines against the original's 284 and the hashes
differ. Exactly one file links to it
(`docs/99-reference/error-handling-logging-research-2025-2026.md`). There is no `mkdocs.yml` in this
repository, so there is no navigation to reconcile. This is a pre-existing documentation-hygiene
defect owned by no phase; it is **recorded, not fixed** here. `B10` corrects its `--method` rows because
leaving a page advertising a deleted CLI option is worse than leaving its encoding broken.

---

## 8. Identifier scoping

Every `VAL-` id in this record is qualified as `phase05/VAL-NNN`. The bare `VAL-` prefix is a
colliding prefix across every validation run — `VAL-501` appears in phase 07's validation store
as a pipeline-document range, not as phase 05's cross-phase conflict — and an unqualified id is
a defect. `TRN-` and `BRW-` are unique to phase 05 across the whole store and are **not**
qualified. This convention is binding on every block, every block report, every task id and
every commit message of this plan.

---

## Verification

`B9` is a prose-only block. No production code, no tests, and no `pyproject.toml` were
modified by this block. The verification commands confirm the tree is unchanged from the
`B10`-through-`B16` baseline:

| Command | Result |
|---|---|
| `uv run pytest tests -q` | **799 passed, 6 skipped, 2 warnings** |
| `uv run ruff check src` | `All checks passed!` |
| `uv run ruff format --check src` | `31 files already formatted` |
| `uv run mypy src` | `Success: no issues found in 31 source files` |
| `git diff --exit-code -- .ai/audit` | empty |
| `git status --short -- .ai/audit` | empty |
| `git diff --exit-code -- src tests pyproject.toml` | empty |

`git diff --cached --stat` shows only this block's new file.

---

## 9. Gate deviation: `mypy src tests` is 93, not 79

**Dated:** 2026-10-04 (post-baseline at `a8294b7`).

### Gate as written

`.ai/plans/10-subprocess-browser-audit-fixes.md` records the gate twice:

- **§1.6:** `uv run mypy src` is clean (31 files). `uv run mypy src tests` reports **79 errors in 8 files**. A block that touches `tests/` writes "the same 79 errors in the same 8 files, with no error in any file the block edited."
- **§8.1 (per-block table, row 5):** `mypy src tests` — **NOT a clean gate.** The suite is 79 errors in 8 files before this plan and must be the same 79 errors in the same 8 files after, with no error in any file the block edited.
- **§8.2 (end-of-plan gate, row 3):** `mypy src tests` — **79 errors in 8 files or fewer. Never more.**
- **§2.1 baseline:** `Found 79 errors in 8 files (checked 54 source files) EXIT=1`.

### Live count

`uv run mypy src tests` reports **93 errors in 8 files**. `mypy src` remains clean (0 issues). No error appears in any `src/` file.

### Cause and commit

Commit `1b8c339` (`refactor(downloader): keep private helpers out of the public facade`) removed `_attempt_segment_resume` and `_download_with_ytdlp` from `downloader.py`'s `__all__` and redirected three test imports to the defining module (`ytdlp_downloader.py`). This restored **23** pre-existing `attr-defined` errors that the `B13` work had previously suppressed by re-exporting those private names through the facade's `__all__`.

### Assessment: the architectural trade is correct and endorsed

`__all__` is the public API surface. `_attempt_segment_resume` and `_download_with_ytdlp` are underscore-prefixed private helpers. Re-widening `__all__` to silence the type checker inverts project rule 2 ("Production code is king"). The Validator explicitly endorsed the `1b8c339` correction. The `+23` are restored baseline, not new debt: they are the same `attr-defined` errors at the same pre-existing, unedited facade import sites (`tests/test_hls_downloader.py` lines 1354, 1791, 3119–4360, 4464).

### Operative rule going forward

| Command | Status |
|---|---|
| `uv run mypy src` | **Remains a gate.** Must stay 0 issues. |
| Any file a block edits | **No mypy error may appear** in any file the block edited. |
| `uv run mypy src tests` | **Not a gate.** |

The plan statements in §1.6, §8.1 (row 5), §8.2 (row 3) and §2.1 that read "79 errors" are **stale prose** — they describe the pre-`1b8c339` count. They are **not amended here** (they are the historical record of what was planned). The operative gate is `mypy src = 0` plus the per-file invariant above, both of which hold at `a8294b7/HEAD`.

### Explicit warning

**Do not re-widen `__all__`.** Re-adding `_attempt_segment_resume` and `_download_with_ytdlp` to `downloader.py`'s `__all__` to suppress the 23 `attr-defined` errors would re-invert exactly what `1b8c339` undid, widening the production API surface to satisfy a test import pattern, and violates project rule 2.
