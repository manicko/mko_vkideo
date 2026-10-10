# Phase 07 — Filesystem Artefacts Fix Plan

**Status**: PARTIALLY IMPLEMENTED — `P12-B1` (`12af960`), `P12-B2` (`5d264d4`), `P12-B3` (`12af960`), `P12-B4` (`aabfc46`), `P12-B5` (`cfe4ce8`), `P12-B6` (`40404e2`), `P12-B7` (`e2c5ad0`), `P12-B8` (`0c704de`), `P12-B9` (`767bb47`), `P12-B10` (`1d09009`) done. `P12-B11` verified (no code change needed — in-code comment and docs already state the posture, preferred shape "no code at all"). `P12-B12` done (`STRUCT.md` sentence updated). Remaining: none.
**Audit input**: `.ai/audit/99-validation/07-filesystem-artifacts-validated-findings.md` (validated findings artifact, phase 07, audit `HEAD = 4bf9efb`)
**Baseline re-verified by this Planner against live `HEAD = 58bb7ce`** (re-baselined after the loader retirement landed; the tree under `src` and `tests` is clean at that commit)
**Binding decisions applied**:
- **The ffmpeg loader is retired from the product.** yt-dlp is the loader; ffmpeg is **not** a loader transport. **Segment download stays and ffmpeg stays as the segment merge engine** (§2.4). This supersedes the plan-10 precedent this document originally recorded as invalid — see §1.1.3 for the withdrawal.
- **Decision A — duplicate batch entries.** Deduplicate by **resolved output filename** before dispatch; the **last occurrence wins**; earlier occurrences are skipped, reported, and must not load the network (§3.8).
- **Decision B — output path containment.** **Warn only. Do not refuse.** The tool does not restrict `--output` to a root (§3.3).

**Block ID namespace**: this plan's blocks are **plan-local** and are referenced across plans as `P12-B<n>`. Two sibling plans (`.ai/plans/10-…` and `.ai/plans/11-…`) also mint `B<n>` labels; a bare `B7` is ambiguous corpus-wide. Every cross-plan reference in this document is written `P12-B<n>` or `P11-B<n>` / `P10-B10`.
**Companion documents**: `.ai/plans/06-config-audit-fixes.md` (house skeleton this plan follows), `.ai/plans/10-subprocess-browser-audit-fixes.md` (the loader retirement — its `B10` **does** name `services/ffmpeg_utils.py` with the five symbols to delete; this plan's earlier claim that it did not is withdrawn, §1.1.3).

---

## 1. Scope

### 1.1 How the scope was derived

Four inputs, in this order. Nothing in this plan comes from the artifact's own `file:line` anchors, all of which are stale (§1.1.4).

1. **The validated findings artifact** (`ART-001` … `ART-014`, `VAL-701`).
2. **The binding product owner decision** that ffmpeg support is fully retired (§2.4).
3. **A fresh re-derivation against the live tree** — every anchor re-located semantically (§2.6).
4. **The other eleven phases' registers** — findings already owned elsewhere are excluded, not re-filed (§1.3).

### 1.1.1 Catalogue → verdict → destination

| Finding | Verdict after re-derivation | Destination | Block |
|---|---|---|---|
| `ART-001` control characters survive `sanitize_title` | **CONFIRMED, live.** Measured: `sanitize_title("before\x00after")` → `'before\x00after'`; `\x01 \x02 \x1f \n \r \t \x7f` all survive unchanged. The function replaces only the nine `:<>\|?*` characters and strips surrounding whitespace. | **IN** (name half) | `P12-B3` |
| `ART-001` diagnostics half — `failed_to_refresh_token` / `invalid_quality_for_browser_streams` mislabels in `_attempt_segment_resume` | **CONFIRMED as a mislabel, but OUT of scope.** Phase 08's `OUT-016` register owns it and states the split explicitly: it owns the diagnostics half and files only the name half. | **OUT** → `OUT-016` (phase 08) | — |
| `ART-002` probe and `DF-008` cleanup target the final name; the child writes `<name>.part` | **CONFIRMED, live.** `_build_ytdlp_cli_command` passes no `--no-part` (0 occurrences in `src/`), so yt-dlp's `FileDownloader.temp_name` writes `<name>.part`. The probe checks the final name's existence and size; `DF-008`'s cleanup unlinks the final name. **Re-verified at `58bb7ce`: `download_hls_with_resume` has exactly one caller**, `_attempt_segment_resume`, so the gate is existence-plus-non-zero-size on a name the child never writes. **HIGH, and the consequence is sharper than the artifact's.** | **IN** | `P12-B9` |
| `ART-003` `_cleanup_segments` bare `f.unlink()` over `glob("*")` | **CONFIRMED, live.** No `missing_ok`, no `is_file()`. On Windows a subdirectory raises `PermissionError [WinError 5]`, so the fix must not be POSIX-shaped. Sole call site is inside `if result:` in `_tally_and_merge`. `segment_downloader.py` is byte-identical at `58bb7ce` — no re-derivation needed. | **IN** | `P12-B6` |
| `ART-004` merge temps counted as segments | **CONFIRMED, but the mechanism changed and the artifact's evidence is stale.** The artifact's chain rests on a `finally` in `_merge_batch_segments` that **no longer exists**. Live: `_merge_segments_batched` returns `None` on a batch-stage failure and on a final-stage failure, and neither path removes the accumulated `batch_NNNNN.ts` temps or `final_list.txt`. The residue window is therefore reachable **with no process kill at all** — a graceful `return None` is sufficient. The count defect is unchanged (`batch_00000.ts` matches `glob("*.ts")` exactly as `00120.ts` does), and `_clear_stale_segments` still short-circuits on a matching `.signature`. The compensating control (`_log_preserve_segments` reporting `working_dir_ts_count` with a `count_note` naming `batch_*.ts`) is present and pinned. | **IN** | `P12-B6` |
| `ART-005` working-directory lifetime | **PARTIALLY FIXED AND PINNED — one half must not be restored.** The `if segment_count > 0` guard is gone; `_log_preserve_segments` reports unconditionally and `TestPreserveSegmentsReporter` pins that (a single `logger.info` on a **zero-count** directory, and `working_dir_ts_count == 3` with `batch_00000.ts` present). Reintroducing a count gate breaks three assertions. Remaining live surface: the `mkdir` preceding the first network fetch, the self-perpetuating `.signature` write, and the single success-path removal. | **IN** (remaining surface only) | `P12-B7` |
| `ART-006` two list entries with the same `(title, id)` collapse onto one name | **CONFIRMED, live.** `_resolve_output_file` composes `{safe_title}_{video.id}.mp4` (or `{index}_{video.id}.mp4` when there is no title) from data that arrives over the network. Measured at `58bb7ce`: `max_concurrent_downloads` defaults to `4`, **no name-level mutex anywhere**, **zero** occurrences of `force-overwrites` or `no-clobber`. **REMEDY CHANGED BY DECISION A: deduplicate by resolved output filename before dispatch, last occurrence wins, earlier ones skipped and never dispatched.** Not collision handling during download — collision elimination before it. | **IN** (re-scoped) | `P12-B10` |
| `ART-007` `0o600` requested, `0o666` measured | **CONFIRMED, live, and SHRINKS under the retirement but does not close.** Measured at `58bb7ce`: **two** `os.chmod` call sites (`ytdlp_downloader._create_temp_cookie_file`, and — with the argfile gone — the only other surviving one is in `config.setup_logging`'s `Path.chmod`) plus one `Path.touch(mode=0o600)` in `setup_logging`; the argfile's `os.chmod` died with the loader. Measured `mkdir` sites with **no mode argument**: **three** — `config.setup_logging` (log parent), `segment_downloader.download_hls_with_resume` (working tree), `security._resolve_output_file` (output dir). Every artefact requests `0o600` and measures `0o666`; every `mkdir` measures `0o777`. Zero compensating controls, zero runnable oracles. Recommendation part (2) is **OUT** → `TST-013` (phase 10). | **IN** (shrunken) | `P12-B11` |
| `ART-008` ffmpeg argfile residue in system `TEMP` | **STAYS RETIRED — for a different reason than this plan first gave.** Its subject was the ffmpeg **argfile**, the loader's artefact. The loader was the part removed; the merger stayed. Measured: **zero** occurrences of `gettempdir`, `iterdir`, `rmtree` or `TEMP` in `src/`. The residue class is empty because the artefact belonged to the loader. Do not resurrect it. | **OUT** | — |
| `ART-009` `validate_output_path` has no containment root | **CONFIRMED, live — but the remedy shrinks under Decision B.** Re-measured: `C:\Windows\System32` and `/etc` → `C:\etc` are both **accepted** (correct under the ruling), and `repo_root` still derives to **`C:\py_exp\mko_vkideo\src`** — one level too deep. The sole comparison is warn-only, and **two of the three call sites suppress it**: `security._resolve_output_file` and `ytdlp_downloader`'s probe pass `warning=False`; only `segment_downloader.download_hls_with_resume`'s call fires. `security.py` is unchanged since `e59523c`, so every anchor here still holds verbatim. | **IN** (re-scoped) | `P12-B2` |
| `ART-010` `".." in str(path)` substring test refuses `a..b` | **CONFIRMED, live.** The guard is a substring test at **two layers** — pre-resolution and post-resolution. All five tests in `TestValidateOutputPathTraversal` use real `..` components, so a `".." in path.parts` fix keeps them green. `security.py` unchanged. | **IN** | `P12-B1` |
| `ART-011` `[:100]` bounds a title component, not the path | **CONFIRMED, live.** `sanitize_title`'s own docstring claims "limits length to 100 characters" — true of the component, false of the path. `TestSanitizeTitle::test_limits_length_to_100_characters` pins the bound. Re-measured: a 777-character path is **accepted**, so the UNVERIFIED failure (`WinError 206`) was not reproduced on this host. | **DONE** (`D-2`, option a, `aabfc46`) | `P12-B4` |
| `ART-012` no download-stage probe; merge multiplier now insufficient | **CONFIRMED, live — and its importance RISES under Decision C.** Half 1: the tree's only free-space probe is `shutil.disk_usage` inside the merge, called once before batch 1. Half 2: `_required_merge_bytes` still returns `segment_bytes * 2 + _MERGE_SPACE_MARGIN_BYTES` and its docstring still justifies `2×`, while the landed additive merge holds segments **plus** batch temps **plus** a growing output = up to `3×`. **The merge engine is now the product's only merge and is permanent surface** (§2.4.4), so an insufficient free-space estimate on it is a standing defect on the only merge path, not one concern among several. The artifact's 3.15× / 1.40× figures were measured on a synthetic 250-segment set it itself marks non-transferable and were never re-driven — do not cite them. | **IN** (priority raised) | `P12-B8` |
| `ART-013` `NNNNN.ts.tmp` residue is unmatched by any sweep | **CONFIRMED, live.** Two sites derive `output_path.with_suffix(output_path.suffix + ".tmp")` and publish with `os.replace`. Measured: `glob("*")`, `glob("*.ts")` (four occurrences) and `f"{i:05d}.ts"` all miss `NNNNN.ts.tmp`. No test anywhere uses `os.replace`. The reporter half is already fixed. | **IN** | `P12-B6` (sweep half) + `P12-B7` (lifetime half) |
| `ART-014` no reserved device name, no trailing dot | **CONFIRMED, live, creation half is Windows-only.** Re-measured on this host: `CON`, `CON.txt`, `NUL` write without exception and leave no file; `AUX.txt` raises `FileNotFoundError [Errno 2]`; `sanitize_title("title...")` is a no-op. On POSIX these names are ordinary files. Derived names always append `_{id}.mp4`, which is the scope bound. **This bound is load-bearing for Decision A's dedup key** (§3.8). | **IN** | `P12-B5` |
| `VAL-701` ordering constraint on `ART-002` | **SHARPENED by the retirement.** `download_hls_with_resume` now has **exactly one** caller, `_attempt_segment_resume`, gated only on the final name existing with non-zero size — re-verified at `58bb7ce`. Fixing `ART-002` therefore moves `ART-001`, `ART-003`, `ART-004`, `ART-005`, `ART-012` and `ART-013` from "opt-in **or** a failed re-run over an existing file" to "a failed re-run over an existing file, **only**" — and to **default** if `ART-002` is fixed in the same batch. Decision A narrows how many items reach that path but does not change its reachability (§3.8). | **IN** (as the ordering keystone) | `P12-B9` |

### 1.1.2 The four adjacent paths — where they landed

The artifact's retention matrix asked whether a fix extends to the cookie file, the log file, the working directory and the final artefact. Re-derived against the tree at `58bb7ce`:

| Adjacent path | Live creation site | Loader-retirement effect | Finding |
|---|---|---|---|
| Log file + its parent dir | `config.setup_logging` | **unchanged** — the CLI preamble always runs | `ART-007` |
| Working tree (`.<stem>_segments/`) | `segment_downloader.download_hls_with_resume` | **unchanged** — the merge engine stayed | `ART-005`, `ART-013` |
| Output dir | `security._resolve_output_file` | **unchanged** | `ART-007`, `ART-009` |
| Final artefact | yt-dlp child / merge output | probe retargeted | `ART-002` |
| ffmpeg argfile | **gone** | deleted with the loader | `ART-008` — retired; it was the *loader's* artefact |
| Cookie file | `ytdlp_downloader._create_temp_cookie_file` | **unchanged** — the yt-dlp loader keeps cookies | `ART-007` (row remains) |

### 1.1.3 Corrections the artifact never made, corrections to the artifact, and corrections to this plan

**The `_INVALID_FILENAME_CHARS` correction.** `ART-001` names `_INVALID_FILENAME_CHARS` as a module constant of `utils/security.py`. **That symbol has never existed.** `sanitize_title` is an inline `for char in title:` loop over the nine characters `:<>\|?*`, with no module-level constant, and the file's last commit is `e59523c` — older than the audit base. Any implementation that "extends the constant" is implementing against a symbol that is not there. The scope for `P12-B3` is stated against the **function**, not a constant.

**The artifact's own corpus map is false.** It records that four handbooks carry no `findings.md`. Measured: all eleven phases have run and been validated. Nothing in this plan relies on that claim.

**The `R9` self-assessment is unsafe.** The artifact rates itself "106 anchors, 106 exact". Every `segment_downloader.py` anchor drifted between the audit base and `HEAD`, `ytdlp_downloader.py` moved, `config.py` moved, and three `ffmpeg_utils.py` anchors no longer exist at all. **This plan re-derived every anchor semantically and quotes no line numbers.**

**Ledger corrections that are themselves now stale.** Row 1 (the `auto` default) is wrong twice over: `DownloadMethod.AUTO` is the default at **both** `--method` option declarations in `cli.py`. Row 6 is **false** — both `ffmpeg_utils.py` sites it calls exact are gone. All four oracle citations are wrong. Rows 2–5 remain correct. The `DownloadError` / `OSError` comment **is** accurate (`issubclass(DownloadError, OSError)` is `False`) and stays.

**Two corrections this Planner adds by measurement, carried forward and re-verified at `58bb7ce`:**
- `tests/test_packaging.py`'s `EXPECTED_SDIST_ENTRIES` is **73** and `EXPECTED_WHEEL_ENTRIES` is **32** (counted from the parsed AST), with `BUILDER_ADDED_SDIST_ENTRIES` (2) and `EXPECTED_DIST_INFO_ENTRIES` (4). **Unchanged at `58bb7ce`.** The binding mechanism is unchanged: any new file under `src/`, `tests/` or `docs/` requires editing the relevant frozensets in the same commit.
- `tests/test_hls_downloader.py::TestCleanupSegments` **does** exercise `_cleanup_segments` — it imports the symbol and drives it with real files. The artifact's "no test names `_cleanup_segments`" is wrong. The real `ART-003` gap is narrower and stated exactly: **no test exercises a non-regular entry**. `P12-B6` extends that class rather than creating one.

**WITHDRAWN — this plan's claim about plan 10's `B10`.** An earlier revision of this plan asserted that `.ai/plans/10-subprocess-browser-audit-fixes.md`'s `B10` "does not name `services/ffmpeg_utils.py` for deletion". **That claim is false and is withdrawn.** Plan 10's `B10` does name the module with the exact five symbols to delete. The substantive conclusion is unchanged and is now stronger: those five are the **group B** symbols, and the module itself survives (§2.4.4).

**Corrected — the reason `ART-008` is empty.** This plan originally recorded that its residue class is empty *because the transport was retired*. The correct reason is narrower and better: the argfile was the **loader's** artefact, and the loader was the part removed while the merger stayed. The conclusion is the same; the reasoning is now the one a future reader can rely on.

### 1.2 IN scope

1. `utils/security.py::sanitize_title` — control characters, the length bound's meaning, reserved device names and trailing dots (`ART-001`, `ART-011`, `ART-014`).
2. `utils/security.py::validate_output_path` — component-wise traversal detection (`ART-010`), and, per **Decision B**, the `repo_root` derivation and the suppression of the warning at two of three call sites (`ART-009`). **The absence of a containment root is decided behaviour, not a defect.**
3. The segment downloader's filesystem sweeps and working-directory lifetime (`ART-003`, `ART-004`, `ART-005`, `ART-013`).
4. The merge engine's free-space sizing and the missing download-stage probe (`ART-012`) — **priority raised**, because the merge is now the product's only merge and is permanent.
5. The yt-dlp partial-file probe and the `DF-008` cleanup target (`ART-002`), with `VAL-701` as its ordering constraint.
6. Batch deduplication by resolved output filename, before dispatch (`ART-006`, per **Decision A**).
7. The artefact-confinement posture for the rows that remain (`ART-007`, shrunken).
8. One structural-map sentence in `docs/STRUCT.md` (§2.4.4).

### 1.3 OUT of scope, and why

| Excluded | Owner | Reason |
|---|---|---|
| `failed_to_refresh_token` and `invalid_quality_for_browser_streams` mislabels in `_attempt_segment_resume` | `OUT-016` (phase 08) | Phase 08's register states the split explicitly and files only the name half. Duplicating it would give one defect two remediation sites. |
| Moving the three `D-11` mode oracles off the platform guard | `TST-013` (phase 10) | Phase 10's store says it is "not covered by anything in `ART-007`" — i.e. phase 07 does not own it. It **is** this plan's declared residual (§1.4 `DEF-1`). |
| **Any containment root, refusal flag, or check that blocks a write** | — | **Decision B.** Warn only. The tool does not restrict `--output` to a root, and the fact that `C:\Windows\System32` is accepted is **correct behaviour**, not a gap to close. |
| The loader's deletion and its eight-file `--method ffmpeg` documentation surface | `P10-B10` | Already landed at `58bb7ce`. Recorded as a constraint here (§2.4), not re-planned. |
| Any sweep, hardening or documentation of the ffmpeg **loader** | — | The binding decision. Never planned, here or anywhere in this plan. The **merge engine** is explicitly not in this exclusion — see §2.4.4. |
| **The segment merge engine itself** — `_merge_batch_segments`, `_perform_final_merge`, `_merge_segments_batched`, `_build_ffmpeg_concat_command`, `_required_merge_bytes`, `_check_merge_space`, `_await_ffmpeg_with_timeout`, `_MERGE_SPACE_MARGIN_BYTES` | — | **Decision C: permanent product surface.** No block may plan any of them for deletion, and `services/ffmpeg_utils.py` can never be deleted whole. |
| **A name-level mutex for within-batch collisions** | — | **Structurally impossible after Decision A** — measured in §3.8. Dedup before dispatch makes unique resolved paths a precondition of dispatch, so two concurrent tasks cannot share a name. A cross-run mutex is a different case and remains a recorded residual (§5.7). |
| The second artefact's integrity when a stale entry is re-run | `NET-001` (phase 03) | Transport-level. Its remedy has landed; this plan must not touch it. |
| The ffmpeg **binary** version constraint | `DEP-011` (phase 11) | **Live and now more so** (§2.4.3): the retirement removed the loader, not the merger, and the merger still spawns ffmpeg. |
| `.gitignore` coverage verdict for the residue classes | `DEP-004` (phase 11) | `ART-013`'s per-pattern verdict is recorded **for** `DEP-004` in `P12-B6`'s task specification; the verdict itself is phase 11's. |
| The untracked root scratch; enforcing mypy's no-`Any` rule; test-file `mypy src tests` errors | `DEP-005`, `QLT-009` (phases 11 / 09 / 10) | Owned elsewhere. `mypy src tests` is a delta gate only (§2.1). |
| `pytest` warning counts as a gate | — | Measured at **1** warning at both `4bf9efb` and `58bb7ce`. Warnings are not stable across runs; the gate is the exit code and the pass/skip counts (§2.1). |
| **Fixing the pre-existing `ruff format` failure in `tests/test_hls_downloader.py`** | — | Measured red at `58bb7ce` (§2.0 `G3`). It is a **baseline** defect, not this plan's, and touching it would put an unrelated formatting change inside a filesystem finding's commit. The gate-lock rule in §2.1 is what governs it. |
| Editing `services/downloader.py`'s re-export lines as a fix | — | It is a backward-compat facade with a symbol-ownership comment and an explicit `__all__`. Fixes go in the owning module. Where a block must add a name here, that is plumbing, never the remedy. |

### 1.4 Deferred, with the named owner

| ID | Deferred item | Owner | Why not here |
|---|---|---|---|
| `DEF-1` | An executable oracle for the Windows mode (assert the *request* is recorded where the platform does not enforce it) | `TST-013` (phase 10) | Phase 10 owns the oracle. `ART-007`'s "zero runnable oracles" half is therefore **not closed** by this plan; `P12-B11` records the residual explicitly. |
| `DEF-2` | `.gitignore` coverage verdict for `*.ts`, `batch_*.ts`, `NNNNN.ts.tmp`, `batch_list_*.txt`, `final_list.txt` | `DEP-004` (phase 11) | The finding depends on `DEP-004`'s verdict. `P12-B6` supplies the per-pattern evidence it needs. |
| `DEF-3` | The ffmpeg binary version constraint | `DEP-011` (phase 11) | **Live and strengthened by Decision C** — the merger is permanent and is the only merge (§2.4.3). |
| `DEF-4` | The untracked root scratch | `DEP-005` (phase 11) | Unrelated. |
| `DEF-5` | Enforcing the no-`Any` rule through mypy | `QLT-009` (phase 09) | Unrelated. |
| `DEF-6` | Whether **the extraction call** that Decision A's dedup key requires can itself be avoided for a duplicate | Product Owner | **Measured conflict, not an omission** — §3.8. Resolving the filename requires `title` and `id`, which arrive over the network. If "must not load the network at all" is read to include metadata extraction, the decision's key and its no-network clause are jointly unsatisfiable and the key must change. Recorded for the Product Owner, not silently reinterpreted. |

### 1.5 Plan-local ordering constraint IDs

`VAL-701` is the cross-phase record. It is **not** re-minted here: `VAL-` is a flat namespace already carrying mutually exclusive claims from plans 05–10, and the corpus contains exactly one `VAL-7xx` identifier — `VAL-701` — so the collision risk is prospective. This plan references it **qualified** as `VAL-701 (phase 07, band VAL-7xx)` and carries its own ordering constraint under the plan-local id `ROLLOUT-1` (§3.7, §4).

**Open decisions after the rulings.** `D-1` (containment) and `D-6` (duplicates) are **CLOSED** by Decisions B and A respectively. Still open, each with a stated criterion and deliberately not chosen by this Planner: `D-2` the length bound's scope · `D-3` rename or broaden `sanitize_title` · `D-4` how far to narrow the `ART-004` counts · `D-5` `.part` probe route · `D-7` the Windows confinement posture.

---

## 2. Baseline

### 2.0 Gates — re-run by this Planner against live `HEAD = 58bb7ce`

None of these figures is inherited. All six were executed after the loader retirement landed; the tree under `src` and `tests` is clean at that commit. Figures from the pre-retirement baseline (`4bf9efb`) are given only to show the delta.

| # | Command | Result at `58bb7ce` | Exit | Δ vs `4bf9efb` |
|---|---|---|---|---|
| G1 | `uv run pytest tests/ -q -rs` | **752 passed, 3 skipped, 1 warning** in 40.00s | **0** | −20 passed, **−1 skip** |
| G2 | `uv run ruff check src tests` | `All checks passed!` | **0** | unchanged |
| G3 | `uv run ruff format --check src tests` | **`Would reformat: tests\test_hls_downloader.py` — 1 file would be reformatted, 53 files already formatted** | **1** | **was 0 — see the gate lock below** |
| G4 | `uv run mypy src` | `Success: no issues found in 31 source files` | **0** | unchanged |
| G5 | `uv run mypy src tests` | **`86 errors in 8 files` (54 checked)** | **1** | was 79 |
| G6 | `uv run ruff check .` | `All checks passed!` | **0** | unchanged |

**`G3` is RED at baseline, and that is a fact this plan plans around rather than through.** Two `with patch(...)` context managers in `tests/test_hls_downloader.py` are wrapped across lines that a deletion in the loader's test classes made collapsible. **This is a pre-existing baseline defect, not this plan's.** §2.1's gate lock governs it.

**The skip floor is 3, not 4.** `test_temp_argfile_permissions_are_0600` and its subject `_temp_argfile` were deleted with the loader. The remaining three, identified by their own skip reasons, are:
- `tests/test_config.py` ×2 — `setup_logging`'s mode assertions (D-11)
- `tests/test_hls_downloader.py::TestCreateTempCookieFile::test_file_permissions_are_0600` (D-11)

**No block may change the skip count in either direction**, and no block may add a platform-gated test to work around an unverified behaviour — that would consume the budget `ART-007`'s oracles need.

**`G4` is a usable gate.** `mypy src` is strict (`strict = true`) with exactly one override, for `vkdownloader.cli`, and `ignore_missing_imports = true`. Bare `uv run mypy` has no default target and must never be invoked.

**`G5` is a delta gate only.** It is red before and after. Per-file distribution at `58bb7ce`: `test_hls_downloader.py` **33**, `test_config.py` 30, `test_extractor.py` 10, `test_batch_downloader.py` 5, `test_segment_downloader.py` 4, `test_progress_display.py` 2, `test_quality_spec.py` 1, `test_downloader.py` 1, and **zero in `src/`**. A block may not increase the total, and may not move an error into `src/`.

**The warning count is not a gate.** Measured **1** at both commits (`RuntimeWarning: coroutine 'Event.wait' was never awaited`). The brief's additional two `ResourceWarning: unclosed file` records originate in `config.setup_logging`'s `logging.basicConfig` FileHandler — a real unclosed-handler leak inside `ART-007`'s own subject — and surface non-deterministically. A block that changes the handler lifetime may change this count; nothing else may.

### 2.1 Binding baseline rules

1. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline. §7 is the per-block gate table.
2. **The gate is a two-way lock.** `G1`, `G2`, `G4`, `G6` exit 0. `G5` stays exit 1 and must not increase. **Skip count stays at 3** — `P12-B10` adds one test, so the floor for that block is 4 and returns to 3 nowhere; the count is **3 at rest and 4 inside `P12-B10`'s commit**, and each block's commit body records the count it ran at. Pass count never decreases except by a test this plan deliberately re-scopes (three named assertions in `TestMergeFreeSpaceProbe`; the `--no-part` assertion in `TestYtdlpCliCommand` **only** if `P12-B9` takes route (b) — §3.7).
3. **`G3` is red at baseline and stays red until it is fixed deliberately.** Measured: `tests/test_hls_downloader.py` would be reformatted, in code unrelated to any phase-07 finding. A block that happens to edit that file may reformat only the lines it touches and must leave the pre-existing two wraps alone, so the baseline delta stays attributable. **Whoever restores `G3` to green does it as its own commit** — see §1.3.
4. **New oracles accompany new behaviour in the same commit.** Every block that changes a decision a reader would need to reproduce carries its own test.
5. No block inherits an anchor from the artifact. Every anchor is re-derived by symbol name at execution time.
6. Explicit path staging. Never `git add -A`, `git add .`, or `-u`. Commit shape `{type}({scope}): {description}`. Never amend, never force-push.
7. **`AGENTS.md` does not exist in this repository.** The binding rule set is `.kilo/rules/project.md` — 15 rules. The code uses `structlog.get_logger(__name__)` universally, never `print()` and never `logging.getLogger`.
8. Editing a doc under `docs/` requires reading `docs/00-overview/doc-maintenance-rules.md` first (single source of truth; translate on touch; English only; frontmatter is contract for domain docs). `docs/STRUCT.md` is a root structural map with no frontmatter and is edited in place.

### 2.2 Repository constraints binding on every block

| ID | Constraint | Consequence for this plan |
|---|---|---|
| `C1` | `tests/test_packaging.py` hard-codes `EXPECTED_SDIST_ENTRIES` (**73**) and `EXPECTED_WHEEL_ENTRIES` (**32**) against a real build, plus `BUILDER_ADDED_SDIST_ENTRIES` (2) and `EXPECTED_DIST_INFO_ENTRIES` (4). | Any new file under `src/`, `tests/` or `docs/` requires editing the relevant frozenset **in the same commit**. `P12-B12` adds no file. Every other block adds at most test code in existing files. |
| `C2` | `ignore_missing_imports = true` hides an undeclared import from mypy. | A block that imports a new module must add it to `pyproject.toml`; `G4` will not catch the omission. |
| `C3` | `services/downloader.py` is a backward-compat re-export facade with a symbol-ownership comment and an explicit `__all__`. | Fixes go in the owning module. Editing a re-export line is never the fix. |
| `C4` | `services/ffmpeg_utils.py` is a **leaf**: it imports only `..exceptions` and `..utils.formatting`. | A merge change there **cannot** import `url_sanitizer`, `downloader_throttle`, `downloader` or `security` without breaking the leaf property. `P12-B8`'s leaf-side edit is arithmetic and docstring only. |
| `C5` | Atomicity primitives in use are exhaustively `os.replace(temp, final)` — the only atomic publish, **two** sites, the only `os.replace` in `src/` — plus `missing_ok=True` unlink (measured sites) and bare `unlink()` (measured sites). There is **no** `fsync`, **no** temp-dir abstraction and **no** lock file. | Any remedy that needs durability across a power loss has no existing primitive to build on. That is named as an alternative consequence in `P12-B6`, not assumed. |
| `C6` | `max_concurrent_downloads` defaults to `4`, range 1–16. | The collision window was the default configuration. Under **Decision A** it is eliminated before dispatch (§3.8), so `C6` now constrains the **dedup pre-pass**'s own concurrency, not a race. |
| `C7` | Measured zero occurrences in `src/`: `force-overwrites`, `no-clobber`, `gettempdir`, `iterdir`, `rmtree`. | No existing precedent for a temp-tree sweep or a clobber policy. Any block introducing one is introducing a new pattern and must say so. Plan 11's reaper independently rules out a top-level `%TEMP%` glob and any age heuristic — **this plan accepts that exclusion**. |
| `C8` | `utils/security.py`'s last commit is `e59523c`, older than the audit base. Verified again at `58bb7ce`: **the file is unchanged**, so every `ART-001`/`009`/`010`/`011`/`014` anchor in this plan still holds verbatim. | Every `security.py` line is a live hit. No prior art to imitate and no drift risk. |
| `C9` | `P12-B10` must run a dedup pre-pass that calls `_resolve_output_file` for **every** entry, and that function performs a `mkdir`. | A skipped entry's directory is still created. Harmless when the directory is shared (it is), but it must be **measured and stated**, not assumed — an oracle asserts what the pre-pass does and does not touch. |
| `C10` | `perform_download` already accepts pre-extracted `video_data` and `selected_stream` precisely so extraction can be skipped. | This is the existing contract that makes a two-phase dedup pre-pass possible without re-extracting (§3.8). Pointed at rather than invented. |

### 2.3 Windows-specific behaviour that shapes the remedies

| Behaviour | Consequence |
|---|---|
| `PermissionError [WinError 5]` from `f.unlink()` on a directory; POSIX raises `IsADirectoryError` | **No fix in this plan may be POSIX-shaped.** `P12-B6`'s guard must be phrased by intent, not by the POSIX exception name. |
| `FileExistsError [WinError 183]` at the output `mkdir` when the path exists as a file; `exist_ok=True` does not suppress it | Recorded for `P12-B2` and `P12-B10`: `_resolve_output_file`'s `mkdir` runs for every entry the dedup pre-pass resolves, including a skipped one (`C9`). Decision B removed the refusal that would otherwise have needed a home here. |
| `os.chmod` toggles only the read-only attribute; `Path.touch(mode=…)` ignores the mode | Every artefact that requests `0o600` measures `0o666`; all parent `mkdir`s measure `0o777`. This is the whole of `ART-007`. |
| `os.replace` on NTFS carried the source's `0o666` to the destination | POSIX rename atomicity is **not** claimed for the two publish sites. `P12-B6`/`P12-B7` must not assert durability. |
| Reserved device names behave as ordinary files on POSIX | `ART-014`'s creation half is Windows-only; any oracle is Windows-gated and must be counted against the **3-skip** budget or asserted structurally instead. |

### 2.4 The landing rule — what the retirement changes, recorded explicitly

#### 2.4.1 What this plan must never do

Never plan work that preserves, restores, hardens or documents the ffmpeg **loader**. The loader is deleted, not repaired. **The merger is not the loader** and is permanent product surface (§2.4.4) — the two must never be conflated.

#### 2.4.2 `ART-008` stays retired — empty residue class, for the right reason

`ART-008`'s subject was the ffmpeg argfile: a `vk_ffmpeg_*.args` file written into the **system `TEMP`**, requested at `0o600`, removed in a `finally`, containing a signed CDN URL. Measured at `58bb7ce`: **zero** occurrences of `gettempdir`, `iterdir`, `rmtree` or `TEMP` in `src/`, and `_temp_argfile` no longer exists.

**The correct reason is narrower than "the transport was retired".** The argfile belonged to the **loader** — it existed so the loader's arguments, including a signed CDN URL, would not appear in process listings. The loader was the part removed; the merger stayed and never used it. The residue class is empty because **the artefact went with its owner**, not because a transport was retired wholesale.

**Do not resurrect `ART-008`.** **`P12-B11` plans no sweep**, and §7 carries an explicit assertion that no block introduces one. Plan 11's reaper design reinforces this from the other side: it deliberately rules out a top-level `%TEMP%` glob and any age heuristic, so **no block of this plan may introduce either.**

#### 2.4.3 `ART-007` shrinks but does not close

**Leaves the table:** the argfile row. `_temp_argfile` and its `os.chmod` are gone with the loader. Measured at `58bb7ce`: the surviving chmod calls are `os.chmod` in `ytdlp_downloader._create_temp_cookie_file` and `Path.chmod` in `config.setup_logging`, plus `Path.touch(mode=0o600)` in `setup_logging`.

**Remains, unchanged:** the log file, the log parent directory, the working tree, the output directory, the segments, the merge temps, the concat lists, `.signature`, the final artefact, and the cookie file.

**Untouched:** the zero-compensating-control half and the zero-runnable-oracle half. Recommendation part (2) is `TST-013`'s (`DEF-1`). `P12-B11` addresses only the posture decision.

**Strengthened for `DEP-011`:** the merger is permanent and is the product's only merge, so the ffmpeg **binary** is a harder dependency than before, not a softer one. `DEF-3` stays live and rises.

#### 2.4.4 `ffmpeg_utils.py` — permanent module, permanent merge engine

**Decision C: yt-dlp is the loader; ffmpeg is not a loader transport. Segment download stays, and ffmpeg stays as the segment merge engine.**

`services/ffmpeg_utils.py` is now **493 lines** (was 577; the loader's progress symbols were deleted from it). **`services/ffmpeg_utils.py` can never be deleted whole.** Measured survivors:

| Group | Members (measured at `58bb7ce`) | Fate |
|---|---|---|
| **(A) generic subprocess infra, shared with yt-dlp** | `iter_process_lines`, `cancel_subprocess` + alias `cancel_ffmpeg_process` | **PERMANENT.** `ytdlp_downloader` imports both directly for the child process's stdout draining and cancellation. Deleting them breaks the loader. |
| **(B') ffmpeg availability** | `check_ffmpeg_available` (+ its `_ffmpeg_available` cache) | **PERMANENT — corrected.** An earlier revision of this plan filed it as retiring. **It survives**: `downloader.perform_download` calls it as a startup probe, on the stated ground that users learn about a missing binary before a long download fails at the merge step, and it is in the facade's `__all__`. It is **load-bearing for the merge**, not for the loader. |
| **(B) loader progress reporting — already deleted** | `FfmpegProgress`, `_PROGRESS_KEY_HANDLERS`, `ProgressParser`, `read_progress` | **GONE** with the loader. No block plans their removal; plan 10 already did it. |
| **(C) HLS segment merge engine** | `_MERGE_SPACE_MARGIN_BYTES`, `_build_ffmpeg_concat_command`, `_merge_batch_segments`, `_perform_final_merge`, `_required_merge_bytes`, `_check_merge_space`, `_merge_segments_batched`, `_await_ffmpeg_with_timeout` | **PERMANENT PRODUCT SURFACE.** The segment path has no other merge. **Group C still spawns ffmpeg**, and the Product Owner has ruled it stays. |

**No block in this plan may plan any group C symbol for deletion**, and `P12-B8`'s edit inside `ffmpeg_utils.py` is confined to `_required_merge_bytes`'s arithmetic and docstring (§2.2 `C4`: the module is a leaf importing only `..exceptions` and `..utils.formatting`).

**Withdrawn.** An earlier revision asserted that plan 10's `B10` "does not name `services/ffmpeg_utils.py` for deletion". **False.** It names the module with the exact five symbols to delete. Those five are the group B progress symbols; groups A, B' and C are untouched, which is consistent with the ruling.

**`P12-B12` corrects `docs/STRUCT.md`'s description of the module**, which currently reads "FFmpeg discovery and stream concatenation". It omits the shared subprocess infrastructure entirely — a reader acting on that sentence deletes group A and the loader's stdout draining with it. The sentence is re-checked against the module **as it now stands** in §3.12: "discovery" is now load-bearing again under Decision C, because `check_ffmpeg_available` is the startup probe that protects the merge.

**The eight-file `--method ffmpeg` documentation surface is `P10-B10`'s obligation, not this plan's:** `README.md`, `docs/01-tools/api-reference.md`, `docs/01-tools/installation.md`, `docs/01-tools/quality-selection.md`, `docs/01-tools/vkdownloader-overview.md`, `docs/11-guides/configuration.md`, `docs/11-guides/vkdownloader-limitations.md`, `docs/99-reference/cli-reference.md` and `docs/99-reference/cli-reference-clean.md`.

#### 2.4.5 Unaffected, and one that rises

`ART-001`, `ART-002`, `ART-006`, `ART-009`, `ART-010`, `ART-011` and `ART-014` are **unaffected by the ffmpeg ruling**, except `ART-002`'s caller count, which the retirement already reduced to **one** (`_attempt_segment_resume`) and which is re-verified at `58bb7ce`.

`ART-004`, `ART-012` and the merge stages of `ART-003`, `ART-005` and `ART-013` are **unchanged** — the merge engine stayed, so every one of them still applies in full.

**`ART-012` rises in importance.** With the merger permanent and the only merge, a free-space estimate that is too low (`segment_bytes * 2` against an actual peak of up to `3×`) is a standing defect on the product's single merge path. It is no longer one concern among several; it is the defect that will surface on every large download that fills a volume. `P12-B8` should be scheduled accordingly (§4.2).

#### 2.4.6 `ROLLOUT-1` — `VAL-701`, sharpened, and what Decision A does to it

Before the retirement, entering the segment path required **opt-in** (`--method ffmpeg`'s fallback arm) **or** a failed re-run over an existing file. The retirement deletes the first, leaving the second. So today, `ART-001`, `ART-003`, `ART-004`, `ART-005`, `ART-012` and `ART-013` are reachable **only** by a failed re-run over an existing file — and fixing `ART-002` **in the same batch** makes that path the default. `P12-B9` is therefore placed last, after all six fixes it can expose.

**What Decision A changes, and what it does not.** Dedup reduces *how many items* reach that path — a duplicate no longer dispatches at all, so it cannot contribute a second failed re-run over a file the survivor is writing. It does **not** change *whether* the path is reachable for a non-duplicate item: a single failed re-run over an existing file still reaches it, and `P12-B9` still promotes it to default. **`ROLLOUT-1` therefore stands unchanged, and `P12-B10` may land before or after the six** — it does not need to be sequenced against them. §4 records it as an unordered pair, and §3.8 states the residual (the `.part` half of `ART-002`'s exposure is *reduced*, not removed, because a non-duplicate item still writes a `.part`).

### 2.5 Test layout and the oracle gaps — re-measured at `58bb7ce`

| File (lines at `58bb7ce`) | Classes that bind this plan |
|---|---|
| `tests/test_security.py` (285, **unchanged**) | `TestValidateOutputPath` (6), `TestValidateOutputPathEdgeCases` (3), `TestSanitizeTitle` (6, **pins `ART-011`'s `[:100]` bound**), `TestValidateOutputPathTraversal` (5, **four use real `..` path components**), `TestResolveOutputFile` (6) |
| `tests/test_hls_downloader.py` (**3944**, was 4279 — the loader's test classes were deleted) | `TestCleanupSegments` (**does exercise `_cleanup_segments` with real files**), `TestYtdlpCliCommand` (**asserts `--no-part` is *absent* from the command, by name, with a docstring saying "lets yt-dlp use .part files"**), `TestCreateTempCookieFile` (**one of the three mode oracles**), `TestFfmpegAvailabilityCheck`, `TestAttemptSegmentResumeQuality`, `TestYtDlpRetryBackoff`, `TestYtDlpSubprocessShutdown`. **Gone:** `TestTempArgfile`, `TestFfmpegCookiePassing`, `TestFfmpegProgress`, `TestProgressParser`, `TestReadProgress`, `TestHLSDownloader`, `TestHLSDownloaderDownload`. |
| `tests/test_segment_downloader.py` (1705, **unchanged**) | `TestPreserveSegmentsReporter` (3 tests — **pins the `ART-004`/`ART-005`/`ART-013` dispositions and names `ART-004` in its own docstring**), `TestSegmentFanoutCompletion`, `TestSegmentFanoutBoundedProduction`, `TestConnectorCeilingsFollowTheSetting` |
| `tests/test_ffmpeg_utils.py` (834, **unchanged**) | `TestMergeFreeSpaceProbe` (**7 tests; three pin the `2×` multiplier exactly**), `TestMergeSegmentsBatched` incl. "batch failure preserves inputs and earlier batch temps", `TestMergeBatchSegments`, `TestPerformFinalMerge` |
| `tests/test_config.py` (1223, **unchanged**) | `setup_logging` tests, and **two of the three** mode oracles |
| `tests/test_packaging.py` | `EXPECTED_SDIST_ENTRIES` (73), `EXPECTED_WHEEL_ENTRIES` (32), `BUILDER_ADDED_SDIST_ENTRIES` (2), `EXPECTED_DIST_INFO_ENTRIES` (4) — **all unchanged** |

**What the retirement removed from the oracle set, and what it did not.** The argfile's format and permission tests went with the loader, which is why the skip floor is 3. **Every oracle this plan depends on survives**: `TestPreserveSegmentsReporter`, `TestMergeFreeSpaceProbe`, `TestCleanupSegments`, `TestYtdlpCliCommand`, and all of `test_security.py` are in files that did not change.

### 2.6 Anchor discipline used by this plan

**No `file:line` appears in any block's scope.** Anchors are symbol names, class names, test class names, config keys and doc entries. Every anchor below was located by symbol in the live tree.

**Drift measured at `58bb7ce` relative to the audit base `4bf9efb`:**

| File | `4bf9efb` | `58bb7ce` | Δ |
|---|---|---|---|
| `services/ffmpeg_utils.py` | 577 | **493** | −84 (loader progress symbols deleted) |
| `services/downloader.py` | 582 | **344** | −238 (the loader) |
| `services/ytdlp_downloader.py` | 815 | **845** | +30 |
| `services/segment_downloader.py` | 1283 | **1283** | **0** |
| `utils/security.py` | 111 | **111** | **0** (last commit `e59523c`) |
| `tests/test_hls_downloader.py` | 4279 | **3944** | −335 |
| `tests/test_segment_downloader.py` | 1705 | **1705** | **0** |
| `tests/test_ffmpeg_utils.py` | 834 | **834** | **0** |
| `tests/test_security.py` | 285 | **285** | **0** |
| `tests/test_config.py` | 1223 | **1223** | **0** |

**Consequence, and it is the useful part of this table: every file carrying a phase-07 anchor is unchanged except the loader's own files.** `security.py`, `segment_downloader.py`, `test_security.py`, `test_segment_downloader.py` and `test_ffmpeg_utils.py` did not move at all, so `ART-001`, `ART-003`, `ART-004`, `ART-005`, `ART-009`, `ART-010`, `ART-011`, `ART-012`, `ART-013` and `ART-014` need **no** re-derivation. The re-derivation the earlier revision performed remains valid for those, and was repeated for the loader-adjacent ones. `DownloadMethod` now holds only `YTDLP` and `AUTO`; `FFMPEG` is gone; `download_with_ffmpeg`, `_temp_argfile`, `FfmpegProgress`, `ProgressParser` and `read_progress` are gone.

**Working-tree state after the baseline was measured — re-measure before starting `P12-B8`.** Immediately after these gates were run, `git status` began showing uncommitted modifications to `services/ffmpeg_utils.py` and `services/ytdlp_downloader.py`, introduced by another agent working a transport finding (an over-long-line drain path added to `iter_process_lines`, which is group A). **This plan made no change to any source or test file.** Two implications:
- **The 493-line figure for `ffmpeg_utils.py` is the committed size at `58bb7ce`, not the on-disk size.** Every block re-derives anchors by symbol anyway (§2.6), so no block is invalidated — but `P12-B8`'s edit to `_required_merge_bytes` sits in that file and must be re-measured against whatever is on disk when it starts.
- **The edit is to group A, which Decision C declares permanent.** That is the correct place for it — group A is the shared subprocess infrastructure and survives. It is recorded here so nobody later reads "someone was editing `ffmpeg_utils.py`" as evidence the module is in flux. It is not: the module is permanent surface being maintained, not deleted. This is exactly the misreading `R8` and `C6` in §5.2 and §5.4 name.

---

## 3. Execution blocks

Twelve blocks, one commit each. `P12-B12` is documentation. `P12-B3` is the only CRITICAL. **Five blocks** (`B2`, `B4`, `B5`, `B9`, `B11`) carry an open implementation decision with a stated criterion, and this Planner deliberately does **not** pick the option — **`B2` and `B10` are closed by Decisions B and A and carry no open decision.** The blocks below are presented in **risk order, not execution order**. The execution order and the reason for each position are in `§4.2`.

**Severity → block assignment**

| Block | Finding | Severity | Decides? | Risk tier |
|---|---|---|---|---|
| `P12-B3` | `ART-001` (name half) | CRITICAL | no | High — CRITICAL, touches a pinned class |
| `P12-B6` | `ART-003`, `ART-004`, `ART-013` sweep half | HIGH | `D-4` | High — changes the merge decision |
| `P12-B7` | `ART-005` remaining surface, `ART-013` lifetime half | MEDIUM → HIGH | no | High — owns the shared insertion point |
| `P12-B8` | `ART-012` | MEDIUM | no | **High — the merge is now permanent and the only merge, so an insufficient free-space estimate is a standing defect on the product's single merge path (§2.4.5)** |
| `P12-B9` | `ART-002` + `ROLLOUT-1` | HIGH | `D-5` | **High — the keystone** |
| `P12-B10` | `ART-006` — dedup before dispatch | HIGH | **CLOSED** by Decision A | High — but **reduced**: the within-batch mutex is structurally unnecessary |
| `P12-B11` | `ART-007` (shrunken) | HIGH | `D-7` | High — platform posture, no oracle |
| `P12-B1` | `ART-010` | MEDIUM | no | Medium — security guard semantics |
| `P12-B2` | `ART-009` — make the warning reach the user | MEDIUM | **CLOSED** by Decision B | Medium — **reduced**: no root, no refusal, no scope to decide |
| `P12-B4` | `ART-011` | MEDIUM | `D-2` | Medium — one pinned assertion |
| `P12-B5` | `ART-014` | LOW | `D-3` | Low |
| `P12-B12` | `STRUCT.md` structural map | — | no | Low — one sentence |

### 3.1 `P12-B3` — `sanitize_title` rejects control characters (`ART-001`, CRITICAL)

**Goal.** A title that reaches the filesystem carries no control character.

**Semantic scope.** `utils/security.py::sanitize_title` — the inline character-removal loop and the strip/length logic immediately around it. Both call sites are in scope only insofar as their expectations change: `security._resolve_output_file` (filesystem derivation) and `downloader`'s title callback (`sanitize_title(video.title)`, a **display** string). `tests/test_security.py::TestSanitizeTitle` gains the oracle.

**What must change.** The removal set must cover the C0 control range and `DEL`. Measured survivors today: `\x00 \x01 \x02 \x1f \n \r \t \x7f`. Replaced-by-underscore is the right shape for all of them **except** `\x00`, which Python rejects outright (`ValueError: embedded null byte`) and which must therefore be *replaced*, never passed through.

**Alternatives — no open question, but two shapes the Implementer must choose between, recorded because both are admissible:**
- **(a) Extend the inline set** to `chr(0)…chr(31)` plus `chr(127)`. Minimal diff; keeps the "replace with `_`" shape already established for the nine illegal characters. Leaves `\x80…\x9f` (the C1 controls) untouched — they are not illegal on Windows and `sanitize_title` is a *filesystem* sanitiser, not a text normaliser.
- **(b) Introduce a real named constant** — e.g. `_CONTROL_CHARS` or, correctly named this time, a symbol whose name describes the *behaviour* rather than an illegal-character list. This is the correction §1.1.3 records: the artifact's `_INVALID_FILENAME_CHARS` never existed, and naming the set this time is a real improvement in readability. It also collides with `P12-B5`'s decision about what the utility is.

Criterion: prefer (b) if `P12-B5` chooses to keep the function and broaden it (one named set, one loop); prefer (a) if `P12-B5` chooses to rename the utility, since a rename and a constant rename in one commit is one decision wearing two hats.

**Acceptance criteria.**
1. No character in `chr(0)…chr(31)` or `chr(127)` survives `sanitize_title`, measured by a table-driven test in `TestSanitizeTitle` — not a spot check.
2. `TestSanitizeTitle`'s six existing tests stay green **unchanged**, including `test_strips_windows_illegal_characters` (exact string equality) and `test_limits_length_to_100_characters` (the `ART-011` pin — do **not** widen the bound here).
3. A newline or tab in a video title no longer produces a multi-line log record or console line. One assertion covers the observable consequence.
4. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.
5. No `file:line` in the commit message; the subject is the behaviour.

**Out of scope.** The `_attempt_segment_resume` mislabels (`OUT-016`, phase 08). `[:100]` (`P12-B4`). Device names and trailing dots (`P12-B5`). Whether stripping changes the *display* string is recorded as a consequence, not fixed here.

**Agent roster — Auditor, Researcher, Planner, Validator.** *High risk.* The character-class enumeration is a platform question (which code points a Windows filename may not contain, and which Python rejects before the syscall) — that is Researcher territory. The display-caller consequence is an architecture consequence — Auditor. The block is CRITICAL with zero review slack and a pinned test class one line away — Validator.

---

### 3.2 `P12-B1` — `validate_output_path` detects traversal by component (`ART-010`)

**Goal.** The guard refuses a path whose *components* are `..`, and stops refusing a component that merely *contains* `..`.

**Semantic scope.** `utils/security.py::validate_output_path` — the `".." in str(path)` substring test, which appears at **two layers**: the pre-resolution guard and the post-resolution guard. Both are in scope; the finding is that both are substring tests. `tests/test_security.py::TestValidateOutputPathTraversal` and `TestValidateOutputPath` gain oracles.

**Alternatives — two admissible shapes:**
- **(a) `".." in path.parts`** at both layers. Directly expresses intent. On Windows this is correct for both separators because `PurePath.parts` normalises them.
- **(b) A shared predicate** (e.g. `_contains_parent_reference(path)`) called from both layers. Same semantics, one definition; marginally more structure than rule 5 (avoid overengineering) needs, but the duplication is currently real (two hand-copied substring tests).

Criterion: (a) is the smallest change that is unambiguously correct. Choose (b) only if the Implementer can show the two layers will otherwise drift again. **The decision is low-stakes and this Planner does not withhold it: prefer (a).**

**Acceptance criteria.**
1. A path with a component containing `..` but not equal to it is **accepted**. Measured live today: such a path is rejected with `DownloadError(error_code="path_traversal")`.
2. All five tests in `TestValidateOutputPathTraversal` and all three traversal tests in `TestValidateOutputPath` stay green **unchanged** — they use real `..` components, so a correct component-wise test keeps them green. No test is edited.
3. `test_validate_output_path_rejects_traversal_even_if_resolved` keeps passing **and** a new oracle actually reaches the **post**-resolution layer. Its own comment concedes that `resolve()` yields no `..`, so today it exercises the pre-resolution layer twice. The new oracle must construct the post-resolution case deliberately — for example by patching `resolve` to return a path that still contains a `..` component — and must be distinguishable from the pre-resolution layer.
4. `TestValidateOutputPathEdgeCases::test_empty_path_resolves_to_cwd` stays green (`Path(".")` must still resolve to the cwd).
5. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Out of scope.** Whether the guard has a containment root at all (`P12-B2`). Warning suppression at call sites (`P12-B2`).

**Agent roster — Implementer, Planner, Validator.** *High risk* by the roster rule because it changes what a security guard refuses. No Researcher (no multi-viable approach survives the criterion above) and no Auditor (the change is one expression at two sites, fully located). Validator because the four existing traversal tests must remain green **for the right reason**, and a green suite that now passes the wrong layer is the failure mode.

---

---

### 3.3 `P12-B2` — make the warning actually reach the user (`ART-009`, MEDIUM) — **re-scoped by Decision B**

**Goal.** The warning the tool already emits actually reaches the user. **This block no longer asks whether the comparison should refuse.**

**Decision B — closed.** **Warn only. Do not refuse.** The tool does not restrict `--output` to a root. `D-1` is **CLOSED**: no refusal flag, no root concept, no containment check that blocks a write is in scope or wanted.

**What is now decided behaviour and is therefore NOT a defect:** `C:\Windows\System32` is accepted; `/etc` resolves to `C:\etc` and is accepted; `--output` may point anywhere the process can write. Re-measured at `58bb7ce` and re-stated because it is the answer, not a gap: **these are correct under this ruling.** An earlier revision of this plan filed them as acceptance failures; that framing is withdrawn.

**What remains a real defect.** Two things, and only two:

1. **The warning does not always fire.** Measured: three call sites, **two suppress it.** `security._resolve_output_file` calls `validate_output_path(output_path, warning=False)`; `ytdlp_downloader`'s probe calls `validate_output_path(output_file, warning=False)`. Only `segment_downloader.download_hls_with_resume`'s call uses the default and fires. **Under Decision B the warning is the entire user-facing behaviour of this guard** — so on the loader path, which is now the only default path, it is silent.
2. **`repo_root` derives one level too deep.** `Path(__file__).resolve().parent.parent.parent` from `utils/security.py` yields `…\mko_vkideo\src`, not the repository root. **This is a real defect precisely because the warning is computed from it**: the warning fires for a path under `src\`, and stays silent for a path under the rest of the repository, because `relative_to` fails against the wrong root. Fixing the derivation is not cosmetic — it changes which paths warn, and under Decision B that is the whole of the guard's observable behaviour.

**Semantic scope.** `utils/security.py::validate_output_path` — the module-level `repo_root` expression only, and the `warning` flag's plumbing. The three call sites, for the `warning` argument only: `security._resolve_output_file`, `ytdlp_downloader`'s probe call, `segment_downloader.download_hls_with_resume`'s call. Test targets: `tests/test_security.py::TestValidateOutputPath` and `::TestValidateOutputPathEdgeCases`.

**Alternatives — one open choice, and it is small.**
- **(a) Derive the root from the repository, and let all three sites warn.** `repo_root` becomes the directory that actually contains `src/`, and the two `warning=False` arguments are dropped. Maximum signal; the warning now fires on every download into the repo tree, which for a developer running the tool from a clone is the common case and may be noisy.
- **(b) Derive the root from the repository and keep the suppression deliberate**, documenting *why* the loader and the resolver suppress it (they are internal callers writing to a path the user already chose). Smaller blast radius on log volume; leaves a suppression that has to be re-justified at every future call site.
- **Criterion:** is the warning's purpose "tell the user their download will land in the source tree" or "tell the user this path is inside the tool's own installation"? The first wants (a) at all three sites; the second wants (b). **This is a genuine product question and this Planner does not answer it** — but note that under (b) the `repo_root` fix is still mandatory, because a wrong root makes the warning fire on the wrong set of paths in *both* options.

**The oracle gap is why this block needs its own eyes.** `TestValidateOutputPath::test_path_inside_repo_warns` **mocks `Path.resolve`**, returning a mock whose `relative_to` always succeeds. It asserts that a warning was logged with `path` and `repo_root` keys, and **it cannot fail if `repo_root` points one level too deep**, because the mock replaces the whole derivation. A fix that adds an assertion to that test without addressing the blind mock proves nothing.

**Acceptance criteria.**
1. `repo_root` derives to the directory that contains `src/` — i.e. the repository root, not `src/` itself. Asserted by value, not by a mock.
2. A **new** oracle detects the mis-derivation: a path under the repository root but **outside** `src/` warns, and a path under `src/` still warns. Today the first case does not warn and the test suite cannot see it.
3. `test_path_inside_repo_warns` either loses its `Path.resolve` mock or gains a companion that exercises the real derivation. **If it loses the mock, that is stated in the commit body** rather than done silently.
4. Whatever option is chosen, the suppression question is **resolved rather than left half-answered**: either all three sites warn, or the remaining suppression is documented at the site. It must not stay warn-only at one site and silent at two for no stated reason.
5. `TestValidateOutputPathEdgeCases` (`test_empty_path_resolves_to_cwd`, `test_absolute_path_valid`, `test_relative_path_valid`) stays green unchanged — `Path(".")` must still resolve to the cwd.
6. **No behaviour changes beyond the warning.** Specifically: a path outside the repository root is still accepted silently, a path inside it is still accepted, and the `..` guard still raises. Asserted, because the temptation under a "make the warning reliable" heading is to start refusing.
7. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Out of scope.** The `..` detection (`P12-B1`). **Any refusal, root concept, or write-blocking check** — foreclosed by Decision B. Any change to what `_resolve_output_file` composes, except the `warning` argument it passes. `FileExistsError [WinError 183]` at the `mkdir` is no longer this block's problem, because nothing here creates a root — it is now `P12-B10`'s (`C9`).

**Agent roster — Auditor, Planner, Validator.** *Reduced from all-agents.* Researcher is **dropped**: with the refusal options gone, there is no best-practice question left — it is a product-scope question about log signal, which a Planner surfaces and the Product Owner answers. Auditor stays because the blind mock means the derivation's real behaviour has not been observed by anything. Validator stays because the highest-risk outcome here is a "fix" that quietly starts refusing paths, which would pass every existing test.

---

### 3.4 `P12-B6` — make the sweeps match what the tree contains (`ART-003`, `ART-004`, `ART-013` sweep half)

**Goal.** Three related reconciliations, one commit: the cleanup loop stops raising on a non-regular entry; the `*.ts` count that decides the merge stops counting merge temps; the staleness sweep stops leaving `*.ts.tmp` behind.

**Semantic scope.**
- `services/segment_downloader.py::_cleanup_segments` — the bare `f.unlink()` over `glob("*")`. Add an intent guard: skip what is not a file, and tolerate what has already gone. **Windows-shaped, not POSIX-shaped**: the operative failure is `PermissionError [WinError 5]` from unlinking a directory, so the guard must be phrased by intent (remove the file entries; leave directories alone) rather than by catching the POSIX exception name.
- `services/segment_downloader.py::_tally_and_merge` — the `downloaded_count` derived from `glob("*.ts")`, which is the count the merge decision reads. `batch_NNNNN.ts` matches it exactly as `NNNNN.ts` does. Exclude the merge temps **here**.
- `services/segment_downloader.py::_clear_stale_segments` — the same `glob("*.ts")` sweep. Extend it to the residue the publish sites actually create: `output_path.with_suffix(output_path.suffix + ".tmp")`, two sites. No existing pattern matches it (`glob("*")`, `glob("*.ts")`, and the `f"{i:05d}.ts"` enumeration all miss it), so a resumable run never reconciles it.
- `tests/test_hls_downloader.py::TestCleanupSegments` — **extend; it already exists** and already drives `_cleanup_segments` with real files. Add the non-regular-entry case that is the actual gap.
- `tests/test_segment_downloader.py` — add oracles for the narrowed merge-decision count and the extended sweep.

**Alternatives.**
- **Merge-temp exclusion (the `D-4` decision — this Planner does not pick).**
  - **(i) Narrow only the merge decision's count.** The reporter's count stays a raw working-directory inventory, consistent with its own `next_action` ("clear the working directory") and its `count_note`. Consequence: `TestPreserveSegmentsReporter::test_count_includes_merge_temps_and_says_so` (which asserts `working_dir_ts_count == 3` with `batch_00000.ts` present) stays **green unchanged**. The `ART-004` deferral note inside `_merge_segments_batched` must still be updated, because the deferral is now discharged.
  - **(ii) Narrow both counts.** One definition of "a resumable segment", one helper, both call sites agree. Consequence: the pinned test above must be **edited** to assert a narrowed count and the `count_note` text must change, because a note that says "this is not a count of resumable segments" becomes false once merge temps are excluded.
  - **Criterion:** is `_log_preserve_segments`'s number an *inventory of the working directory* or a *count of resumable segments*? The function's own docstring, `next_action` and the pinned test all say inventory. Choose **(i)** unless the product wants the reporter's number to be actionable as a resume estimate — in which case (ii), and the pinned test's edit is declared, not silent.
- **`.ts.tmp` residue.** Two shapes: (a) extend `_clear_stale_segments`'s sweep to cover the temp suffix as well as `*.ts`; (b) sweep the temp suffix in `_cleanup_segments` as well, so a completed download reconciles it. Criterion: (a) alone leaves the residue for a *failed* run whose `.signature` still matches — the exact case the sweep exists to handle. **Prefer (a)+(b): both call sites, one suffix constant.**

**Acceptance criteria.**
1. A directory inside the working tree no longer turns a completed download into an exception. Oracle: extend `TestCleanupSegments` with a directory entry, on Windows and POSIX alike, asserting the call returns and the file entries are gone. Assert **no** POSIX-specific exception type.
2. `_tally_and_merge`'s count excludes `batch_*.ts`. Oracle: a tree of the expected number of `NNNNN.ts` files **plus** one or more `batch_NNNNN.ts` files reaches the merge (rather than returning `None` on a count mismatch).
3. `_clear_stale_segments` reconciles `NNNNN.ts.tmp`. Oracle: a `.ts.tmp` beside the segments does not survive a stale sweep.
4. `TestPreserveSegmentsReporter`'s three tests stay green, **or** — if `D-4` resolves to (ii) — the one affected test is edited and the edit is declared in the commit body with the reason.
5. `TestMergeSegmentsBatched`'s "batch failure preserves inputs and earlier batch temps" stays green **unchanged**. This is the load-bearing D-13 preservation oracle: it asserts that a graceful failure leaves the accumulated batch temps, which is precisely the `ART-004` residue. The block must not weaken it.
6. `_merge_segments_batched`'s in-code `ART-004` deferral note is updated to record that the deferral is discharged, and `segment_downloader._log_preserve_segments`'s `ART-004` note is updated to match whichever side of `D-4` was taken. The `_log_preserve_segments` comment currently says excluding the temps "is phase 07's `ART-004`; until then the count is stated as a working-directory count".
7. `_cleanup_segments` is still called **only** under `if result:`. This block does not add call sites — `P12-B7` does. Stated so the two blocks are not confused.
8. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Out of scope.** The download-stage probe and the merge multiplier (`P12-B8`). The `.signature` semantics and the working-tree lifetime (`P12-B7`). Adding `fsync`, a temp-dir abstraction or a lock file — `C5` says none exists, and inventing one here is a redesign.

**Agent roster — Auditor, Researcher, Planner, Validator.** *High risk, all agents.* It changes the decision that decides whether a merge runs — the single most consequential predicate in the segment path. Auditor: the residue set must be established from what the tree can actually contain, not from what the finding lists. Researcher: the "which patterns must a sweep match" question has multiple viable approaches and a platform-shaped answer. Planner: `D-4` is a real fork with a test-pinning consequence on either side. Validator: three blocks in this plan (`B7`, `B8`, `B9`) are ordered by this block's semantics, so an error here propagates.

---

### 3.5 `P12-B7` — the working tree's lifetime, and the shared insertion point (`ART-005` remaining surface, `ART-013` lifetime half)

**Goal.** The working directory is created when the run needs it and removed on every exit that did not reach a merge, so a `.ts.tmp` residue and a complete segment set reconcile rather than accumulate.

**Semantic scope.**
- `services/segment_downloader.py::download_hls_with_resume` — the `segments_dir.mkdir(parents=True, exist_ok=True)` that currently runs **before** the playlist is fetched, and the single `finally` that only *reports* on a non-success exit. Create the tree after the playlist has been parsed and its segments enumerated; remove it on every exit that did not produce a merged output, not only after the merge succeeds.
- `services/segment_downloader.py::_clear_stale_segments` and `_compute_playlist_signature` — the `.signature` write is self-perpetuating: the file is written into the tree that was just swept, so the next run finds a matching signature and short-circuits. That is what makes `ART-004`'s residue survive. This block closes the lifetime; whether the `.signature` short-circuit also needs to consider the residue is `P12-B6`'s sweep decision, and the two must not both change the short-circuit without saying so.
- `services/segment_downloader.py::_cleanup_segments` — **new call sites**, for the exits that fail before or instead of a merge. These are the call sites the shared insertion point serves.
- `services/segment_downloader.py::_run_download_session` — the playlist fetch currently happens inside the session and the tree already exists by then; deferring the `mkdir` means the directory is not available to the sweep at fetch time. The order of `mkdir`, `_clear_stale_segments` and the fan-out must be re-established explicitly, and the docstrings updated to match.
- `tests/test_segment_downloader.py` — oracles for: no tree before the playlist is known; the tree removed after a failed session; the tree removed after a graceful merge-stage failure; the tree removed after a `FileNotFoundError` from the merge's own existence check.

**The shared insertion point.** The artifact's own analysis found that `ART-005` and `ART-013`'s lifetime half converge on one insertion point, and that `ART-005` is the finding that should carry it. This block carries it. **`P12-B6` must land first** so the guard exists before these new call sites use it — that is the reason for the `B6 → B7` edge in §4.

**Alternatives.**
- **(a) One removal point** in `download_hls_with_resume`'s existing `finally`, extended to remove rather than report, with the `if result:` success case exempted. One place, one decision, matches the existing structure.
- **(b) Remove at the layer that knows why it failed** — inside `_run_download_session` for a fetch failure, inside `_process_downloaded_segments` for a fan-out failure, inside `_tally_and_merge` for a merge failure. More precise, but three sites, and the tree's lifetime is then no longer one function's responsibility.
- **Criterion:** does the operator ever want the tree preserved after a failure for manual inspection? Today the only thing that happens on failure is a log record telling them to clear the directory — nothing reads the tree. If the answer is no, (a) is correct and strictly smaller. Choose (b) only if a preservation requirement appears.

**Acceptance criteria.**
1. No working directory exists before the playlist has been parsed and its segments enumerated. A session that fails at the playlist fetch leaves **no** tree.
2. Every non-success exit removes the tree: playlist failure, fan-out failure, graceful merge-stage failure, and the merge's own `FileNotFoundError` precondition. Each has an oracle.
3. **The merge's success path is unchanged** — the tree is removed after a successful merge exactly as today, and the merged artefact is never inside the tree.
4. `TestPreserveSegmentsReporter`'s three tests stay green **unchanged**. This is the fixed-and-pinned half of `ART-005`: the reporter reports on **every** non-success exit including a zero-count directory. **If this block removes the tree, the reporter's `working_dir_ts_count` will read 0 on the paths it now observes — that is acceptable and correct, but the block must verify the reporter's contract still holds (a record is emitted, the count is the working-directory count of a tree that was just removed, the `next_action` is still truthful) and must not reintroduce any count gate.** If the reporter is no longer reachable because the tree is gone before it runs, the reporter's call must move with the removal, and the pinned tests must still pass — declare that in the commit body if it happens.
5. `TestSegmentFanoutCompletion`, `TestSegmentFanoutBoundedProduction` and `TestConnectorCeilingsFollowTheSetting` stay green **unchanged**.
6. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Out of scope.** The `.signature` short-circuit's reconciliation with the residue (`P12-B6`). Any disk-space behaviour (`P12-B8`). Reintroducing a count gate anywhere — forbidden by the pinned tests.

**Agent roster — Auditor, Planner, Validator.** *High risk.* Auditor: the tree's lifetime is decided across three functions and the session's error paths have to be enumerated before a removal point can be chosen — deeper investigation than a diff can settle. Planner: three findings converge on one insertion point, and the `if result:` guard this block depends on is `P12-B6`'s. Validator: the pinned reporter class is the one thing standing between this block and a silent regression of an already-landed fix. No Researcher — there is one question here (lifetime) and one shape of answer.

---

### 3.6 `P12-B8` — the download stage needs space too, and the merge now needs three times the segments (`ART-012`)

**Goal.** Give the download stage a free-space precondition, and correct the merge's sizing to match the additive merge that actually landed.

**Semantic scope.**
- **New probe, download stage.** `services/segment_downloader.py` — the segment fan-out has no space precondition of any kind. Measured: the tree's only probe is `shutil.disk_usage` inside `_merge_segments_batched`, called once before batch 1. The new probe needs a demand figure for the download stage, which the code does not currently have: a segment count and a per-segment size estimate. Where the estimate comes from is an implementation decision (below).
- **Merge multiplier.** `services/ffmpeg_utils.py::_required_merge_bytes` — still `segment_bytes * 2 + _MERGE_SPACE_MARGIN_BYTES`, with a docstring that still justifies `2×`. The landed additive merge holds segments **plus** the accumulated batch temps **plus** the growing final output, so the peak is up to `3×`. The module's own comment says this and assigns the sizing to phase 07's `ART-012`. **This edit must stay arithmetic and docstring only** (`C4`: the module is a leaf importing only `..exceptions` and `..utils.formatting`; a merge change cannot import the segment layer).
- `services/ffmpeg_utils.py::_merge_segments_batched` — the deferral comment that assigns the sizing here is discharged by this block and must be updated.
- `tests/test_ffmpeg_utils.py::TestMergeFreeSpaceProbe` — **three assertions must change, and this is declared, not silent** (below).

**The declared test change.** `TestMergeFreeSpaceProbe` pins the `2×` multiplier **exactly**, in three places: `test_required_bytes_cover_final_merge_headroom` (asserts the required value equals `segment_bytes * 2 + _MERGE_SPACE_MARGIN_BYTES`), `test_required_bytes_ignore_missing_segments` (asserts `2000 * 2 + _MERGE_SPACE_MARGIN_BYTES`), and `test_insufficient_space_fails_before_spawning_ffmpeg` (asserts the error message contains `str(3 * 2048 * 2 + _MERGE_SPACE_MARGIN_BYTES)`). Correcting the multiplier necessarily breaks all three. Each must be re-expressed against the new multiplier and against the invariant it was actually protecting — the docstring of the first says the assertion that matters is "fails if the arithmetic drifts toward the segment total alone", so the replacement must keep that direction of protection, not merely restate the number. **The commit body must name all three.**

**Alternatives — download-stage demand figure.**
- **(a) Probe once, up front, on a fixed per-segment budget.** Multiply the expected segment count by a configurable or constant per-segment size. Simplest; the figure is a guess before any byte has arrived.
- **(b) Probe incrementally.** Fold a space check into the fan-out at a bounded interval (every N completed segments), against the running high-water mark. Accurate; adds a decision inside the concurrency-bounded pump, which is the most delicate code in this plan (`CON-003`/`CON-006`/`CON-007` all live there).
- **(c) Probe once, up front, on the observed bytes of the first completed batch.** Accurate after the first batch, cheap, and no pump-internal decision — but it cannot pre-empt a run that is already out of space before batch 1 completes.
- **Criterion:** can the download stage *fail meaningfully before the merge*? The merge's own docstring already carries this argument for itself ("running out of space halfway through turns a large download into a failed one with no partial result"), and segments **are** resumable, so the download stage's failure is not catastrophic — unlike the merge's. That asymmetry argues for the cheap option: **prefer (a) or (c), not (b).** Choosing (b) means adding a decision inside the pump and must argue why the resumability of the download stage does not apply.

**Alternatives — the multiplier.**
- **(a) `segment_bytes * 3 + margin`.** Matches the additive merge's measured peak. Over-estimates for single-batch merges (≤100 segments), where the peak is ~2×.
- **(b) Peak-aware: sum the segments plus the batch temps the merge will accumulate**, computed from the batch size the merge actually uses. Accurate for both one-batch and many-batch merges. Requires `_required_merge_bytes` to know the batch size, which is currently a local literal inside `_merge_segments_batched` — so the batch size must become a named module constant shared by both. Still arithmetic, still leaf-safe.
- **(c) Keep `2×` and record the gap.** Honest, closes nothing.
- **Criterion:** is a fixed `3×` acceptable when a one-batch merge — the common case, ≤100 segments — now demands 50% more free space than it needs? If the product prefers a predictable constant over a slightly better estimate, (a). If the extra headroom is judged a real cost on large volumes, (b). **(b) is the better engineering answer and costs one named constant; this Planner does not withhold the choice.**

**Acceptance criteria.**
1. A download that cannot fit raises an actionable `DownloadError` **before** the fan-out begins, naming the required and available figures — the same shape the merge's probe already uses, and the same `hint` about writing to another volume or selecting a lower quality.
2. The merge's required bytes reflect the additive merge's real peak. Whichever multiplier is chosen, the *direction* of the three pinned assertions is preserved: the requirement must never drift toward the segment total alone.
3. All three `TestMergeFreeSpaceProbe` assertions updated and **named in the commit body** with the reason. The remaining four tests in that class stay green unchanged, including the "one byte below the requirement fails" boundary test — which must still be a boundary, i.e. the new figure must not be rounded.
4. `_required_merge_bytes`'s docstring justifies the new figure and no longer claims `2×`.
5. `_check_merge_space`'s existing behaviour is otherwise untouched: a missing segment still contributes nothing and is reported by the existence check that runs next, and an unreadable mount still does not block the merge.
6. **The tree's free-space probe count goes from one to two, and `shutil.disk_usage` gains exactly one call site.** Assert this by grep, not by eye — the finding is specifically that no download-stage probe exists, and a future block must be able to see both.
7. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Out of scope.** The artifact's 3.15× / 1.40× figures — they were measured on a synthetic 250-segment set the artifact itself marks non-transferable and were never re-driven; do not cite or reproduce them. Any change to the merge's staging. The ffmpeg binary version constraint (`DEP-011`).

**Agent roster — Auditor, Researcher, Planner, Validator.** *High risk, all agents.* Researcher: "how should peak disk be estimated for a staged merge, and where should the check live" is a best-practice question with several viable answers and real platform consequences. Auditor: the additive merge's actual peak must be established from the landed code, not from the finding's transferability-flagged numbers — and it must be established for the one-batch case too. Planner: the declared three-assertion test change needs a designed replacement that keeps the invariant, not a restated constant. Validator: this block makes the tree harder to write tests against, which is a regression in its own right.

### 3.7 `P12-B9` — the probe and the cleanup must name what the child actually writes (`ART-002`, HIGH) — the keystone

**Goal.** The "did yt-dlp get anywhere?" question and the partial-file cleanup must both refer to the file yt-dlp writes.

**Semantic scope.**
- `services/ytdlp_downloader.py::download_with_ytdlp_with_resume_fallback` — the partial-file probe, which validates the output path and then tests the **final** name's existence and non-zero size.
- `services/ytdlp_downloader.py::_build_ytdlp_cli_command` — the command construction, which passes **no** `--no-part` (measured: zero occurrences of `no-part` in `src/`). yt-dlp's `FileDownloader.temp_name` therefore writes `<name>.part`.
- The `DF-008` cleanup at the end of the retry loop, which unlinks the **final** name.
- `services/ytdlp_downloader.py::_attempt_segment_resume` — the sole remaining caller of `download_hls_with_resume` after the retirement; the probe is what decides whether it runs, and the unlink inside it (`output_file.unlink()`) discards whatever partial state the probe found.
- `tests/test_hls_downloader.py::TestYtdlpCliCommand` — **asserts `--no-part` is *absent* from the command, by name**, with a docstring saying "lets yt-dlp use .part files". Route (b) breaks this test by name.

**Severity, re-derived.** The artifact rated this HIGH on the chain "the child writes `.part`, so the probe never fires, so the segment path is dead on arrival". The retirement deletes the `--method ffmpeg` fallback call site, which leaves `download_hls_with_resume` with **exactly one** caller, gated only on the final name existing with non-zero size. So the residual defect is no longer "the path is unreachable" — it is "the gate tests the wrong file", and it is the **only** gate. **HIGH is confirmed, and the consequence is sharper than the artifact's:** whatever else the finding was, after the retirement it is the single switch between "yt-dlp retries" and "the segment path takes over and discards the partial file".

**Alternatives — `D-5`. This Planner does not pick.**
- **(a) Repoint the probe and the cleanup at `<name>.part`.** The child's crash-safe resume is preserved: the `.part` is what lets yt-dlp itself resume an interrupted transfer, and the probe then sees real partial progress. Requires one helper that derives the temp name from the final name, used by both the probe and the `DF-008` cleanup so they cannot drift. Touches `ytdlp_downloader.py` only.
- **(b) Pass `--no-part` so the child writes the final name.** Then the probe is correct as written and the cleanup is correct as written. Cost: the child loses its own resumability, and `TestYtdlpCliCommand`'s `--no-part`-absent assertion must be **edited** (declared, not silent), and its docstring's stated intent — "lets yt-dlp use .part files" — becomes the thing being removed.
- **(c) Probe both names**, preferring the final name and falling back to `.part`. Correct under either invocation; two names to reason about, and the `DF-008` cleanup then needs the same two-name logic.

**Criterion:** which one preserves the behaviour the retry loop exists for? The loop retries because a transfer can be interrupted and resumed. Route (b) removes the child's ability to resume its own transfer and replaces it with the segment path's resume — a different mechanism with different preconditions (it needs a fresh browser token, which is exactly what `_attempt_segment_resume` forces). **A reader acting on this plan should treat (a) as the default and (b) as requiring an explicit argument for why losing the child's resumability is acceptable.** Neither route is free: see `ROLLOUT-1` below, which both routes trigger.

**`ROLLOUT-1` — the ordering constraint, and what happens if it is inverted.** Fixing this block moves `ART-001`, `ART-003`, `ART-004`, `ART-005`, `ART-012` and `ART-013` from "a failed re-run over an existing file, only" to **default reachability**, because the probe will now fire whenever the child leaves partial state. Therefore:
- **`P12-B9` is the last block in this plan.** It depends on `P12-B3`, `P12-B6`, `P12-B7` and `P12-B8` (§4).
- If the order is inverted anyway, the six findings must be **re-triaged as default-reachable before this block lands**, not after. The consequence of getting this wrong is a defect class that only appears on the default path, with the finding's own severity note saying it was opt-in.
- Landing this block **in the same batch** as any of the six makes them default-reachable in the same release. That is not forbidden; it is a decision that must be taken deliberately and written down, not inherited from a block ordering.

**Acceptance criteria.**
1. The probe and the `DF-008` cleanup refer to the same name the child writes, by construction — one helper, two callers, so they cannot diverge. An oracle asserts both use it.
2. The probe's contract is unchanged in shape: "the child made progress" still means existence **and** non-zero size, and the second condition is still load-bearing (a zero-length `.part` must not count as progress).
3. The retry loop's structure is untouched: the probe still gates `_attempt_segment_resume`, and exhausting the loop still logs and returns `None`.
4. The `output_file.unlink()` inside `_attempt_segment_resume` — which discards the partial state to start the segment download clean — is **not changed** by this block. Whether discarding an existing final artefact on the retry path is acceptable is `ART-006`'s question and `ROLLOUT-1`'s risk, not a decision to fold in here. Record it; do not fix it.
5. If route (b): `TestYtdlpCliCommand`'s `--no-part`-absent assertion is edited, and the edit is **named in the commit body with the reason**. If route (a) or (c): that test stays green **unchanged**.
6. `TestYtDlpRetryBackoff` and `TestAttemptSegmentResumeQuality` stay green unchanged.
7. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Out of scope.** The `--method ffmpeg` transport and its fallback arm (deleted by `P10-B10`; this plan does not touch it). The mislabels inside `_attempt_segment_resume` (`OUT-016`, phase 08). Whether a partially-downloaded final artefact should ever be overwritten (the unlink at acceptance criterion 4) — recorded, not fixed.

**Agent roster — Auditor, Researcher, Planner, Validator.** *High risk, all agents.* This is the plan's keystone and the only block whose landing changes the reachability of six other findings. Auditor: whether a `.part` is really what this yt-dlp version writes for this invocation needs verification against the installed version, not against the artifact. Researcher: the two-route question has current-best-practice dimensions (yt-dlp's own resumability model, `--no-part` semantics across versions) and the answer is version-sensitive. Planner: `ROLLOUT-1` must be designed as a release-level constraint, not a commit-order note. Validator: the block makes six other findings default-reachable, so it needs independent confirmation that the reachability analysis is right.

---

### 3.8 `P12-B10` — deduplicate by resolved output filename, before dispatch (`ART-006`, HIGH) — **re-scoped by Decision A**

**Decision A — closed.** **Deduplicate by resolved output filename BEFORE any dispatch. The LAST occurrence in the list wins. Earlier occurrences are skipped, reported, and must not load the network at all.**

**`D-6` is CLOSED, and neither option this plan offered was chosen.** Rejecting duplicates in the reader is not what happens — the last occurrence downloads. Disambiguating in the resolver is not what happens — no suffix is added, because the file name is unchanged. The criterion recorded against `D-6` — *"is a duplicate URL a user error or a legitimate repeat request? The reader's precedent is that malformed input is rejected, not repaired"* — is **retained as the test the ruling was decided against**, and the ruling answers it differently: a duplicate is neither an error to reject nor a name to disambiguate. It is an entry to drop, and the one that survives is the last.

**The dedup key is the resolved output path, not `(title, id)`.** `_resolve_output_file` composes `{safe_title}_{video.id}.mp4`, falling back to `{index}_{video.id}.mp4` when the video has no title. The resolved `Path` is the key, for two measured reasons:
- **Different titles can sanitise to the same filename.** `sanitize_title` replaces each of the nine illegal characters with `_`, and — after this plan's own `P12-B3`, `P12-B4` and `P12-B5` — control characters with `_`, applies the `[:100]` bound, and maps reserved device names. So `a?b` and `a:b` produce one `safe_title`, and two titles differing only past character 100 produce one truncated string. A `(title, id)` key misses both.
- **`output_index` already discriminates one case.** Two entries with the same `id`, different indices and no title get different names. A `(title, id)` key would **over-dedup** those. The resolved path gets it right for free, because it is the thing that actually collides.

**MEASURED CONFLICT — the "no network at all" clause cannot be met literally at this key, and the plan does not paper over it.** `download_video` calls `extractor.extract_streams(url)` and only then calls `_resolve_output_file`. **The resolved filename is not knowable before a network call, because `title` and `id` arrive with the extraction.** The decision's key and its no-network clause are jointly unsatisfiable if "any network fetch" includes metadata extraction. What is achievable, and what this block plans:
- **A skipped entry performs no media transfer of any kind** — no dispatch, no permit, no yt-dlp subprocess, no segment fetch, no `.part`, no working tree, no merge. That is the substance of the clause and it is fully enforceable.
- **A skipped entry still costs one extraction call**, because computing the key requires it. Recorded as `DEF-6` for the Product Owner rather than reinterpreted.
- The two-phase shape is supported by an **existing contract**: `perform_download` already accepts pre-extracted `video_data` and `selected_stream` precisely so extraction is not repeated (`C10`). The pre-pass hands the buffered extraction forward rather than re-fetching.

**MEASURED — the name-level mutex is NOT needed for the within-batch case, and the block shrinks accordingly.** This is the "measure and say, do not assume" check. After dedup:
- the surviving set has **unique resolved output paths by construction**, because that is the dedup key and duplicates were dropped;
- each survivor gets its **own** permit in `perform_download`, and its `output_file` is computed before the permit is taken;
- therefore **no two concurrently dispatched tasks can share a name**, and within-batch collision is **structurally impossible**, not merely unlikely. The `.part` is derived from the output path, so unique paths also mean unique `.part` files.
- **A name-level mutex is therefore OUT of scope** (§1.3). `ART-006` shrinks from "handle collisions during download" to "eliminate them before dispatch". No lock file, no lock primitive — consistent with `C5`.

**What still needs a mutex, stated as a residual rather than solved:** dedup is **per invocation**. Two concurrent runs into the same output directory are two invocations and neither sees the other's names. And `_attempt_segment_resume`'s `output_file.unlink()` deletes the final name, so across runs one invocation can still remove another's artefact. That is the cross-run case, and it is **out of scope** (§5.7).

**Semantic scope.**
1. `services/downloader.py::download_video` — the extract → `title_callback` → `_resolve_output_file` → `perform_download` pipeline. The pre-pass sits between resolution and dispatch. Its docstring states the pipeline.
2. `src/vkdownloader/cli.py` — the `batch` command's URL reader: `valid_urls`, `skipped_count`, the per-line validation loop. **Where the skipped entries are counted**, because it already owns "how many entries did not make it".
3. `utils/security.py::_resolve_output_file` — **the dedup key producer.** Read for its key; **not modified** except for the `warning` argument under `P12-B2`.
4. `services/batch_downloader.py` — the fan-out threading `output_index` and creating per-video tasks under the shared semaphore; and the reporting path (`_print_batch_summary`, the per-item `results` accounting).
5. `tests/test_cli.py::TestBatchCommand` — extended. **The oracle set lives here**; none of it exists today (§2.5).

**Where the skip is reported — existing machinery, no new channel.** "Skip" implies the user is told. Two homes already exist and both are used:
- **Per item:** `ProgressStatus.SKIPPED` — the member already exists in `models/enums.py`, and the batch `results` list already carries one such label per entry. A skipped entry joins that list.
- **In aggregate:** the summary line `_print_batch_summary` already prints for `skipped_count`. A dedup skip is a **different reason**, so it needs a **second line** rather than being folded into the invalid-URL count — folding them would tell the operator their file was malformed when it was fine.
- **No new reporting channel is invented.** `exceptions.py`'s `_map_exception_to_status` is the existing exception-to-label mapping and is **not** the vehicle: a dedup skip is not an exception.

**Interaction with `ROLLOUT-1`.** Dedup reduces how many items reach the segment path, and a skipped item cannot contribute a second failed re-run over a file the survivor is writing. It does **not** change whether the path is reachable for a non-duplicate item. **`ROLLOUT-1` stands, and `P12-B10` is unordered with respect to `B3`/`B6`/`B7`/`B8`/`B9`** (§4.1).

**Interaction with `ART-002`'s `.part` probe (`P12-B9`).** If a duplicate never dispatches, **no `.part` is created for it**, so the "two entries sharing one `.part`" half of `ART-002`'s exposure is **eliminated within a batch**, not merely reduced. But a **non-duplicate** item still writes a `.part`, so the half that matters — the probe and the `DF-008` cleanup naming the wrong file — is **untouched**. `P12-B9`'s scope is unchanged and its two routes remain open (`D-5`).

**Alternatives — one open choice: where the pre-pass lives.**
- **(a) In `download_video`, per entry.** Each entry resolves, reports its resolved path to a batch-scoped registry, and is told whether it survives. Last-wins requires the registry to overwrite; earlier entries have been resolved but **none has dispatched**, which is what the decision requires. Cost: the registry must be threaded, must be **batch-scoped** (the single-URL `download` has one entry and must not pay for it), and under this shape **every** entry is extracted regardless of whether it will be dispatched.
- **(b) A separate resolution phase in `batch_downloader`, before the fan-out.** All entries are extracted and resolved, dedup runs once, survivors are dispatched. The registry's lifetime is obvious. Cost: extraction for **every** entry completes before any download starts, changing the batch's latency profile and needing its own bounding decision — extraction is currently interleaved with downloads under the shared semaphore.
- **Criterion:** does the batch's user-visible progress stay meaningful during a long batch? Under (b) the screen shows resolution for all N and then downloads; under (a) the two interleave. **This Planner does not pick** — but note (b) is the only shape in which "must not load the network at all" is even approximately true. **If the Product Owner's no-network clause is strict, that forces (b).**

**Acceptance criteria.**
1. Two entries resolving to the same output path produce **exactly one dispatch**, and it is the **last** occurrence in list order. Oracle: dispatch call count **and** the identity of the dispatched entry.
2. A skipped entry performs **no media transfer** — no dispatch, no permit, no subprocess, no segment fetch, no `.part`, no working tree. Asserted by patching each and asserting not-called for the skipped entry: the clause is load-bearing, so it gets an explicit oracle rather than an inference from the dispatch count.
3. The skip is **visible** through the existing channels: `ProgressStatus.SKIPPED` in `results`, and a dedup-skipped summary line **distinct** from the invalid-URL line. Oracle at both levels.
4. The key is the **resolved output path**. Oracle, both directions, because they are the two reasons it is not `(title, id)`: two entries whose different titles sanitise to the same filename **are** deduped; two entries with the same `id`, different `output_index` and no title are **not**.
5. A re-run of the same URL file into the same directory is **idempotent** — the same entries are skipped and the same one downloads, because dedup is a function of the list, not of the filesystem.
6. The single-URL `download` command is unchanged and does not pay for the registry.
7. `TestBatchDownloaderSemaphore`, `TestBatchLiveTaskBounding` and the bounded-fan-out classes stay green unchanged — this block changes **what** is dispatched, not **how** it is bounded.
8. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.
9. **The `mkdir` side effect is measured and stated** (`C9`): `_resolve_output_file` creates the output directory, so a skipped entry's directory is still created. Assert what happens and that it is harmless — the directory is shared by every entry in the batch.

**Out of scope.** A name-level mutex — **structurally impossible within a batch** (measured above). Cross-run name collisions, which need one and are a recorded residual. The second artefact's integrity when a stale entry is re-run (`NET-001`, phase 03). What the user is told about a video that was never written for any reason other than a duplicate (phase 08's boundary). Disambiguating names — foreclosed: the file name is unchanged. The `..` guard and warning suppression (`P12-B1`, `P12-B2`).

**Agent roster — Auditor, Planner, Validator.** *Reduced from all-agents.* Researcher is **dropped**: Decision A removes the best-practice question ("how should a downloader name colliding outputs") by fixing the answer, and what remains is an ordering-and-reporting design problem. Auditor **stays and is the most important reviewer here**, because three acceptance criteria rest on measurements not yet taken: the dispatch count, the no-transfer assertion, and the `mkdir` side effect. Planner stays because (a) versus (b) changes the batch's latency profile and its bounding, and last-wins needs a defined registry lifetime. Validator stays because "one dispatch" can pass while two transfers still happen.

---

### 3.9 `P12-B11` — the confinement posture for the artefacts that survive (`ART-007`, HIGH, shrunken)

**Goal.** Decide, once, what the product claims about artefact confinement on Windows — and record it where a reader will find it. **This block closes no exposure; it closes an unstated claim.**

**What the retirement already did to this finding.** The argfile row **leaves the table**: the `os.chmod` in `downloader._temp_argfile` dies with the transport, so measured chmod call sites drop from three to two. The row stays for the log file (`config.setup_logging`), the log parent directory, the working tree, the output directory, the segments, the merge temps, the concat lists, `.signature`, the final artefact, and the cookie file (`ytdlp_downloader._create_temp_cookie_file`, which the surviving yt-dlp transport still uses). Measured: `os.chmod` ×2 plus `Path.chmod` ×1 plus `Path.touch(mode=0o600)` ×1, and **three** `mkdir` sites with **no mode argument**. Every one of them requests `0o600` and measures `0o666`; every `mkdir` measures `0o777`. Zero compensating controls, zero runnable oracles.

**Semantic scope.**
- `src/vkdownloader/config.py::setup_logging` — the log-file creation branch, **only if** the chosen option changes what it does. It is otherwise read-only for this block.
- `docs/11-guides/configuration.md` and `docs/01-tools/vkdownloader-overview.md` — the two documents that already state the Windows caveat for other artefacts ("on Windows `os.chmod` only toggles the read-only attribute, so the owner-only guarantee is not offered there"). Whatever is decided must land in the same register, in the same words, so the log file is not described differently from the cookie file.
- `src/vkdownloader/config.py::setup_logging`'s in-code comment already states this finding's own conclusion: the mode is "requested for its POSIX effect only, and no access control list is applied". That sentence stays or is updated; it is not removed.

**Alternatives — `D-7`. This Planner does not pick.**
- **(a) Explicit DACL, per artefact.** Set a real ACL at creation. Mechanism: `ctypes`/`ctypes.wintypes` against `SetNamedSecurityInfo` (no new dependency), or `pywin32` (a new dependency, and `C1`/`C2` make that a packaging change in the same commit). Consequence: a Windows-only code path that **no oracle on any host can verify** — the finding's own verdict is "zero runnable oracles". The change would ship unverifiable.
- **(b) Confinement by directory inheritance.** Create the log's parent directory with a restrictive DACL and let the file inherit. Same mechanism, one target, and it constrains everything else the operator puts there — including the videos, which is almost certainly wrong for a download tool.
- **(c) State it plainly.** No code change. The claim becomes accurate: on Windows these artefacts are not confined, on POSIX the `0o600` request is honoured, and the documentation says exactly that — which is already the shape of the existing caveat for the cookie file and the argfile.
- **(d) Reframe the request.** Stop requesting `0o600` where the platform will not honour it, and document the platform matrix instead. Removes a request that does not do what it appears to do; leaves the artefact exactly as exposed.
- **Criterion:** project rule 5 (avoid overengineering) against rule 14 (keep documentation updated), plus one hard constraint — **`P11`'s reaper deliberately rules out a top-level `%TEMP%` glob and any age heuristic, so no block of this plan may introduce either.** That removes the "sweep it later" answer outright. Between (a) and (c): (a) requires a Windows-only code path with no runnable oracle on any host, which means the change cannot be verified — and rule 2 makes production code king over tests, so an unverifiable platform path is a liability, not a fix. **(c) or (d) is the defensible answer; this Planner states the criterion and does not pick between them.**

**Acceptance criteria.**
1. A reader of `docs/11-guides/configuration.md` can tell, without reading source, what confinement each artefact has on Windows and on POSIX, in one place, in the same register the cookie file and argfile already use.
2. Whatever the option, the `setup_logging` comment and the documentation **agree**. A divergence between them is the failure this block exists to prevent.
3. **No new dependency** is added unless option (a) with `pywin32` is chosen, in which case `pyproject.toml` **and** both `test_packaging.py` frozensets are edited in the same commit (`C1`, `C2`).
4. **No block introduces a sweep over the system temp directory and no age heuristic appears anywhere** — assert by grep over `src/` for `gettempdir`, `iterdir`, `rmtree` and any time-based expiry.
5. The three `D-11` mode oracles are **not touched** — they are `TST-013`'s (`DEF-1`), and the skip count stays at 3.
6. `P11-B3`'s log-file oracles and `P11-B6`'s structlog chain are unaffected: this block writes `setup_logging` **only** if the chosen option changes its behaviour, and in that case **only after `P11-B6` has landed** (§4.2).
7. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Out of scope.** The argfile row (deleted with the transport; §2.4.2). Any temp-directory reaper or sweep (`P11`'s). Moving a mode oracle off the platform guard (`TST-013`, phase 10 — `DEF-1`). The `ResourceWarning: unclosed file` from `setup_logging`'s `logging.basicConfig` FileHandler: it is a real leak inside this finding's own subject and it is **recorded here as an observation**, but fixing it means changing the logging configuration's handler lifetime, which is `P11-B6`'s territory.

**Agent roster — Auditor, Researcher, Planner, Validator.** *High risk, all agents.* Auditor: what confinement mechanisms are actually available to this process on Windows without a new dependency is an investigation, not a guess, and the answer decides whether (a) is even on the table. Researcher: the Windows ACL story through `ctypes` versus a platform dependency, and what current tooling does by default, is a best-practice question with support implications. Planner: (c) and (d) differ in whether the code keeps making a request it cannot honour — that is a product-claim decision. Validator: the block's entire output is a claim about behaviour; an independent reader must be able to confirm the claim matches the code.

---

### 3.10 `P12-B4` — say what the length bound bounds (`ART-011`, MEDIUM)

**Goal.** The `[:100]` bound either bounds what it claims to bound, or the claim changes. **The bound itself is pinned by a test and is not up for silent change.**

**Semantic scope.** `utils/security.py::sanitize_title` — the length truncation and the docstring sentence "limits length to 100 characters". If the option moves the bound, also `utils/security.py::_resolve_output_file` (which composes `{safe_title}_{video.id}.mp4`) and its docstring, and `tests/test_security.py::TestSanitizeTitle` plus `TestResolveOutputFile`.

**Alternatives — `D-2`. This Planner does not pick.**
- **(a) Record the bound as a title bound.** No code change. The docstring says the *title component* is limited to 100 characters and says plainly that the resulting path is not length-bounded.
- **(b) Bound the composed path.** Apply the limit to the composed output path rather than to the component. Directly addresses the failure class — a path that exceeds what the platform accepts. Cost: the effective title budget becomes path-length-dependent, so the same title produces a different name at different depths; `TestResolveOutputFile`'s name assertions must be re-expressed against a depth-independent budget; and the pinned component assertion must be re-scoped.
- **Criterion:** does the product intend a path-length guarantee? Measured: a 777-character path is **accepted** on this host, so the artifact's UNVERIFIED `WinError 206` failure was not reproduced. A host property the product cannot control (the effective limit is 260 for many APIs regardless of what `os` reports) is a poor thing to guarantee in code. That argues for (a). Choose (b) only if there is evidence of a real long-path failure in the field — the artifact has none, and re-measurement found none.

**Acceptance criteria.**
1. `sanitize_title`'s docstring and, if the bound moves, the module's behaviour agree about **what** is limited. One of them changes; they cannot both stay as they are.
2. `TestSanitizeTitle::test_limits_length_to_100_characters` stays green **unchanged** under option (a). Under option (b) it is re-scoped, and the re-scope is **declared in the commit body** with the reason.
3. If option (b): an oracle asserts the composed path stays within the declared budget at a deep directory, and `TestResolveOutputFile`'s exact-name assertions are updated consistently.
4. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Out of scope.** The `C7` assertion that a long path is *accepted* — that is a platform measurement, not a defect to fix here. `P12-B3`'s control characters (the character set changes what a title can contain, not how long it is).

**Agent roster — Planner, Researcher, Validator.** *High risk* by the roster rule because a pinned assertion and a documented contract are both in play. Planner: the decision is a product-claim question and the test-pinning consequence differs per option. Researcher: what path-length guarantee is actually available on the supported platforms is a current-practice question, and the answer is what decides (a) versus (b). Validator: one pinned assertion and one exact-string set separate the two options; an error there is a silent contract change. No Auditor — one function, one bound, fully located.

---

### 3.11 `P12-B5` — device names and trailing dots (`ART-014`, LOW)

**Goal.** The filesystem-facing title becomes a name Windows will actually accept.

**Semantic scope.** `utils/security.py::sanitize_title` — the normalisation chain. Both call sites are affected: `security._resolve_output_file` (filesystem) and `downloader`'s title callback (`sanitize_title(video.title)`), which is a **display** string. If the chosen option broadens the function, the display caller's output changes too and that must be a deliberate choice, not a side effect. `tests/test_security.py::TestSanitizeTitle`.

**Alternatives — `D-3`. This Planner does not pick.**
- **(a) Rename the utility** and stop treating the function as a sanitiser. `sanitize_filename_component` (or similar), with the docstring saying what it does and does not do, and the two call sites renamed. Keeps display output untouched, makes the contract honest, and closes the finding by removing the false claim rather than by adding more behaviour. Cost: a public-ish rename — the symbol is re-exported from `vkdownloader.utils`, so `utils/__init__.py` and its `__all__` change.
- **(b) Make it a real sanitiser.** Strip or prefix reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, with or without an extension) and trailing dots and spaces. Fixes the class for good, including titles sanitised into a collision by `P12-B3`'s replacements. Cost: the display caller starts showing `_`-prefixed device names and stripped dots — a visible console change for a cosmetic path.
- **(c) Leave it.** Recorded as a Windows-only creation hazard with a measured table.
- **Criterion:** is a second, non-appending caller foreseeable? Today the derived name always appends `_{id}.mp4`, which is the scope bound that keeps this LOW. If `sanitize_title` keeps being called for names that get no suffix, (b) is the only durable answer. **Prefer (a) if the suffix invariant is real** — it removes the misleading name without changing any output. Choose (b) only with an explicit acceptance that the display string changes.

**Acceptance criteria.**
1. The reserved-device-name and trailing-dot behaviour is **stated** — in the docstring at minimum, and in the documentation if the claim is user-visible. Measured table to record: `CON`, `CON.txt`, `NUL` write without exception and leave no file; `AUX.txt` raises `FileNotFoundError [Errno 2]`; a trailing-dot name is accepted by creation.
2. Under option (a): the rename is consistent across `utils/security.py`, `utils/__init__.py`'s `__all__`, both call sites and the tests. Under option (b): an oracle covers at least one bare device name, one device name **with** an extension, and one trailing dot — and asserts the display caller's new output is intended.
3. No fix here is POSIX-shaped: reserved names are ordinary files on POSIX, so any oracle must be either Windows-gated (and then counted against the **3-skip** budget, which is why a structural assertion is preferred) or written to assert the *normalisation* rather than the platform's refusal.
4. `TestSanitizeTitle`'s six existing tests stay green unchanged.
5. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; **skips unchanged at 3** — this is the block most likely to be tempted into a platform-gated test, and that would consume the budget `ART-007`'s oracles need.

**Out of scope.** The creation half as a defect on POSIX. `P12-B11`'s confinement posture. `P12-B3`'s control characters — though note the interaction: if (b) is chosen, one normalisation chain handles both, and the two blocks should be sequenced so the chain is written once (`P12-B3` first).

**Agent roster — Auditor, Planner, Validator.** *High risk* by the roster rule because a public-ish rename and a display-string change are both on the table. Auditor: whether the `_{id}.mp4` suffix invariant is real — i.e. whether every filesystem-facing call site appends a suffix — is an investigation across call sites, and the whole severity rests on it. Planner: (a) versus (b) is a contract decision with two different output surfaces. Validator: LOW severity does not mean low blast radius when a rename touches a re-exported symbol's `__all__`. No Researcher — the Windows reserved-name set is a platform fact, not a best-practice question.

---

### 3.12 `P12-B12` — the structural map must not mislead a reader into deleting the subprocess infrastructure (`docs/STRUCT.md`)

**Goal.** One sentence in the structural map describes what `services/ffmpeg_utils.py` actually is.

**Semantic scope.** `docs/STRUCT.md` — the `services/` tree listing's entry for `ffmpeg_utils.py`, which currently reads "FFmpeg discovery and stream concatenation".

**Why this block exists, re-checked against the module as it now stands.** The entry reads "FFmpeg discovery and stream concatenation". Measured at `58bb7ce`, the module holds **three** kinds of thing and the sentence names one:
- **shared subprocess infrastructure** (`iter_process_lines`, `cancel_subprocess` + alias) — imported and used directly by `ytdlp_downloader` for the loader child's stdout draining and cancellation, and **omitted from the sentence entirely**;
- **availability discovery** (`check_ffmpeg_available` and its cache) — **load-bearing again under Decision C**: `perform_download` calls it as the startup probe that warns before a long download fails at the merge step, and it is in the facade's `__all__`;
- **the segment merge engine** (`_merge_batch_segments`, `_perform_final_merge`, `_merge_segments_batched`, `_build_ffmpeg_concat_command`, `_required_merge_bytes`, `_check_merge_space`, `_await_ffmpeg_with_timeout`, `_MERGE_SPACE_MARGIN_BYTES`) — permanent.

**A reader acting on the current sentence deletes the infrastructure and takes the loader's stdout draining with it**, and may also read "discovery" as the disposable part — which under Decision C is the one protecting the merge. The measurement is in §2.4.4; the imports are direct and unconditional.

**Constraint on the wording.** It describes what the module *is* — subprocess infrastructure, availability discovery, and the segment merge engine. It does **not** describe the ffmpeg loader transport, which is deleted, and this plan does not document it.

**Acceptance criteria.**
1. The description names all three surviving kinds. A reader who deletes what the sentence names must not take `iter_process_lines` or `cancel_subprocess` with it, and must not take `check_ffmpeg_available`.
2. The sentence does not name the ffmpeg loader transport.
3. No other file changes. `C1` does not apply — no file is added, so both `test_packaging.py` frozensets stay at 73 and 32.
4. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged; skip count 3 — the edit is inert to every gate, which is why they run anyway.

**Out of scope.** The eight-file `--method ffmpeg` documentation surface — `P10-B10`'s obligation (§2.4.4). `docs/STRUCT.md`'s other entries, its layering section, or its absence of frontmatter. Any **code** change to `ffmpeg_utils.py` — Decision C makes it permanent surface and the merge engine untouchable by this plan except for `P12-B8`'s sizing arithmetic. The ffmpeg binary version constraint (`DEP-011`).

**Agent roster — Auditor, Planner.** Auditor: the justification is an import-graph fact, and the block must confirm it at execution time rather than inherit it from this plan. Planner: the wording has to survive the retirement as well as precede it, which is a two-state description. **No Researcher and no Validator** — the diff is one line in one file, the fact is verified, and a Validator review would exceed the risk. This is the only block in the plan without a Validator, and the reason is recorded rather than defaulted.

---

## 4. Dependency graph, linearised order, and the conflict matrix

### 4.1 The graph

```
        ┌───────────────────────── security.py track (one writer at a time) ─────────────────────────┐
        │                                                                                            │
        │   P12-B3 ──► P12-B4 ──► P12-B5                                                            │
        │  (sanitise)  (length)  (device)                                                            │
        │                                                                                            │
        │   P12-B1 ──► P12-B2                                                                        │
        │  (traversal) (warn)                                                                         │
        │                                                                                            │
        └───────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                    │
                          (P12-B10 reads _resolve_output_file as its key; writes cli.py,
                           downloader.py, batch_downloader.py — see note below)
                                                    │
                                                    ▼
                                             P12-B10
                                                    │
        ┌───────────────────── segment / merge track (one writer at a time) ─────────────────────────┐
        │                                                                                            │
        │   P12-B6 ──► P12-B7 ──► P12-B8                                                            │
        │  (sweeps)   (lifetime) (space)                                                             │
        └────────────────────────┬────────────────────────────────────────────────┘
                                 │
   P12-B3 ────────────────────────┤
   (ROLLOUT-1: ART-001 must be    │
    fixed before it is reachable)  │
                                 ▼
                              P12-B9 ◄── the keystone. Lands last among the six it promotes.

        P12-B10 ──► P12-B2      P12-B11 (after P11-B6)          P12-B12 (docs, independent)
        (the dedup pre-pass is the
         loader path's single place to
         let the warning fire)
```

**Two edges changed under the rulings, and one disappeared.**

- **`B10 → B2` is new.** Decision A puts the dedup pre-pass on the loader path, resolving an output file for **every** entry. Decision B makes the warning that `_resolve_output_file` currently suppresses the guard's entire user-facing behaviour. Together they mean the pre-pass is the natural single place for the warning to fire — so `B2`'s suppression half is best done **after** `B10` has established the pre-pass, rather than at a call site `B10` is about to restructure. **`B10 → B2`, and `B10` drops its conditional edge onto the `security.py` track** (it no longer writes `_resolve_output_file`, only reads it).
- **`B5 → B10` is gone.** Under Decision A `B10` does not disambiguate names, so it does not write `_resolve_output_file`. It only *reads* that function for the key. The earlier conditional edge existed because route (b) would have modified it.
- **`B1 → B2` survives but for a narrower reason.** `B2` no longer decides the guard's scope — Decision B did that. It now settles the guard's **reach** (does the warning fire) and `B1` settles what it **refuses**; both are in one function, so they stay one-writer.

**Edge justifications — every edge, and what breaks without it.**

| Edge | Type | Why it exists |
|---|---|---|
| `B3 → B4` | serialisation | Both write `sanitize_title`. `B3` changes what the function removes (control characters → `_`); `B4` bounds the function's **output string**. Applying the bound to a pre-`B3` string means re-deriving it against a different input alphabet. |
| `B4 → B5` | serialisation | Both write `sanitize_title`. `B5` route (a) renames the function and its docstring — the same docstring `B4` rewrites under route (a). Renaming and re-contracting one function in one commit is one decision wearing two hats. |
| `B1 → B2` | serialisation | Both write `validate_output_path`. `B1` settles what the guard **refuses** (component-wise); `B2` settles whether the warning **reaches** the user and against which root. Two writers to one function regardless of scope. |
| `B3 → B9` | **`ROLLOUT-1`** | Fixing the probe (`B9`) makes the segment path **default-reachable**. `ART-001`'s name half must already be fixed, or `B9`'s landing promotes a CRITICAL control-character defect from "opt-in / re-run only" to default. |
| `B6 → B7` | serialisation + mechanism | `B6` adds the non-regular-entry guard to `_cleanup_segments`. `B7` adds **new call sites** to that same function. Without the guard first, `B7`'s new sites multiply the exposure `ART-003` describes. Also `B6` settles what the sweeps match before `B7` decides when the tree exists — the tree cannot be removed before its contents are reconciled. |
| `B7 → B8` | serialisation | Both write `segment_downloader.py`. `B8`'s download-stage probe must be placed relative to the restructured session and lifetime `B7` establishes, or the probe runs on a tree that `B7` may have just removed. |
| `B8 → B9` | **`ROLLOUT-1`** | Same constraint as `B3 → B9`. `ART-012` becomes default-reachable when the probe starts firing — and under Decision C that matters more, since the merge is now the only merge. |
| `B6 → B9`, `B7 → B9` | **`ROLLOUT-1`** | Same constraint for `ART-003`, `ART-004`, `ART-005`, `ART-013`. |
| `B10 → B2` | **new under Decision A + B** | `B10` establishes the dedup pre-pass on the loader path; `B2` makes the warning fire. Doing `B2` first means changing suppression at call sites `B10` is about to restructure. **This edge is the only one that pairs the two rulings**, and it is why they are sequenced rather than run in parallel. |
| `P11-B6 → B11` | **cross-plan** | Both write `config.py::setup_logging`. See §4.2. |

### 4.2 The linearised order, with the reason for each position

**Total order.** `B3 → B1 → B10 → B2 → B4 → B5 → B6 → B7 → B8 → B9`, with `B11` after `P11-B6` and `B12` free at any point.

| # | Block | Position reason |
|---|---|---|
| 1 | **`P12-B3`** | The only CRITICAL, and it has no open decision. It goes first because it is also the deepest node in the `ROLLOUT-1` constraint: three later blocks are ordered by it. Starting with a decision-gated block would put the CRITICAL behind a product question. |
| 2 | **`P12-B1`** | The unambiguous half of the traversal finding. It precedes `B2` because both write `validate_output_path`, and it is ahead of `B4`/`B5` only because it is the shortest block in the plan and shares nothing with them. |
| 3 | **`P12-B10`** | **Moved here by Decision A.** It has no open decision any more, it writes none of `utils/security.py`, and it is now independent of every other block in the plan — except `B2`. Placed early because `B10 → B2` is the one new edge, and because a two-phase pre-pass is the largest structural change in the plan and should be landed before the segment track starts. |
| 4 | **`P12-B2`** | **Moved here by Decision B + the new edge.** It no longer decides a scope; it fixes the `repo_root` derivation and makes the warning fire. Doing it after `B10` means the suppression change lands on a call site the pre-pass already established, rather than one `B10` is about to restructure. |
| 5 | **`P12-B4`** | `D-2` resolved — option (a) chosen and committed (`aabfc46`): docstring-only clarification that the `[:100]` bound limits the title component, not the composed path. Queued after the guard pair because it shares `utils/security.py` with them and nothing else. |
| 6 | **`P12-B5`** | `D-3` resolved — option (a) chosen and committed (`6bd3188`): rename `sanitize_title` → `sanitize_filename_component` across `security.py`, `downloader.py`, and both test files; docstring states the function does NOT handle reserved Windows device names or trailing dots. No behavior change. Last on the `security.py` track because it renames the function `B4` re-contracted. |
| 7 | **`P12-B6`** | First segment block. Carries the guard that `B7`'s new call sites depend on, and settles the sweep semantics before the lifetime change alters when the tree exists. |
| 8 | **`P12-B7`** | Second segment block. Owns the shared insertion point for `ART-005` and `ART-013`'s lifetime half, and it can only be placed after `B6`'s guard exists. |
| 9 | **`P12-B8`** | Third segment block. Its new probe must be placed relative to the session shape `B7` leaves behind. **Under Decision C this is the highest-value block in the segment track** — the merge is the only merge and is permanent, so an insufficient free-space estimate is a standing defect on the product's single merge path (§2.4.5). It stays behind `B6`/`B7` because it writes the same file. |
| 10 | **`P12-B9`** | **Last.** `ROLLOUT-1`: fixing the probe promotes `ART-001`, `ART-003`, `ART-004`, `ART-005`, `ART-012` and `ART-013` to default reachability. Every one of those fixes must be landed and re-triased as default-reachable **before** this block. **Decision A did not change this** — dedup reduces how many items reach the path, not whether it is reachable (§2.4.6) — so `B10` is not gated on `B9` and `B9` is not gated on `B10`. |
| — | **`P12-B11`** | **After `P11-B6`.** See below. Independent of every block in this plan. |
| — | **`P12-B12`** | Free. It depends on an import-graph fact that is already established. Put it wherever the documentation pass falls. |

**Why `B9` is not batched with the blocks it promotes.** `ROLLOUT-1` is not a code dependency — `B9` compiles and passes with any of the six unfixed. It is a **rollout** constraint: `B9` changes which defects a default user can hit. Serialising it last converts "six findings fixed" into "six findings fixed and then promoted to default in one release", which is a reviewable statement. Batching them makes the promotion invisible to anyone reviewing the individual commits.

**Why `B10` is unordered with respect to `B9`.** Decision A removes a duplicate's `.part`, so within a batch the "two entries sharing one `.part`" half of `ART-002`'s exposure disappears. It does not touch the half that matters — the probe and the `DF-008` cleanup naming the wrong file — because a **non-duplicate** item still writes a `.part`. So `B9`'s scope and its two routes are unchanged, and neither block must wait for the other.

**Why `B11` is not simply last.** It is independent of this plan's code, but it shares `config.py::setup_logging` with plan 11, and plan 11's order puts its `B6` (which touches `setup_logging`) before its `B3` (which writes the log-file oracles). `P11`'s sequence is `P11-B1 → P11-B2 → P11-B4 → P11-B5 → P11-B6 → P11-B3`. So:

- **`P11-B6` must land before `P12-B11`** if `B11`'s chosen option changes `setup_logging`'s behaviour. Two writers to one function, and plan 11's `B6` is earlier in its own sequence.
- `P12-B11` writes **no oracle** in `tests/test_config.py`. Recommendation part (2) is `TST-013`'s (`DEF-1`), so `B11` never writes the log-file mode oracles — which is why it does not collide with `P11-B3`, and why the skip count stays at 3 for both plans.
- The residual `ResourceWarning: unclosed file` from `setup_logging`'s `logging.basicConfig` FileHandler sits inside both plans' subject matter and is recorded in `B11` as an observation **only**. Whoever changes the handler lifetime must reconcile both plans.
- If `B11` resolves to option (c) or (d) — state it in documentation, change no behaviour — then it writes no code at all and the `P11-B6` dependency disappears entirely. **That is the preferred outcome and the reason the criterion in §3.9 is stated as it is.**

### 4.3 Conflict matrix over shared semantic anchors

Each row is a **semantic anchor** two blocks both write. "Code" means a module or function body; "Test" means a test class.

| # | Shared anchor | Blocks in conflict | Serialised? | Rule |
|---|---|---|---|---|
| 1 | `utils/security.py::sanitize_title` | `B3`, `B4`, `B5` | **Yes** — one writer | `B3 → B4 → B5`. Never two blocks in one commit. |
| 2 | `utils/security.py::validate_output_path` | `B1`, `B2` | **Yes** | `B1 → B2`. |
| 3 | `utils/security.py::_resolve_output_file` | `B5` (route b, **narrowing the function's output**), and `B10` (**reads it for the dedup key**), and `B2` (**its `warning` argument only**) | **Yes for code; read-only for `B10`** | `B5` first, then `B10`/`B2`. `B10` must not modify it — Decision A disambiguates nothing. If `B5` route (b) is chosen, `B10`'s dedup key changes with it, so `B5 → B10` on that route only. |
| 4 | `tests/test_security.py::TestSanitizeTitle` | `B3`, `B4`, `B5` | **Yes** | Follows row 1. |
| 5 | `tests/test_security.py::TestValidateOutputPath`, `::TestValidateOutputPathTraversal` | `B1`, `B2` | **Yes** | Follows row 2. |
| 6 | `services/segment_downloader.py` | `B6`, `B7`, `B8` | **Yes** | `B6 → B7 → B8`. |
| 7 | `services/segment_downloader.py::_cleanup_segments` | `B6` (guard), `B7` (new call sites) | **Yes — and mechanism** | Guard first, call sites second. This is the edge that fails hardest if inverted. |
| 8 | `services/segment_downloader.py::_clear_stale_segments` | `B6` (sweep widening), `B7` (lifetime) | **Yes** | `B6` decides what the sweep matches; `B7` decides when the tree exists. If both change the signature short-circuit without saying so, the two changes interleave unreviewably. **Exactly one block may change the short-circuit; that block is `B6`.** |
| 9 | `services/segment_downloader.py::_tally_and_merge`'s `*.ts` count | `B6` only | n/a | Sole owner. `B7` must not touch it. |
| 10 | `tests/test_segment_downloader.py::TestPreserveSegmentsReporter` | `B6` (only if `D-4` → ii), `B7` | **Yes** | `B6` first. `B7` must leave all three tests green **unchanged**. |
| 11 | `tests/test_segment_downloader.py` (non-reporter classes) | `B7`, `B8` | **Yes** | `B7` first. |
| 12 | `services/ffmpeg_utils.py::_required_merge_bytes` | `B8` only | n/a | Sole owner. The module is a leaf (`C4`): the edit is arithmetic and docstring, and must not import the segment layer. |
| 13 | `services/ffmpeg_utils.py::_merge_segments_batched`'s deferral comment | `B6` (ART-004 discharged), `B8` (ART-012 discharged) | **Yes** | `B6` first. **One block may rewrite that comment block at a time** — it is a single comment carrying two deferrals, and two independent rewrites will overwrite each other. |
| 14 | `tests/test_ffmpeg_utils.py::TestMergeFreeSpaceProbe` | `B8` only | n/a | Sole owner, with the declared three-assertion change. |
| 15 | `services/ytdlp_downloader.py` | `B9` only (in this plan) | n/a | Also written by `P10-B10`'s fallback-arm deletion — serialise with plan 10. |
| 16 | `tests/test_hls_downloader.py::TestYtdlpCliCommand` | `B9` only | n/a | The `--no-part`-absent assertion is `B9`'s to edit under route (b) only, declared in the commit body. |
| 17 | `tests/test_hls_downloader.py::TestCleanupSegments` | `B6` only | n/a | Sole owner. **Extend the existing class; do not create a second one.** |
| 18 | `src/vkdownloader/cli.py` — the `batch` URL reader and its `skipped_count` accounting | `B10` only | n/a | Sole owner in this plan. Decision A gives the dedup skip a **second** summary line here rather than folding it into the invalid-URL count. |
| 18b | **`services/downloader.py::download_video`** (the extract → resolve → dispatch pipeline) | `B10` only | n/a | Sole owner. `P10-B10` already landed; nothing else in this plan writes it beyond the facade re-export caveat (`C3`). |
| 18c | **`services/batch_downloader.py`** — the fan-out and `_print_batch_summary` | `B10` only | n/a | Sole owner. It threads `output_index` and owns the reporting the dedup skip must reach. |
| 19 | `src/vkdownloader/config.py::setup_logging` | `B11`, and `P11-B6` / `P11-B3` | **Cross-plan** | `P11-B6` → `B11` (if `B11` changes behaviour) → `P11-B3` writes the oracles. `B11` writes **no** oracle, so row 19's oracle column never collides. |
| 20 | `tests/test_config.py` — the two `D-11` mode oracles | nobody in this plan | n/a | `TST-013`'s (`DEF-1`). **Forbidden**: no block may touch them or change the skip count. |
| 20b | **`tests/test_cli.py::TestBatchCommand`** — the reader's accounting and the new dedup summary line | `B10` only | n/a | Sole owner. No existing test asserts anything about duplicates (§2.5), so the whole oracle set is new here. |
| 21 | `docs/STRUCT.md` | `B12` only | n/a | Sole owner. |
| 22 | `tests/test_packaging.py` frozensets | any block adding a file | **Per-commit** | `C1`: 73 / 32, edited in the same commit. `B12` adds no file; `B11` option (a) with `pywin32` does. |
| 23 | `services/downloader.py`'s title callback | `B5` (route a: rename affects the call site) | Cross-module | The call site only. **Never a re-export line** (`C3`). |
| 24 | System temp directory / any age heuristic | `B11` explicitly forbidden | n/a | `P11`'s reaper rules both out. Assert by grep in `B11`'s acceptance criteria. |

**Anchor none of the blocks share but that all must respect:** `B3`, `B4`, `B5` change the title string that `_resolve_output_file` keys on, and **`B10` keys on that function's output**. So `B10`'s dedup key must be computed against the **post-`B3`/`B4`/`B5`** normalisation, not against today's — a title containing a control character, a device name, or a character past position 100 can collide only *after* those blocks land. This is a **read** dependency, not a write conflict, which is why it is not an edge in §4.1: `B10` is correct at any point in the order, but its oracle for the sanitised-title-collision direction is only meaningful once those blocks have landed.

---

## 5. Risks

### 5.1 Implementation risk

| ID | Risk | Severity | Block | Mitigation |
|---|---|---|---|---|
| `I1` | **A POSIX-shaped fix lands.** `P12-B6`'s guard is the live trap: `IsADirectoryError` is the natural thing to catch and it **is not raised on Windows** — `PermissionError [WinError 5]` is. A guard written against the POSIX exception leaves the defect exactly where it is on the platform that ships. | High | `B6` | Acceptance criterion 1 requires the guard to be phrased by intent and asserts **no** POSIX exception type. |
| `I2` | **A stale anchor is implemented against.** The artifact's `R9` self-assessment claims "106 anchors, 106 exact"; every `segment_downloader.py` anchor drifted, and three `ffmpeg_utils.py` sites no longer exist. | High | all | §2.6. No block inherits an anchor. Anchors are symbol names, re-derived at execution time. |
| `I3` | **Implementing against `_INVALID_FILENAME_CHARS`.** The artifact names it as a module constant. It has never existed. An Implementor who reads the finding rather than the code writes `utils.security._INVALID_FILENAME_CHARS` and either creates a new constant or fails to import. | High | `B3`, `B5` | §1.1.3 states the correction. `B3`'s alternatives name the constant explicitly as a *new* symbol whose name must describe behaviour. |
| `I4` | **The `ffmpeg_utils.py` leaf property is broken.** A merge change that imports the segment layer, a path helper or a URL sanitiser to get a constant "compiles fine" and passes every gate, because `C4` is a design property and `ignore_missing_imports = true` hides the symptom. | High | `B8` | `B8`'s scope is arithmetic and docstring only. Reviewers check the import block explicitly. |
| `I5` | **`os.replace` durability is assumed.** NTFS carried the source's mode to the destination and POSIX rename atomicity is not claimed. A fix that adds `fsync` on the strength of the atomicity comment is solving a problem no code in this repository has stated. | Medium | `B6`, `B7` | `C5`: no `fsync` exists. `B6`/`B7` must not assert durability. |
| `I6` | **The batch size becomes a shared constant and the peak calculation drifts.** `_merge_segments_batched` holds the batch size as a local literal. Promoting it to a module constant so `_required_merge_bytes` can read it is the natural fix, and it means the sizing silently depends on a staging parameter. | Medium | `B8` | The constant is named and its relationship to the sizing is documented at both sites. **Under Decision C this is the highest-consequence arithmetic in the plan** — see `R7`. |
| `I7` | **A `mkdir` collides with a file.** `FileExistsError [WinError 183]` at the output `mkdir` when the path exists as a file; `exist_ok=True` does not suppress it. | Low | `B10` | Decision B removed the refusal that needed a home here. It is now `B10`'s: `_resolve_output_file`'s `mkdir` runs for every resolved entry, including a skipped one (`C9`). |
| `I8` | **The download-stage probe's demand figure is a guess.** Before any byte arrives, "how much space will this download need" is an estimate. A probe built on a guess fails either silently (too generous) or uselessly (too strict). | Medium | `B8` | The alternatives are ranked by that asymmetry, and the argument for **not** putting the check inside the concurrency pump is written out (§3.6, criterion). |
| `I9` | **The dedup registry leaks or is scoped wrong.** Last-wins needs a registry whose lifetime is the batch. Scoped too wide it dedups across two commands; too narrow and it dedups nothing. | Medium | `B10` | Assert the single-URL command does not carry a registry, and that two entries in one batch do. |
| `I10` | **The pre-pass dispatches a skipped entry by accident.** Any path that reaches `perform_download` without consulting the registry bypasses the whole decision. | **High** | `B10` | The acceptance criterion is an explicit not-called assertion on the dispatch path, not an inference from the dispatch count. The registry is consulted at the single point every entry passes through. |

### 5.2 Rollout risk

| ID | Risk | Severity | Block | Mitigation |
|---|---|---|---|---|
| `R1` | **`ROLLOUT-1` lands inverted.** `B9` fixes the probe and promotes six findings — one of them CRITICAL — to default reachability in the same release. Every affected finding's own severity note says "opt-in", so the triage is wrong the moment the probe works. | **Highest in the plan** | `B9` | `B9` depends on `B3`, `B6`, `B7`, `B8` and is scheduled last. If inverted, the six must be **re-triaged as default-reachable before** `B9` lands, not after. **Decision A does not relieve this** — it reduces item count, not reachability (§2.4.6). |
| `R2` | **Batching hides the promotion.** Landing `B9` in the same batch as any of the six makes the promotion invisible to a reviewer reading individual commits. | High | `B9` | §3.7 acceptance criteria: if batched, the decision is written down, not inherited. |
| `R3` | **The loader deletion and this plan land in an unknown order.** Nothing here depends on `P10-B10` — it has already landed at `58bb7ce`. But `B11`'s confinement row list is stated relative to the current tree, and a future retirement of anything else could shift it again. | Low | `B11` | No block waits. Re-measure the anchors before each block if more than a few commits land in between. |
| `R4` | **`B3` changes what a title can contain, so every block that keys on the title string changes behaviour underneath itself.** `B10`'s dedup key, `B4`'s bound, `B5`'s device handling all read the title. | Medium | `B3`, `B4`, `B5`, `B10` | §4.3's closing note: `B10`'s sanitised-title-collision oracle is only meaningful once those blocks land. A read dependency, not an edge. |
| `R5` | **`B7` removes the working tree that the operator was told to clear manually.** The pinned reporter's `next_action` says "clear the working directory before re-running the download". If `B7` removes the tree, that instruction becomes stale guidance. | Medium | `B7` | Acceptance criterion 4: verify the reporter's contract still holds and the `next_action` is still truthful; declare the change in the commit body if the reporter's call had to move. |
| `R6` | **Two planners writing `config.py::setup_logging` concurrently.** | Medium | `B11` | §4.2: `P11-B6` → `P12-B11` (if it changes behaviour) → `P11-B3` writes the oracles. `B11` writes no oracle, so the skip count is safe for both. |
| `R7` | **The merge's free-space estimate stays insufficient on the product's only, permanent merge.** Under Decision C there is no second merge and no plan to remove this one, so the `2×`-against-`3×` gap is no longer a concern that a future change would absorb. | **High, and newly framed** | `B8` | `B8`'s multiplier fix is now a standing-defect fix, not a tuning change. `§2.4.5` raises it; the three declared assertion changes are the price. |
| `R8` | **The merge engine is read as removable.** A later reader — or a later plan — sees "ffmpeg" in the module name and a retirement nearby, and deletes it. | High | `B12`, all | `§2.4.4` states permanence; `§7.3` item 3 makes the import contract a gate; `B12`'s wording names all three kinds so the module reads as infrastructure, not as a leftover. |
| `R9` | **The dedup pre-pass changes the batch's latency profile**, and under alternative (b) every entry is extracted before any download starts. A long batch looks stalled to the operator. | Medium | `B10` | The (a)/(b) choice in §3.8 turns on this and is left open. Whichever is chosen, the progress display's behaviour during the resolution phase is part of that block's acceptance, not an afterthought. |
| `R10` | **A strict reading of Decision A's no-network clause is discovered to be unimplementable at execution time.** The resolved filename needs `title` and `id`, which arrive over the network. | Medium | `B10` | Measured and recorded as `DEF-6` (§3.8), surfaced to the Product Owner rather than reinterpreted. `B10` must not silently relax the clause to "no media transfer" without that record existing. |

### 5.3 Regression risk

| ID | Risk | Severity | Block | Mitigation |
|---|---|---|---|---|
| `G1` | **A fix strengthens a guard and rejects input the product needs.** Under Decision B this risk is **narrowed to `B1` alone**: `B2` no longer refuses anything, and `ART-009`'s re-scope makes "start refusing paths" an explicit non-outcome with its own acceptance criterion. `B1` is a strict narrowing of the false-positive set (a component containing `..` is not a traversal). | High | `B1` | `B2`'s acceptance criterion 6 asserts that acceptance behaviour is otherwise unchanged, precisely because the temptation under a "make the warning reliable" heading is to start refusing. |
| `G2` | **The pinned reporter's zero-count contract is broken.** `ART-005`'s already-fixed half exists because a `count > 0` gate emitted nothing in exactly the case that mattered. Any block that reintroduces a gate, or that stops the reporter from being called, regresses a landed fix. | High | `B6`, `B7` | `TestPreserveSegmentsReporter`'s three tests stay green **unchanged** in both. Acceptance criteria state this twice. |
| `G3` | **`B6`'s narrowed count makes the merge run when it should not.** Excluding `batch_*.ts` means a tree with a *missing* segment plus a leftover batch temp now reads as short — which is correct — but a tree whose temps happen to make the arithmetic work would merge the wrong input set. | High | `B6` | The merge's own existence check (`FileNotFoundError` naming the missing file) is the backstop and is untouched. Acceptance criterion 2 requires the oracle to prove the merge is **reached**, and `TestMergeSegmentsBatched`'s failure-preservation test must stay green unchanged. |
| `G4` | **`B7`'s new `_cleanup_segments` call sites raise where they did not before.** The guard (`B6`) handles directories; anything else in `glob("*")` is a new failure surface. | Medium | `B7` | Depends on `B6`. `B7` adds no call site until the guard is in. |
| `G5` | **`B8`'s download-stage probe blocks downloads that would have succeeded.** A probe with a wrong demand figure converts working downloads into failures — the failure mode `_check_merge_space`'s own docstring explicitly avoids for an unreadable mount. | Medium | `B8` | The probe must apply the same "an unreadable mount is not evidence of a full one" rule: a failed probe logs and proceeds. Acceptance criterion must not create a new hard-failure path for an unmeasurable volume. |
| `G6` | **`B9` changes what counts as "yt-dlp made progress",** so the retry loop's entry into the segment path changes. A `.part` of non-zero size from an interrupted transfer is progress; a zero-length one is not. | Medium | `B9` | Acceptance criterion 2 keeps existence **and** non-zero size load-bearing. |
| `G7` | **`B10`'s dedup drops an entry the operator wanted.** Last-wins means the *earlier* copy is discarded. If two entries were meant to produce two files, one is now silently absent. | Medium | `B10` | The skip is **visible** through `ProgressStatus.SKIPPED` and a distinct summary line, and it must name the discarded entry's resolved path — otherwise "which file did I lose?" is unanswerable. |
| `G8` | **A dedup'd batch reports a count the operator reads as success.** The existing summary prints counts per status; a skipped entry folded into the wrong bucket makes the arithmetic look fine. | Medium | `B10` | The dedup line is **distinct** from the invalid-URL line, and `B10` writes an oracle at both the per-item and the aggregate level. |

### 5.4 Compatibility risk

| ID | Risk | Severity | Block | Mitigation |
|---|---|---|---|---|
| `C1` | **`B5` route (a) renames a re-exported symbol.** `sanitize_title` is exported from `vkdownloader.utils` with an explicit `__all__`. A rename is a breaking change for any external importer. | Medium | `B5` | The rename is declared in the commit body; `utils/__init__.py`'s `__all__` is updated in the same commit; if a compatibility alias is wanted, that is a decision recorded, not assumed. |
| `C2` | **`B11` option (a) with `pywin32` adds a platform dependency** to a package that currently has none of that kind. | Medium | `B11` | `C1`/`C2`: `pyproject.toml` and both `test_packaging.py` frozensets edited in the same commit. The criterion in §3.9 argues against this option on verification grounds, not on taste. |
| `C3` | **`C5` — introducing a lock file or a temp-dir abstraction** where none exists. | Medium | `B6`, `B7` | Explicitly out of scope. **And for `B10` it is no longer even the right shape**: the within-batch mutex need is structurally eliminated by dedup-before-dispatch (§3.8), so no locking primitive is introduced for it at all. The cross-run residual is recorded, not solved. |
| `C4` | **`C7` — introducing a clobber policy or a temp sweep** where neither exists. Decision A forecloses the first without this plan adding one: **no suffix is added, because the file name is unchanged.** | Medium | `B10`, `B11` | `B11` acceptance criterion 4 asserts by grep that neither appears. `B10` introduces no clobber flag. |
| `C5` | **`C2` — importing a module without declaring it.** `ignore_missing_imports = true` means mypy will not catch it. | Low | all | Any block adding an import must add the declaration; `G4` is not sufficient on its own. |
| `C6` | **A block treats the merge engine as removable** because "ffmpeg" reads as a retired dependency. Decision C makes it permanent; the naming invites the mistake. | **High** | `B12`, all | `§2.4.4`; `§7.3` item 3 as a gate; `B12` rewrites the structural-map sentence so the module reads as infrastructure. |

### 5.5 Documentation risk

| ID | Risk | Severity | Block | Mitigation |
|---|---|---|---|---|
| `D1` | **A block lands and its in-code deferral comment stays.** `_merge_segments_batched`'s comment block assigns the merge-temp counting to `ART-004` and the sizing to `ART-012`; `_log_preserve_segments`'s comment says excluding the temps "is phase 07's `ART-004`; until then the count is stated as a working-directory count". | High | `B6`, `B8` | Acceptance criteria in both blocks require the comment to record that the deferral is discharged. A stale in-code pointer to a finished finding is how the next auditor re-files it. **Under Decision C the sizing half is now permanent-code commentary, not a retirement remnant** — it must be rewritten, not deleted. |
| `D2` | **`docs/STRUCT.md` misdescribes a module and a reader deletes live infrastructure.** Under Decision C there are now **three** things in that module a reader could delete by mistake, and one of them ("discovery") was misread as disposable for most of this plan's life. | High | `B12` | §3.12. The omission costs `iter_process_lines` and `cancel_subprocess` (the loader's stdout draining) and, if "discovery" is read as removable, `check_ffmpeg_available` (the probe that protects the merge). |
| `D3` | **`B11` documents a posture the code does not implement, or vice versa.** The block's entire output is a claim. | High | `B11` | Acceptance criterion 2: the comment and the documentation must agree. Divergence is the failure the block exists to prevent. |
| `D4` | **Documentation claims drift on the other side of the loader's deletion.** The eight-file `--method ffmpeg` surface is `P10-B10`'s obligation and has landed. **Decision C adds a new documentation obligation**: the merger is permanent product surface, and any doc that described it as part of the retired loader now understates it. | Medium | all | §2.4.4 records the boundary. No block in this plan touches those eight files. `B12` covers the structural map, which is the one structural claim this plan owns. |
| `D5` | **A block edits `docs/` without the maintenance rules being read.** | Low | `B11`, `B12` | §2.1 rule 7: read `docs/00-overview/doc-maintenance-rules.md` first. English only; frontmatter is contract for domain docs (`STRUCT.md` is a root structural map with none and is edited in place). |

### 5.6 Test-pinning risk

| ID | Pinned assertion | Block | Disposition |
|---|---|---|---|
| `T1` | `TestSanitizeTitle::test_limits_length_to_100_characters` — pins the `[:100]` bound | `B4` | **Stay green unchanged** under option (a). Under option (b), re-scoped and **declared**. |
| `T2` | `TestPreserveSegmentsReporter::test_count_includes_merge_temps_and_says_so` — asserts `working_dir_ts_count == 3` with `batch_00000.ts` present, and its own docstring names `ART-004` as deferred | `B6` | **Stay green unchanged** under `D-4` → (i). Under (ii), edited and **declared**. |
| `T3` | `TestPreserveSegmentsReporter::test_reports_zero_count_directory` — the already-fixed half of `ART-005` | `B6`, `B7` | **Stay green unchanged. Forbidden to break.** Reintroducing a count gate breaks it. |
| `T4` | `TestMergeFreeSpaceProbe` — **three** assertions pin the `2×` multiplier exactly | `B8` | **MUST change. Declared, not silent.** All three named in the commit body. The replacement must preserve the *direction* of the invariant each was protecting. |
| `T5` | `TestYtdlpCliCommand` — asserts `--no-part` is **absent**, docstring "lets yt-dlp use .part files" | `B9` | Green unchanged under route (a) or (c). **Edited and declared** under route (b). |
| `T6` | `TestMergeSegmentsBatched`'s "batch failure preserves inputs and earlier batch temps" — the D-13 preservation oracle, which is precisely the `ART-004` residue | `B6` | **Stay green unchanged. Must not be weakened.** |
| `T7` | The three `D-11` mode oracles (two in `test_config.py`, one in `test_hls_downloader.py::TestCreateTempCookieFile`) — the **3-skip** floor | `B11`, `B5` | **Untouched. `TST-013`'s (`DEF-1`).** Any change to the skip count in either direction is a failure. A fourth skip would have existed had the argfile's oracle survived; it did not, and reviving it is not this plan's job. |
| `T8` | `TestValidateOutputPathTraversal` — five tests, four using real `..` components | `B1`, `B2` | **Stay green unchanged.** A component-wise test keeps them green; that they stay green **for the right layer** is `B1`'s Validator criterion. `B2` must not add a refusal assertion here — that would contradict Decision B. |
| `T9` | `TestValidateOutputPath::test_path_inside_repo_warns` — **mocks `Path.resolve`** so `relative_to` always succeeds | `B2` | Cannot detect the `repo_root` mis-derivation. `B2` must add an oracle that does, and must not "fix" the test by removing the mock without saying so. |
| `T10` | `TestSegmentFanoutCompletion`, `TestSegmentFanoutBoundedProduction`, `TestConnectorCeilingsFollowTheSetting` — the bounded fan-out | `B7`, `B8` | **Stay green unchanged.** `B8` is explicitly steered away from putting a decision inside the pump for this reason. |
| `T11` | `test_packaging.py`'s `EXPECTED_SDIST_ENTRIES` (73) / `EXPECTED_WHEEL_ENTRIES` (32) / `BUILDER_ADDED_SDIST_ENTRIES` (2) / `EXPECTED_DIST_INFO_ENTRIES` (4) | any block adding a file | Edited in the same commit. Measured, not estimated. **All four unchanged at `58bb7ce`.** A new file under `src/vkdownloader/` moves **both** the sdist and the wheel sets. |
| `T12` | `TestBatchCommand`'s existing reader accounting | `B10` | **Extended, not rewritten.** The invalid-URL `skipped_count` path must stay green unchanged; the dedup skip gets its own line. Folding them together would make a valid duplicate look like malformed input. |
| `T13` | **`G3`'s red baseline** — the two `with patch(...)` wraps in `tests/test_hls_downloader.py` | any block touching that file | **Left alone.** Not this plan's defect, and reformatting it inside a filesystem commit would make the baseline delta unattributable. Restoring it is its own commit (§2.1 rule 3). |

### 5.7 The prohibitions that survive a fix

These outlive every block in this plan. They are not findings; they are the things that are still wrong when every block has landed.

1. **`ART-007`'s zero-compensating-control half is not closed.** `B11` decides and records a posture; on option (c) or (d) nothing is confined on Windows that was not confined before. Every artefact the product creates — log file, log parent, working tree, output directory, segments, merge temps, concat lists, `.signature`, the final artefact, the cookie file — is readable by any local user on Windows. The decision is recorded; the exposure is unchanged.
2. **`ART-007`'s zero-runnable-oracle half is not closed.** `DEF-1` is `TST-013`'s. No block here writes an oracle that runs on Windows for the mode.
3. **No durability across power loss.** `C5`: no `fsync` anywhere. The two `os.replace` publish sites are atomic with respect to concurrent readers on NTFS and that is the whole of the guarantee.
4. **No name-level mutual exclusion within a batch.** After Decision A, within-batch collision is **structurally impossible** (measured, §3.8), so no mutex exists and none is introduced. What survives: dedup is **per invocation**, so two concurrent runs into one output directory are two invocations and neither sees the other's names — and `_attempt_segment_resume`'s `output_file.unlink()` means one can still remove another's artefact across runs. **`C5` records that no lock file or lock primitive exists anywhere in `src/`.**
5. **`B10`'s success report is only correct for duplicates.** A skipped duplicate is reported; a video that was never written for any *other* reason is still reported by the reporting layer's existing contract, and what the user is told about it is phase 08's.
6. **`ART-001`'s mislabels are not fixed.** `OUT-016`, phase 08.
7. **The ffmpeg binary is still an unconstrained external dependency** — and now more load-bearing than before, because the merger is permanent and is the only merge. `DEP-011`, phase 11.
8. **Reserved device names are still ordinary files on POSIX**, and `ART-014`'s creation half is Windows-only. Option (a) in `B5` removes the false claim; it does not make the names portable.
9. **`mypy` still cannot enforce the no-`Any` rule.** `QLT-009`, phase 09.
10. **The 777-character path is still accepted.** Under Decision B this is now **decided behaviour** rather than a residual: the tool does not bound path length and does not refuse unusual paths. `B4` records the bound's true scope; it does not add a limit.
11. **The dedup pre-pass cannot avoid the extraction call** that computing the key requires. `DEF-6`, unresolved and escalated rather than reinterpreted.
12. **`G3` is red at baseline** and stays red until someone fixes it in its own commit (§2.1 rule 3).

---

## 6. Task specifications

One specification per block. Each names its semantic target, the mechanical verification, the points where honest judgement is required (never mechanically verifiable), the deliverable shape, and what blocks it. **No positional assumption is made anywhere** — every target is a symbol, a class, a config key or a doc entry.

A task specification is complete when the agent executing it can find every file it needs by symbol and needs nothing re-derived from the artifact.

---

### 6.1 `P12-B3` — control characters in `sanitize_title`

**Semantic target.** `src/vkdownloader/utils/security.py::sanitize_title`. Its docstring. Its inline character-removal loop and the `strip()` and truncation immediately around it. Test target: `tests/test_security.py::TestSanitizeTitle` (extend; do not create a second class).

**Do not touch.** `_resolve_output_file`'s derivation logic. The `[:100]` bound (`P12-B4`). Device names and trailing dots (`P12-B5`). Any `except` clause in `_attempt_segment_resume`.

**Mechanical verification.** A table-driven oracle in `TestSanitizeTitle` covering every code point in `chr(0)`–`chr(31)` and `chr(127)`, asserting none survives. The six existing tests in the class run unchanged. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged; skip count 3.

**Honest judgement required.** Whether `\x80`–`\x9f` are in scope. Argument: `sanitize_title` is a *filesystem* sanitiser, those are not illegal on Windows, and adding them changes display output for no filesystem reason. `\x00` must be *replaced* rather than stripped, because Python rejects it before the syscall — a strip that leaves it would raise `ValueError` instead of sanitising. And the display caller (`downloader`'s title callback) now renders a newline-free string where it previously rendered a newline: that is an improvement, but it is a **visible** change and belongs in the commit body.

**Deliverable.** One commit. The commit body names the control range, states that the nine illegal characters were already handled, and names the display consequence. If the constant is introduced (`§3.1` alternative (b)), its name describes the *behaviour*, not "invalid filename characters" — the artifact's `_INVALID_FILENAME_CHARS` never existed and that name would reintroduce the error.

**Blocked by.** Nothing. **Blocks:** `B4`, `B5`, `B9`.

---

### 6.2 `P12-B1` — component-wise traversal detection

**Semantic target.** Both `".." in str(path)` layers inside `utils/security.py::validate_output_path`. Test targets: `tests/test_security.py::TestValidateOutputPathTraversal` and `::TestValidateOutputPath` (extend).

**Do not touch.** `repo_root`, the containment comparison, or the `warning` parameter's plumbing — those are `P12-B2`.

**Mechanical verification.** (i) A component containing `..` but not equal to it is accepted — measured live as rejected today. (ii) All five `TestValidateOutputPathTraversal` tests and all three traversal tests in `TestValidateOutputPath` pass **unchanged**. (iii) A new oracle reaches the **post**-resolution layer specifically; `test_validate_output_path_rejects_traversal_even_if_resolved` does not count, because its own comment concedes `resolve()` yields no `..`, so it exercises the pre-resolution layer twice. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Honest judgement required.** Whether to extract a shared predicate (§3.2 alternative (b)) or write the test twice (§3.2 alternative (a)). Criterion recorded in §3.2: prefer the smallest change that is unambiguously correct. `TestValidateOutputPathEdgeCases::test_empty_path_resolves_to_cwd` must keep passing — `Path(".")` must still resolve to the cwd, which a naive `".." in parts` on an unresolved `Path(".")` could disturb.

**Deliverable.** One commit. No test in the existing traversal classes is edited.

**Blocked by.** Nothing. **Blocks:** `B2`.

---

### 6.3 `P12-B2` — the warning reaches the user (`ART-009`) — Decision B

**Decision B is closed. `D-1` is closed.** Warn only; no refusal, no root concept, no write-blocking check. **`C:\Windows\System32` and `/etc` → `C:\etc` being accepted is correct behaviour, not a gap.**

**Semantic target.** `src/vkdownloader/utils/security.py::validate_output_path` — the module-level `repo_root` expression only, and the `warning` flag's plumbing. The three call sites, **for the `warning` argument only**: `security._resolve_output_file`, `ytdlp_downloader`'s probe call, `segment_downloader.download_hls_with_resume`'s call. Test targets: `tests/test_security.py::TestValidateOutputPath` and `::TestValidateOutputPathEdgeCases`.

**Do not touch.** The `..` detection (`P12-B1`). Anything that would make a path unacceptable. What `_resolve_output_file` composes.

**Mechanical verification.** (i) `repo_root` derives to the directory that contains `src/`, asserted **by value** — the last commit on this file is `e59523c` and it is unchanged, so the expression is exactly `parent.parent.parent` and one level too deep. (ii) A **new** oracle detects it: a path under the repository root but **outside** `src/` warns, and a path under `src/` still warns. Today the first does not warn. (iii) `test_path_inside_repo_warns` either loses its `Path.resolve` mock or gains a real-derivation companion — **declared in the commit body if the mock goes.** (iv) `TestValidateOutputPathEdgeCases`' three tests pass unchanged. (v) `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged; skip count 3.

**Honest judgement required.** Only one thing, and it is small: whether the remaining `warning=False` suppression survives at the internal call sites (§3.3's (a) versus (b)). Under Decision B the warning is the guard's entire user-facing behaviour, so silencing it at two of three sites means the default loader path is silent. But a developer running the tool from a clone may find a warning on every download noisy. **This Planner does not pick**; the criterion is whether the warning's purpose is "you are writing into the source tree" or "you are writing into the tool's own installation".

**The judgement that is NOT open:** whether to add a refusal, a root, or a write-blocking check. Foreclosed. Acceptance criterion 6 asserts acceptance behaviour is otherwise unchanged, because the failure mode here is a "reliable warning" that quietly becomes a restriction and passes every existing test.

**Deliverable.** One commit. The commit body records the suppression outcome and, if the mock was removed, that too.

**Blocked by.** `B1`, and **`B10`** (the new edge — the pre-pass is the right place to let the warning fire). **Blocks:** nothing.

---

### 6.4 `P12-B4` — the length bound's true scope

**Semantic target.** `src/vkdownloader/utils/security.py::sanitize_title`'s truncation and its docstring sentence. Under option (b) also `_resolve_output_file`'s composition and its docstring. Test targets: `tests/test_security.py::TestSanitizeTitle` and `::TestResolveOutputFile`.

**Do not touch.** The set of characters removed (`P12-B3`). Device names and trailing dots (`P12-B5`).

**Mechanical verification.** Option (a): `TestSanitizeTitle::test_limits_length_to_100_characters` passes **unchanged** and the docstring names the *component* as the limited thing. Option (b): an oracle asserts the composed path stays within the declared budget **at a deep directory**, and `TestResolveOutputFile`'s exact-name assertions are updated consistently — the same title at a different depth must still be deterministic. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Honest judgement required.** `D-2`. Measured: a 777-character path is **accepted** on this host, so the artifact's UNVERIFIED `WinError 206` failure was not reproduced. A host property the product cannot control is a poor thing to guarantee in code. The docstring's current claim is not false — it is true of the component — but it is read as a claim about the file, which is the whole of the finding.

**Deliverable.** One commit. If option (b) is chosen, the re-scoped assertion is **named in the commit body with the reason**, because it is a pinned test.

**Blocked by.** `B3`. **Blocks:** `B5`.

---

### 6.5 `P12-B5` — device names and trailing dots

**Semantic target.** `utils/security.py::sanitize_title`'s normalisation chain, and under option (a) the symbol name plus `utils/__init__.py`'s `__all__` and both call sites (`security._resolve_output_file`, and `downloader`'s title callback). Test target: `tests/test_security.py::TestSanitizeTitle`.

**Do not touch.** `P12-B3`'s control-character set unless both blocks take the "one normalisation chain" shape, in which case `B3` has already landed.

**Mechanical verification.** The measured table is recorded in the block: `CON`, `CON.txt`, `NUL` write without exception and leave no file; `AUX.txt` raises `FileNotFoundError [Errno 2]`; `sanitize_title("title...")` is a no-op. Option (b) oracles: one bare device name, one device name with an extension, one trailing dot — asserting the **normalisation**, not the platform's refusal, so the test is not POSIX-shaped and does not consume the 4-skip budget. Option (a): `grep` shows the old symbol is gone from `utils/security.py`, `utils/__init__.py` and the tests, and the new name is consistent. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged; **skips unchanged at 3**.

**Honest judgement required.** `D-3`. Verify before deciding whether the `_{id}.mp4` suffix invariant is real — that every filesystem-facing call site appends a suffix. The whole severity rests on it. Under option (b) the display caller's output changes (device names gain a prefix, trailing dots disappear); that is a visible console change for a cosmetic path and must be accepted explicitly, not absorbed.

**Deliverable.** One commit. Option (a)'s rename is a breaking change for an external importer of `vkdownloader.utils.sanitize_title`; the commit body says so.

**Blocked by.** `B4`. **Blocks:** `B10` (route (b) only).

---

### 6.6 `P12-B6` — the sweeps match the tree

**Semantic targets.** Four code sites and two test classes:
1. `services/segment_downloader.py::_cleanup_segments` — the bare `f.unlink()` over `glob("*")`.
2. `services/segment_downloader.py::_tally_and_merge` — the `downloaded_count` derived from `glob("*.ts")`.
3. `services/segment_downloader.py::_clear_stale_segments` — the same glob, plus the `.signature` short-circuit (**this block is the only one allowed to change the short-circuit** — §4.3 row 8).
4. `services/ffmpeg_utils.py::_merge_segments_batched` — the deferral comment assigning the merge-temp counting to `ART-004` (one comment block, two deferrals; `B8` rewrites the other half later — §4.3 row 13).
5. `tests/test_hls_downloader.py::TestCleanupSegments` — **extend the existing class**.
6. `tests/test_segment_downloader.py::TestPreserveSegmentsReporter` — **only** if `D-4` resolves to (ii).

**Do not touch.** `_cleanup_segments`'s call sites (`B7` owns those; this block adds none). The `if result:` guard itself — the guard must still wrap every call site after `B7` lands. `_log_preserve_segments`'s unconditional report — that is `ART-005`'s already-fixed, pinned half. The residue must be established from the tree: `NNNNN.ts.tmp` is what the two `with_suffix(suffix + ".tmp")` publish sites leave behind, and **no test anywhere uses `os.replace`**, so no existing oracle can see it.

**Mechanical verification.** (i) A directory in the tree does not turn a completed download into an exception — oracle added to `TestCleanupSegments`, asserting the call returns, with **no** POSIX exception type named. (ii) The merge is **reached** when the tree holds the expected segments plus leftover `batch_*.ts` files. (iii) A `.ts.tmp` does not survive a stale sweep. (iv) `TestMergeSegmentsBatched`'s "batch failure preserves inputs and earlier batch temps" passes **unchanged** — it is the D-13 preservation oracle and it is precisely the residue this finding is about. (v) `TestPreserveSegmentsReporter`'s three tests pass, unchanged or declared. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Honest judgement required.** `D-4` — whether `_log_preserve_segments`'s number is a working-directory **inventory** or a resumable-segment **count**. Its docstring, its `next_action` ("clear the working directory") and its pinned test all say inventory, which argues for narrowing only the merge decision's count. The counter-argument: one definition of "a resumable segment", used by both call sites, is what stops the two from drifting again. Whichever is chosen, the `count_note` text must remain **true** — under option (ii) the note "this is not a count of resumable segments" becomes false and must change.

**Deliverable.** One commit. The commit body records `D-4`'s outcome and, if a pinned test was edited, names it.

**Blocked by.** Nothing. **Blocks:** `B7`, `B9`.

---

### 6.7 `P12-B7` — the working tree's lifetime

**Status:** DONE — implemented, tested (1063 passed, 3 skipped), committed as `e2c5ad0`. Execution position 7 (after `P12-B6`, before `P12-B8`).
**Task file:** `.ai/tasks/p12-b7-tree-lifetime.yaml`

**Semantic targets.**
1. `services/segment_downloader.py::download_hls_with_resume` — the `segments_dir.mkdir(parents=True, exist_ok=True)` that runs before the playlist is fetched, and the `finally` that only reports today.
2. `services/segment_downloader.py::_run_download_session` — the playlist fetch, and therefore the order of `mkdir`, `_clear_stale_segments` and the fan-out. Deferring the `mkdir` means the sweep has no directory to sweep at fetch time; that ordering must be re-established explicitly and the docstrings updated.
3. `services/segment_downloader.py::_cleanup_segments` — **new call sites** for the exits that fail before or instead of a merge.
4. `tests/test_segment_downloader.py` — oracles for: no tree before the playlist is known; the tree removed after a failed session, after a graceful merge-stage failure, and after the merge's own `FileNotFoundError` precondition.

**Do not touch.** `_clear_stale_segments`'s short-circuit (`B6`'s). `_tally_and_merge`'s count (`B6`'s). `_merge_segments_batched` (`ffmpeg_utils.py`, `B8`'s). Any count gate anywhere — **forbidden**; `TestPreserveSegmentsReporter` pins the unconditional report.

**Mechanical verification.** (i) A session that fails at the playlist fetch leaves no tree — the strongest single oracle, because it fails if the `mkdir` stays where it is. (ii) Each of the three non-success exits removes the tree. (iii) The merge's success path is unchanged: the tree is removed after a successful merge exactly as today. (iv) `TestPreserveSegmentsReporter`'s three tests pass **unchanged**. (v) `TestSegmentFanoutCompletion`, `TestSegmentFanoutBoundedProduction` and `TestConnectorCeilingsFollowTheSetting` pass **unchanged** — the bounded fan-out is the most heavily specified code in this module and this block must not touch it. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Honest judgement required.** The removal point (§3.5): one place in `download_hls_with_resume`'s `finally`, or three places at the layer that knows why it failed. Criterion: does the operator ever want the tree preserved for manual inspection? Today the only thing that happens on failure is a log record telling them to clear the directory — nothing reads the tree — which argues for the single point. Second honest judgement: if the tree is gone before the reporter runs, the reporter's call must move with the removal, and `working_dir_ts_count` will read 0 on paths it now observes. That is correct and the pinned test still passes, but it is a change in what the record means, and it belongs in the commit body.

**Deliverable.** One commit. It carries the shared insertion point for `ART-005` and `ART-013`'s lifetime half; the commit body says so, because the artifact's own analysis found these two findings converge there.

**Blocked by.** `B6`. **Blocks:** `B8`, `B9`.

---

### 6.8 `P12-B8` — space at both stages

**Status:** DONE — implemented, tested (1068 passed, 3 skipped), committed as `0c704de`. Execution position 8 (after `P12-B7`, before `P12-B9`).
**Task file:** `.ai/tasks/p12-b8-space-probe.yaml`

**Semantic targets.**
1. `services/segment_downloader.py` — a new download-stage free-space precondition ahead of the fan-out. Demand figure per §3.6's alternatives.
2. `services/ffmpeg_utils.py::_required_merge_bytes` — the multiplier and the docstring's `2×` justification. **Arithmetic and docstring only** (`C4`: the module imports only `..exceptions` and `..utils.formatting`).
3. `services/ffmpeg_utils.py::_merge_segments_batched` — the deferral comment assigning the sizing to `ART-012`, and the batch-size literal if it becomes a shared constant.
4. `tests/test_ffmpeg_utils.py::TestMergeFreeSpaceProbe` — **three** assertions change, declared.

**Do not touch.** The merge's existence check (its `FileNotFoundError` naming the missing file). `_check_merge_space`'s rule that a missing segment contributes nothing and an unreadable mount does not block the merge. The three `D-11` oracles. The artifact's 3.15× / 1.40× figures — measured on a synthetic 250-segment set the artifact itself marks non-transferable, never re-driven; **do not cite or reproduce them.**

**Mechanical verification.** (i) A download that cannot fit raises an actionable `DownloadError` **before** the fan-out, naming required and available, with the same `hint` shape the merge's probe already uses. (ii) A failed probe (unreadable mount) logs and proceeds, exactly as the merge's probe does — a new hard-failure path for an unmeasurable volume is a regression. (iii) `grep`: `shutil.disk_usage` goes from **one** call site to **two**, and the tree has two free-space probes. This is the finding's core claim and it must be checkable by a future auditor without reading a diff. (iv) The three `TestMergeFreeSpaceProbe` assertions are updated to the new multiplier **and** still protect the direction the original docstring names — "fails if the arithmetic drifts toward the segment total alone". (v) The class's other four tests pass unchanged, including the one-byte-below boundary, which must still be a boundary: **the new figure must not be rounded.** `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Honest judgement required.** Two choices. Where the download-stage check lives: a fixed budget up front, an observed-first-batch figure, or an incremental check inside the pump — the pump option is argued against explicitly, because segments **are** resumable, so a download-stage space failure is not the catastrophe a merge failure is. And the multiplier: a flat `3×` that over-estimates the common single-batch merge by 50%, or a peak-aware figure computed from the batch size the merge actually uses (one named constant, still leaf-safe). This Planner does not pick either.

**Deliverable.** One commit. **The commit body names all three changed assertions and the reason each changed.** A silent change to a pinned test in this plan is a failure of the plan, not of the block.

**Blocked by.** `B7`. **Blocks:** `B9`.

---

### 6.9 `P12-B9` — the probe and the cleanup name the right file

**Status:** DONE — implemented, tested (1073 passed, 3 skipped), committed as `767bb47`. Execution position 9 (after `P12-B8`, plan terminus). Route (a) chosen.
**Task file:** `.ai/tasks/p12-b9-partial-file-probe.yaml`

**Semantic targets.**
1. `services/ytdlp_downloader.py::download_with_ytdlp_with_resume_fallback` — the partial-file probe, repointed from the final name to yt-dlp's `.part` temp name.
2. `services/ytdlp_downloader.py::_build_ytdlp_cli_command` — the command construction; measured **zero** occurrences of `no-part` in `src/`, so yt-dlp's `FileDownloader.temp_name` writes `<name>.part`.
3. The `DF-008` cleanup at the end of the retry loop, repointed from the final name to the `.part` temp name.
4. `tests/test_hls_downloader.py::TestYtdlpCliCommand` — route (b) only.

**Do not touch.** The `output_file.unlink()` inside `_attempt_segment_resume` — it discards partial state to start a segment download clean, and whether discarding an existing final artefact on the retry path is acceptable is `ROLLOUT-1`'s risk to record, not this block's to fix. The retry loop's structure. The mislabels (`OUT-016`). The `--method ffmpeg` fallback arm (`P10-B10`'s).

**Mechanical verification.** (i) One helper (`_ytdlp_temp_name`) derives the temp name; the probe and the `DF-008` cleanup both call it, asserted by test so they cannot diverge. (ii) The probe's contract is unchanged in shape — existence **and** non-zero size, with a zero-length `.part` explicitly not counting as progress. (iii) Exhausting the loop still logs and returns `None`. (iv) `TestYtDlpRetryBackoff`, `TestAttemptSegmentResumeQuality`, `TestB13ResumeErrorHandling`, `TestPerformDownload`, and `TestBatchDownloaderSemaphore` tests pass after updating their simulated partial files to `.part`. (v) The `.part` name is verified against the **installed** yt-dlp version's `FileDownloader.temp_name` in `TestYtdlpTempName`. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged from its red baseline; skip count 3.

**Honest judgement required.** `D-5` — route (a) repoint, (b) `--no-part`, or (c) probe both. Criterion: route (b) removes the child's own resumability, replacing it with the segment path's resume, which needs a fresh browser token that `_attempt_segment_resume` forces. A reader should treat (a) as the default and (b) as requiring an explicit argument. Under (c), which name does `DF-008` remove, and does leaving the other behind recreate the residue problem?

**Deliverable.** One commit, **alone** — see `ROLLOUT-1`. Route (b) additionally edits `TestYtdlpCliCommand`'s `--no-part`-absent assertion, and that edit is **named in the commit body**.

**Blocked by.** `B3`, `B6`, `B7`, `B8`. **Blocks:** nothing (it is the plan's terminus).

---

### 6.10 `P12-B10` — dedup by resolved output filename, before dispatch (`ART-006`) — Decision A

**Decision A is closed. `D-6` is closed, and neither offered option was chosen.** Dedup by resolved output filename; **last occurrence wins**; earlier occurrences skipped, reported, and performing no media transfer.

**Semantic targets.**
1. `services/downloader.py::download_video` — the extract → `title_callback` → `_resolve_output_file` → `perform_download` pipeline. The dedup pre-pass sits between resolution and dispatch. Docstring updated to state the pipeline.
2. `src/vkdownloader/cli.py` — the `batch` reader: `valid_urls`, `skipped_count`, the per-line loop. **Where the skipped entries are counted.**
3. `utils/security.py::_resolve_output_file` — **the key producer. Read, not modified** (except its `warning` argument under `P12-B2`).
4. `services/batch_downloader.py` — the fan-out threading `output_index`, and `_print_batch_summary` plus the per-item `results` accounting for the report.
5. `tests/test_cli.py::TestBatchCommand` — extended; **the whole oracle set is new**, because nothing asserts anything about duplicates today.

**Do not touch.** `_resolve_output_file`'s composition. The semaphore and the bounded pump. `ProgressStatus.SKIPPED` — it already exists; the block uses it, does not define it. `exceptions.py`'s `_map_exception_to_status` — a dedup skip is not an exception. Any name suffixing.

**Mechanical verification.** (i) Two entries resolving to the same path → **exactly one dispatch**, and it is the **last** in list order; assert both the count and the identity. (ii) The skipped entry performs **no media transfer**: patch the dispatch, the permit, the subprocess, the segment fetch and the working tree, and assert not-called. (iii) The skip is visible at **both** levels: `ProgressStatus.SKIPPED` in `results`, and a dedup summary line **distinct** from the invalid-URL line. (iv) The key is the resolved path, asserted **both ways**: different titles sanitising to one filename **are** deduped; same `id` with different `output_index` and no title are **not**. (v) Idempotence on re-run. (vi) The single-URL command is unchanged and carries no registry. (vii) `TestBatchDownloaderSemaphore`, `TestBatchLiveTaskBounding` and the bounded-fan-out classes pass unchanged. (viii) The `mkdir` side effect (`C9`) is asserted, not assumed. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged; skip count 3.

**Honest judgement required.** Two things.

First, **where the pre-pass lives** (§3.8's (a) versus (b)). Under (a) the pre-pass is per-entry inside `download_video` and every entry is extracted regardless; under (b) it is a resolution phase in `batch_downloader` before the fan-out, which changes the batch's latency profile and needs its own bounding. **The criterion is whether the batch's progress display stays meaningful during a long batch** — and the note that if Decision A's no-network clause is strict, (b) is forced, because (a) extracts every entry either way.

Second, **what "no network" can mean here**, and this is escalated rather than decided. `download_video` calls `extract_streams` **before** `_resolve_output_file`, so the resolved filename is not knowable without a network call. The decision's key and a literal no-network reading are jointly unsatisfiable. This block delivers the achievable form — **no media transfer for a skipped entry** — and records the gap as `DEF-6`. It must **not** relax the clause further than that without `DEF-6` existing on the record.

**The measurement that shrinks this block.** Within-batch name collision is **structurally impossible** after dedup: unique resolved paths by construction, one permit per survivor, output file computed before the permit is taken, and `.part` derived from the output path. **A name-level mutex is therefore not planned** (§1.3, §5.4 `C3`). The cross-run case is recorded as a residual (§5.7 item 4), not solved.

**Deliverable.** One commit. The commit body records the pre-pass shape, the `mkdir` side effect, and — if the no-network clause was narrowed to "no media transfer" — that narrowing and why.

**Blocked by.** Nothing. `B5` only if its route (b) changes `sanitize_title`'s output, since the key derives from it — a read dependency, and this is the first block that can land. **Blocks:** `B2`.

---

### 6.11 `P12-B11` — the confinement posture

**Status:** DONE — no code change needed (preferred shape "no code at all"). Verified: in-code comment in `setup_logging` already states the Windows caveat; `docs/01-tools/vkdownloader-overview.md` and `docs/11-guides/configuration.md` already carry the same caveat. `grep` over `src/` for `gettempdir`/`iterdir`/`rmtree` shows only the pre-existing cookie-artefact lifecycle in `ytdlp_downloader.py` (SEC-001/SEC-002), no new occurrences introduced by this plan.

**Semantic targets.**
1. `src/vkdownloader/config.py::setup_logging` — the log-file creation branch, **only if** the chosen option changes what it does.
2. `docs/11-guides/configuration.md` and `docs/01-tools/vkdownloader-overview.md` — the two documents that already carry the Windows caveat for other artefacts, in the same register and the same words.
3. The in-code comment in `setup_logging` that already states this finding's conclusion ("requested for its POSIX effect only, and no access control list is applied") — updated, never removed.

**Do not touch.** The three `D-11` mode oracles (`DEF-1`, `TST-013`'s). The `ResourceWarning: unclosed file` from `logging.basicConfig`'s FileHandler — recorded here as an **observation only**; fixing the handler lifetime is `P11-B6`'s territory and touches both plans. The eight-file `--method ffmpeg` documentation surface (`P10-B10`'s). Any sweep over the system temp directory and any age heuristic — **forbidden**, and `P11`'s reaper deliberately rules both out.

**Mechanical verification.** (i) `grep` over `src/` for `gettempdir`, `iterdir`, `rmtree` and any time-based expiry returns nothing new — measured today: **zero** occurrences of the first three. (ii) The `setup_logging` comment and the documentation state the same posture; the divergence is the failure this block exists to prevent, so the review must read both. (iii) If a dependency is added: `pyproject.toml` and all four `test_packaging.py` frozensets edited in the same commit. (iv) Skip count stays at 3. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged.

**Honest judgement required.** `D-7`. What confinement mechanisms are actually available to this process on Windows **without** a new dependency — that is an investigation, and its answer decides whether the DACL option is even on the table. Then: an explicit DACL would be a Windows-only code path that **no oracle on any host can verify**, and the finding's own verdict is "zero runnable oracles". Rule 2 makes production code king over tests, so an unverifiable platform path is a liability, not a fix. Between stating it plainly and reframing the request, the difference is whether the code keeps making a `0o600` request it cannot honour — that is a product-claim question.

**Deliverable.** One commit. **Preferred shape: no code at all** (option (c) or (d)), in which case the cross-plan dependency on `P11-B6` disappears. If `B11` does change `setup_logging`, it lands after `P11-B6`.

**Blocked by.** `P11-B6` (only if it changes behaviour). **Blocks:** nothing.

---

### 6.12 `P12-B12` — the structural map sentence

**Status:** DONE — committed as part of `767bb47`. The `docs/STRUCT.md` line for `ffmpeg_utils.py` updated to name all three surviving kinds: shared subprocess infrastructure, availability discovery, and the segment merge engine. No frozenset changes (no new files).

**Semantic target.** `docs/STRUCT.md` — the `services/` tree listing's entry for `ffmpeg_utils.py`, currently "FFmpeg discovery and stream concatenation". Read `docs/00-overview/doc-maintenance-rules.md` before editing anything under `docs/`.

**Do not touch.** The eight-file `--method ffmpeg` documentation surface (`P10-B10`'s obligation). `docs/STRUCT.md`'s other entries, its layering section, or its lack of frontmatter — it is a root structural map, edited in place.

**Mechanical verification.** The new sentence names all three surviving kinds — shared subprocess infrastructure, availability discovery, and the segment merge engine. **A reader who deletes what the sentence names must not take `iter_process_lines`, `cancel_subprocess` or `check_ffmpeg_available` with them**: `ytdlp_downloader` imports the first two directly for the child's stdout draining and cancellation, and `perform_download` calls the third as the startup probe that protects the merge. The sentence does **not** name the ffmpeg loader transport. `grep` confirms no other file changed, so the four `test_packaging.py` frozensets stay at 73 / 32 / 2 / 4. `G1`, `G2`, `G4`, `G6` exit 0; `G5` non-increasing; `G3` unchanged; skip count 3 — the edit is inert to every gate, which is why they run anyway.

**Honest judgement required.** The wording has one live trap, and it is the opposite of the one this block originally recorded. "FFmpeg discovery and stream concatenation" reads as though discovery were the disposable half — and under Decision C **discovery is the half that must survive**, because `check_ffmpeg_available` is the startup probe that warns before a long download fails at the merge, and the merger is permanent. A description written only for the current tree will read as justifying exactly the deletions §3.12 forbids.

**Deliverable.** One commit. The only block in this plan without a Validator — the diff is one line, the fact is verified, and a review would exceed the risk. Recorded rather than defaulted.

**Blocked by.** Nothing. **Blocks:** nothing.

---

## 7. Verification strategy

Three layers: a gate every block runs, a gate the plan as a whole runs, and a trace from each finding to the oracle that proves it is closed.

### 7.1 The standing gate — every block, every commit

Run in this order. Any non-zero exit stops the commit.

| # | Command | Requirement |
|---|---|---|
| 1 | `uv run pytest tests/ -q -rs` | Exit 0. **Pass count ≥ the pre-block count minus only the declared test re-scopes in §5.6.** Skip count **3 at rest**; `P12-B10`'s commit is the single exception at 4 if it adds a test. |
| 2 | `uv run ruff check src tests` | Exit 0, `All checks passed!` |
| 3 | `uv run ruff format --check src tests` | **Exit 1 — red at baseline and unchanged by any block.** Delta is the pre-existing `tests/test_hls_downloader.py` reformat, which no block may absorb or widen. |
| 4 | `uv run mypy src` | Exit 0, `Success: no issues found in 31 source files` |
| 5 | `uv run mypy src tests` | **Exit 1 both before and after.** Total ≤ the pre-block total (**86**). **Zero errors in `src/`.** Delta only — a red gate that carries signal only as movement. |
| 6 | `uv run ruff check .` | Exit 0, `All checks passed!` |

**Never invoke bare `uv run mypy`.** It has no default target and will report success over nothing.

**Warning counts are observed, never gated.** Measured **1** at both commits (`RuntimeWarning: coroutine 'Event.wait' was never awaited`). The two additional `ResourceWarning: unclosed file` records originate in `config.setup_logging`'s `logging.basicConfig` FileHandler — a real unclosed-handler leak inside `ART-007`'s own subject — and surface non-deterministically. A block that changes the handler lifetime may change this count; nothing else may.

**The three skips are the `D-11` mode oracles** — two in `tests/test_config.py`, one in `tests/test_hls_downloader.py::TestCreateTempCookieFile`. Their count is a gate in both directions: adding a platform-gated test to work around an unverified behaviour consumes budget that `ART-007`'s oracles need, and `P12-B11` must not touch them at all.

### 7.2 Per-block gate — what each block adds on top of §7.1

| Block | Additional mechanical checks | Named in the commit body |
|---|---|---|
| `P12-B3` | Table-driven oracle over `chr(0)`–`chr(31)` + `chr(127)`; `TestSanitizeTitle`'s six existing tests unchanged | The control range; the display consequence |
| `P12-B1` | False-positive oracle accepted; all 5 `TestValidateOutputPathTraversal` tests unchanged; a **new** oracle that reaches the post-resolution layer (the existing "resolved" test does not — its own comment says so) | — |
| `P12-B2` | `repo_root` derives to the repository root **by value, not by mock**; a path under the root but outside `src/` warns while one under `src/` still warns; the blind mock is removed or supplemented (**declared**); **acceptance behaviour is otherwise unchanged** | Which option, and why the others were not |
| `P12-B4` | Option (a): the pin passes unchanged. Option (b): a composed-path budget oracle at a deep directory | A re-scoped pinned assertion, if any |
| `P12-B5` | Normalisation oracles (bare device name, device name + extension, trailing dot) — **asserting normalisation, not the platform's refusal**, so no skip is consumed. Option (a): `grep` shows the old symbol gone from all three sites | The breaking change, if (a) |
| `P12-B6` | Non-regular-entry oracle in `TestCleanupSegments` with **no** POSIX exception named; merge-**reached** oracle with leftover temps; `.ts.tmp` sweep oracle; `TestMergeSegmentsBatched`'s failure-preservation test unchanged | `D-4`'s outcome; any edited pinned test |
| `P12-B7` | No tree before the playlist is parsed; tree removed on each of the three non-success exits; merge success path unchanged; `TestPreserveSegmentsReporter`'s three tests unchanged; the bounded fan-out classes unchanged | If the reporter's call moved, and what the count now means |
| `P12-B8` | `grep`: `shutil.disk_usage` **1 → 2** call sites; a failed probe logs and proceeds; the one-byte-below boundary test still a boundary (the figure is **not** rounded) | **All three** `TestMergeFreeSpaceProbe` assertions and why each changed |
| `P12-B9` | One helper, two callers, asserted; existence **and** non-zero size both load-bearing; a zero-length `.part` does not count; the `.part` name verified against the installed yt-dlp's `FileDownloader.temp_name` | Route (b)'s pinned-test edit; the reachability promotion |
| `P12-B10` | Exactly one dispatch and it is the **last**; the skipped entry's dispatch/permit/subprocess/segment/working-tree all **not called**; `ProgressStatus.SKIPPED` **and** a distinct summary line; key asserted both directions (sanitised-title collision deduped, differing `output_index` **not** deduped); idempotence; single-URL path unchanged; the `mkdir` side effect asserted | The pre-pass shape; the `mkdir` side effect; any narrowing of the no-network clause |
| `P12-B11` | `grep` over `src/` for `gettempdir` / `iterdir` / `rmtree` returns nothing new (0 today) and no age heuristic appears; comment and documentation agree; dependency declaration and all four frozensets edited together if a dependency is added | — |
| `P12-B12` | The sentence names all three surviving kinds and not the deleted loader; `grep` confirms no other file changed, so the frozensets stay at 73 / 32 | — |

### 7.3 End-of-plan gate — run after `P12-B9`

The standing gate (§7.1) **plus** the following, which are only meaningful once all twelve blocks have landed:

1. **`ROLLOUT-1` verification.** For each of `ART-001`, `ART-003`, `ART-004`, `ART-005`, `ART-012` and `ART-013`, state on the record that its fix is landed **and** that it is now default-reachable. A block landing without this statement is an incomplete rollout, not an incomplete fix.
2. **No sweep of the system temp directory exists.** `grep` over `src/` for `gettempdir`, `iterdir`, `rmtree` and any time-based expiry: zero. `ART-008`'s residue class stays empty — because the argfile was the **loader's** artefact, not because a transport was retired wholesale (§2.4.2).
3. **The `ffmpeg_utils.py` contract is intact and the module is permanent.** Assert by symbol: `iter_process_lines` and `cancel_subprocess` are still imported and used by `ytdlp_downloader`; **`check_ffmpeg_available` still exists and is still called as the startup probe**; every group C symbol still exists; and the module still imports only `..exceptions` and `..utils.formatting` (`C4`). A reader acting on `docs/STRUCT.md` must not be able to delete any of the three kinds (`P12-B12`). **Decision C: none of this is planned for removal, by this plan or any other.**
4. **Every in-code deferral pointer is discharged.** `_merge_segments_batched`'s comment block (both halves), `_log_preserve_segments`'s `ART-004` note, and `config.setup_logging`'s comment that states `ART-007`'s own conclusion — none may still point at a finding this plan closed (`D1` in §5.5).
5. **The skip count is still 3** and the three `D-11` mode oracles are untouched (`DEF-1` is `TST-013`'s).
6. **`EXPECTED_SDIST_ENTRIES` is 73, `EXPECTED_WHEEL_ENTRIES` is 32, `BUILDER_ADDED_SDIST_ENTRIES` is 2, `EXPECTED_DIST_INFO_ENTRIES` is 4** — or the block that added a file edited the affected sets in its own commit and this plan records the new counts. **A new file under `src/vkdownloader/` moves both the sdist and the wheel set.**
7. **The full residue set is enumerable.** `grep` over `src/` lists every filesystem pattern in use, and each is either reconciled by a sweep or recorded as a known residue in `DEF-2`'s hand-off to `DEP-004`.
8. **Decision A holds end to end.** For every entry in a batch, assert exactly one of: dispatched, or skipped-with-a-report. No third outcome, and specifically **no entry that was skipped but still transferred**.
9. **§5.7's prohibitions are reviewed on the record.** Each is still true after every block has landed. A block that closed one of them must say which, and how.

### 7.4 Per-finding verification trace

| Finding | Block | The oracle that proves it | Verified by | Residual after the block |
|---|---|---|---|---|
| `ART-001` (name half) | `B3` | Table-driven control-character oracle in `TestSanitizeTitle`; the six existing tests unchanged | `B3` Validator | The mislabels remain (`OUT-016`, phase 08). |
| `ART-001` (diagnostics half) | — | — | — | **Not closed here.** Phase 08. |
| `ART-002` | `B9` | One-helper-two-callers assertion; existence-and-non-zero-size preserved; the `.part` name verified against the installed yt-dlp | `B9` Validator + §7.3 item 1 | **Reduced, not removed, by Decision A**: a duplicate no longer dispatches so it creates no `.part`, but a non-duplicate item still writes one, and the probe/cleanup naming the wrong file is untouched. |
| `ART-003` | `B6` | Non-regular-entry oracle in the existing `TestCleanupSegments`, naming no POSIX exception | `B6` Validator | — |
| `ART-004` | `B6` | Merge-**reached** oracle with leftover `batch_*.ts`; the `.signature` reconciliation oracle; `TestMergeSegmentsBatched`'s failure-preservation test unchanged | `B6` Validator | Whether `D-4` chose (i) or (ii) determines whether the reporter's count was narrowed. Recorded either way. |
| `ART-005` | `B7` | No-tree-before-playlist oracle; three non-success-exit oracles; the pinned reporter class unchanged | `B7` Validator | Whether the operator ever wants a preserved tree for inspection is the undecided question (`§3.5`). |
| `ART-006` | `B10` | One-dispatch-and-it-is-the-last; no-media-transfer not-called assertions on dispatch/permit/subprocess/segment/working tree; `ProgressStatus.SKIPPED` **and** a distinct summary line; key asserted both directions; idempotence; `mkdir` side effect asserted | `B10` Validator | **Within-batch collision is structurally eliminated** — no mutex needed, none introduced. **Cross-run collision is not**: dedup is per invocation. `DEF-6` (the extraction call the key requires) is unresolved. |
| `ART-007` | `B11` | `grep` proving no sweep and no age heuristic; comment and documentation read together | `B11` Validator | **Both halves open.** Zero compensating controls and zero runnable oracles survive (`§5.7` items 1–2). The block records a posture; it closes no exposure on options (c) and (d). |
| `ART-008` | — | §7.3 item 2 | §7.3 | **Retired, and not to be resurrected.** The residue class is empty because the argfile was the **loader's** artefact. |
| `ART-009` | `B2` | `repo_root` derived **by value**; a root-but-not-`src/` path warns; the blind mock removed or supplemented | `B2` Validator | **Resolved by Decision B, option (a).** The absence of a containment root is decided behaviour, not a residual. Both `warning=False` suppressions were dropped (`_resolve_output_file` and the ytdlp retry probe), so the warning now fires on all three call sites. Nothing remains open. |
| `ART-010` | `B1` | False-positive oracle accepted; post-resolution layer reached by a new oracle | `B1` Validator | — |
| `ART-011` | `B4` | Option (a): the pin unchanged and the docstring names the component. Option (b): a composed-path budget oracle | `B4` Validator | Under Decision B a long path is **accepted by design**; `B4` records the bound's true scope rather than adding a limit. |
| `ART-012` | `B8` | `disk_usage` **1 → 2** by grep; the three declared assertion changes; the unrounded boundary test | `B8` Validator | **Raised in importance by Decision C**: the merge is the only merge and permanent, so a too-low estimate is a standing defect there. The volume can still fill after the probe — another process may consume it, and no probe can predict that. |
| `ART-013` | `B6` + `B7` | Sweep-reconciliation oracle (`B6`); tree removal on the non-success exits (`B7`) | Both validators | The `.gitignore` coverage verdict is `DEP-004`'s (`DEF-2`); `B6` supplies its per-pattern evidence. |
| `ART-014` | `B5` | Three normalisation oracles, or the consistency `grep` under option (a) | `B5` Validator | POSIX treats these names as ordinary files (`§5.7` item 8). |
| `VAL-701` / `ROLLOUT-1` | `B9` | §7.3 item 1: the six findings' default reachability stated on the record when `B9` lands | `B9` Validator + Tech Lead | **Decision A does not relieve it** — it reduces item count, not reachability. If `B9` was batched with any of the six, the promotion must be recorded in that batch's commit body instead. |

---

## Plan self-check

- **The baseline was re-measured at `58bb7ce`, not inherited.** All six gates re-run; `src` and `tests` clean at that commit. Every figure in §2.0 is from this session.
- **Every gate figure that changed is corrected, and the change is shown as a delta** so a reader can see what moved and why: 752 passed / **3 skipped** (was 4 — the argfile's mode oracle went with the loader) · `mypy src tests` **86 errors** (was 79; `test_hls_downloader.py` 33) · **`G3` is now red** and is planned *around*, with a two-way gate lock and an explicit rule that no block absorbs the pre-existing reformat · `test_hls_downloader.py` **3944** lines · `ffmpeg_utils.py` **493** lines.
- **A useful result of the re-baseline:** every file carrying a phase-07 anchor except the loader's own is **unchanged**. `security.py`, `segment_downloader.py`, `test_security.py`, `test_segment_downloader.py` and `test_ffmpeg_utils.py` did not move, so the earlier re-derivation for `ART-001`/`003`/`004`/`005`/`009`/`010`/`011`/`012`/`013`/`014` still holds and the table in §2.6 records it.
- **Decision A closed `D-6` and changed `ART-006`'s shape**, from collision *handling* to collision *elimination*. The dedup key is stated and justified as the **resolved output path**, not `(title, id)`, with both directions of the reason. Last-wins is recorded as the ruling; the criterion it was decided against is **kept as the test**. The skip's report uses **existing machinery only** — `ProgressStatus.SKIPPED` and the batch summary — with no new channel and no new exception mapping.
- **The mutex question was measured, not assumed.** Within-batch collision is **structurally impossible** after dedup; no lock primitive is introduced and `ART-006` shrinks. The cross-run case is named as the residual that would need one. A separate entry, `DEF-6`, records that the resolved filename requires an extraction call, so a literal reading of "no network at all" is not implementable — surfaced, not reinterpreted.
- **Decision B closed `D-1` and shrank `ART-009`.** No root, no refusal, no scope decision. `C:\Windows\System32` and `/etc` being accepted are now stated as **correct**. What remains is two things: the `repo_root` derivation and the two-of-three suppression — and the derivation is a real defect specifically *because* the warning is computed from it. `B2`'s acceptance criteria now forbid the most likely failure mode, which is a "reliable warning" that quietly becomes a restriction.
- **Decision C corrected §2.4.** `check_ffmpeg_available` is **permanent**, not retiring — it is the startup probe that protects the merge. The merge engine is stated as **permanent product surface** with an explicit prohibition on planning it for deletion, `ART-012` is raised, and `ART-008` stays retired **for the correct reason** (the argfile was the loader's artefact).
- **The plan-10 claim is withdrawn in §1.1.3.** `P10-B10` does name `ffmpeg_utils.py` with the five symbols to delete. `P12-B12` keeps its ownership of the `docs/STRUCT.md` sentence, re-checked against the module as it now stands — which now has **three** deletable-looking parts, and "discovery" is one of them.
- **`ROLLOUT-1` is unchanged by Decision A**, and the plan says so explicitly in three places (§2.4.6, §3.8, §4.2) rather than leaving a reader to infer it.
- **Six decisions remain open** — `D-2`, `D-3`, `D-4`, `D-5`, `D-7`, and the `B10` pre-pass shape — each with a stated criterion and none chosen by the Planner.
- **The gate lock is two-way** (§2.1), plan 11's `%TEMP%`-glob and age-heuristic exclusion is still asserted by grep in `B11`, and the `P11-B6 → B12-B11 → P11-B3` ordering on `setup_logging` is carried in both §4.2 and conflict-matrix row 19.
- **Nothing in this plan preserves, restores, hardens or documents the ffmpeg loader.** The merger is explicitly exempt from that prohibition and is stated as permanent in §1.3, §2.4.4, §5.4 and §7.3.
- **No block writes an oracle for the Windows mode** — that is `DEF-1`, owned by `TST-013`, and the 3-skip count is a gate in both directions.
- **Nothing in this plan edits `services/downloader.py`'s re-export lines as a remedy** (`C3`), and nothing adds a lock file, a temp-dir abstraction, `fsync`, a clobber policy, a name suffix or a temp sweep.

**Plan ends.** Twelve blocks, one commit each; fourteen findings routed; seven deferred with named owners; six decisions left open with stated criteria rather than chosen by the Planner.

---

## 8. Implementation task: P12-B1 — component-wise traversal detection

**Status:** DONE — implemented, tested (1047 passed, 3 skipped), committed as `12af960`. Execution position 2 (after `P12-B3`, which is already committed).
**Task file:** `.ai/tasks/p12-b1-component-traversal-detection.yaml`

### 8.1 Semantic scope

Exactly two locations, both inside `src/vkdownloader/utils/security.py::validate_output_path`:

1. **Pre-resolution guard** (the first `if` in the function body, before `path.resolve()`): the substring test `".." in str(path)` becomes the component-wise `".." in path.parts`. The now-unused local `path_str = str(path)` is removed.
2. **Post-resolution guard** (the defense-in-depth `if`, after `path.resolve()`): the substring test `".." in str(resolved)` becomes the component-wise `".." in resolved.parts`.

**Do not touch:** `repo_root` (the module-level expression), the `relative_to` containment comparison, the `warning` parameter plumbing, or the `return resolved`. Those are `P12-B2`'s territory. Do not collapse the two guards into one.

### 8.2 Implementation sequence

1. **Modify the pre-resolution guard.** In `validate_output_path` in `src/vkdownloader/utils/security.py`, replace `path_str = str(path)` + `if ".." in path_str:` with `if ".." in path.parts:`. Remove the unused local. Update the preceding comment to describe component-wise semantics: an exact `..` path component is refused; a component merely containing `..` is not.
2. **Modify the post-resolution guard.** Replace `if ".." in str(resolved):` with `if ".." in resolved.parts:`. Update the defense-in-depth comment to reference `resolved.parts`.
3. **Add oracles** to `tests/test_security.py::TestValidateOutputPathTraversal`:
   - **False-positive acceptance:** `Path("a..b") / "video.mp4"` is accepted (measured live today as rejected by the substring test). Assert `validate_output_path` returns without raising.
   - **New post-resolution oracle:** an input path with no `..` component so the pre-resolution guard is a no-op; patch `Path.resolve` to return a path whose `.parts` still contains `..` (e.g. `Path("/safe") / ".." / "etc"`); assert `DownloadError` is raised — proving the post-resolution layer fires independently. The test is distinguishable from the pre-resolution layer because the input contains no `..` component; the error can only originate from the post-resolution check.
4. **Run the standing gate** (§7.1): `pytest`, `ruff check src tests`, `ruff format --check src tests`, `mypy src`, `mypy src tests`, `ruff check .`. Confirm `G1`/`G2`/`G4`/`G6` exit 0, `G5` non-increasing, `G3` unchanged from red baseline, skip count 3.

### 8.3 Architectural constraints

- **Two-layer structure preserved.** The pre-resolution guard catches raw user input; the post-resolution guard catches already-resolved paths (where the pre-resolution check is a no-op) plus symlink/UNC edge cases. Both are in scope and both must be changed; they must not be merged.
- **No `file:line` references.** All anchors are symbol names: `validate_output_path`, `path.parts`, `resolved.parts`, `path.resolve`. The commit subject describes the behaviour.
- **Leaf safety.** `security.py` currently imports only `config`, `exceptions`, `models.enums`, `models.video`. `path.parts` and `resolved.parts` are stdlib `pathlib` — no new import is introduced.
- **POSIX neutrality.** `PurePath.parts` normalises both `/` and `\` on Windows, so the component-wise test is correct regardless of separator.
- **`Path(".")` is not disturbed.** `Path(".").parts` is `('.',)` — `".." not in ('.',)` is `False`, so the empty-path edge case (`TestValidateOutputPathEdgeCases::test_empty_path_resolves_to_cwd`) keeps passing. This is the one edge case that must be verified before closing.

### 8.4 Required tests — mechanical verification

| # | Oracle | Target class | Expected with fix | Expected without fix |
|---|---|---|---|---|
| (i) | False-positive: component `a..b` is accepted | `TestValidateOutputPathTraversal` | Returns without raising | **Rejected** (substring `..` in `a..b`) |
| (ii) | All 5 `TestValidateOutputPathTraversal` tests unchanged | existing | Green | Green |
| (iii) | All 3 traversal tests in `TestValidateOutputPath` unchanged | existing | Green | Green |
| (iv) | `test_empty_path_resolves_to_cwd` unchanged | `TestValidateOutputPathEdgeCases` | Green | Green |
| (v) | `test_validate_output_path_rejects_traversal_even_if_resolved` unchanged | `TestValidateOutputPathTraversal` | Green | Green |
| (vi) | New post-resolution oracle reaches the post-resolution layer | `TestValidateOutputPathTraversal` | Green (raises) | Green (raises, via pre-resolution) — but does not *prove* the post layer |

No test in the existing traversal classes is edited. Two new tests are added to `TestValidateOutputPathTraversal`.

### 8.5 Honest judgement

**The decision is low-stakes and the plan does not withhold it: prefer option (a).**

- **Option (a):** `".." in path.parts` written at both layers. The smallest change that is unambiguously correct.
- **Option (b):** a shared predicate (e.g. `_contains_parent_reference(path)`) called from both layers. Adds structure beyond what rule 5 (avoid overengineering) warrants for two call sites of a one-line expression.

**Criterion:** (a) is the smallest change that is unambiguously correct. Choose (b) only if the Implementer can demonstrate the two layers will otherwise drift again. **Recommendation: (a)** — the two layers operate on different `Path` objects (the raw argument vs. the resolved result), and a shared predicate would obscure that distinction rather than clarify it.

**The one thing to verify before closing:** `Path(".").parts` returns `('.',)`. A naive implementation that checks `str(path)` instead of `path.parts` would break `test_empty_path_resolves_to_cwd`, but the component-wise test does not. Confirm this test passes after the change.

### 8.6 Deliverable

One commit. Production change in `src/vkdownloader/utils/security.py` plus oracle extension in `tests/test_security.py`. No test in the existing traversal classes is edited. The commit subject describes the behaviour (component-wise traversal detection), not a file location. The commit body is empty or notes only the option (a) vs (b) choice.

### 8.7 Dependency metadata

- **Blocked by:** Nothing.
- **Blocks:** `P12-B2` (both write `validate_output_path`; `B1` settles what the guard refuses, `B2` settles whether the warning reaches the user).
- **Conflict-matrix rows:** §4.3 rows 2 and 5 (`validate_output_path` code; `TestValidateOutputPath`/`TestValidateOutputPathTraversal` test classes).
- **Risk tier:** Medium — security guard semantics (T8 pin set, §5.6).
- **Agent roster:** Implementer, Planner, Validator. (No Auditor — the change is one expression at two confirmed sites, fully located. No Researcher — no multi-viable approach survives the criterion above.)

---

## 9. P12-B6 Auditor context (`context_a`)

Live-tree audit of the three findings bundled under `P12-B6`
(`ART-003`, `ART-004`, `ART-013` sweep half), inspected against the
current working tree at task time. All source paths are
`src/vkdownloader/services/segment_downloader.py` and
`src/vkdownloader/services/ffmpeg_utils.py` (the plan's §1.3 `services/`
prefix resolves under `src/vkdownloader/`).

### 9.1 Current line counts (re-measured vs §2.6 table)

| File | §2.6 claims (`58bb7ce`) | Live on-disk | Discrepancy |
|---|---|---|---|
| `segment_downloader.py` | 1283 | **1275** | −8 lines; content matches semantically |
| `ffmpeg_utils.py` | 493 | **646** | **+153 lines** vs the committed figure |

The `ffmpeg_utils.py` delta is material: §2.6 line 286–288 records that
*immediately after the baseline was measured*, uncommitted modifications
appeared on `ffmpeg_utils.py` and `ytdlp_downloader.py` from a transport
finding (an over-long-line drain added to `iter_process_lines`). The
current `git status` shows **neither file as modified**, meaning those
changes were committed or reverted since the plan was written; the
on-disk file is 646 committed lines, not 493. `segment_downloader.py`
is unchanged from baseline. The symbols P12-B6 targets are all present
and match the plan's description; the line-count gap is noted for B8's
implementer, whose edit sits in that file.

### 9.2 Measurement 1 — `_cleanup_segments` call-site guard

**Finding:** `_cleanup_segments` is called **only** under `if result:`.

Confirmed at `segment_downloader.py:866–869`:

```python
        result = await _merge_segments_batched(segments_dir, output_file, len(segments))
        if result:
            _cleanup_segments(segments_dir)
        return result
```

This is the **sole** call site in production code. `services/downloader.py`
re-exports the name (lines 39, 118, in `__all__`) for the backward-compat
facade (§2.2 `C3`), but never calls it. No other call site exists in `src/`.

**Implication for B6:** the guard must not change call-site topology —
B7 adds new call sites; B6 only hardens the existing one. This matches
plan §6.6 acceptance criterion 7.

### 9.3 Measurement 2 — bare `f.unlink()` over `glob("*")`

**Finding:** `_cleanup_segments` still runs a bare `f.unlink()` with **no
`is_file()` guard and no `missing_ok`**.

Confirmed at `segment_downloader.py:443–454`:

```python
def _cleanup_segments(segments_dir: Path) -> None:
    for f in segments_dir.glob("*"):
        f.unlink()                       # <-- no is_file(), no missing_ok
    try:
        segments_dir.rmdir()
    except OSError:
        pass
```

`glob("*")` enumerates every entry — regular files, directories, and
symlinks. On Windows, `f.unlink()` on a directory raises
`PermissionError [WinError 5]`; on POSIX it raises `IsADirectoryError`.
The `rmdir()` at the tail is wrapped in `try/except OSError`, but the
per-entry `unlink()` is not. This is the live `ART-003` defect.

### 9.4 Measurement 3 — `glob("*.ts")` in `_tally_and_merge` includes `batch_*.ts`

**Finding:** The merge-decision count derived from `glob("*.ts")`
**does include `batch_*.ts`** temp files.

Confirmed at `segment_downloader.py:849`:

```python
    downloaded_count = len(list(segments_dir.glob("*.ts")))
```

`glob("*.ts")` matches `00000.ts` and `batch_00000.ts` identically — both
end in `.ts`. The count is then compared at line 864:

```python
    if downloaded_count == len(segments):
```

With N real segments plus M leftover batch temps, `downloaded_count ==
N + M`, which exceeds `len(segments)` → the merge is **skipped** (`return
None` at line 871). This is the stale merge-temps defect: a resumed run
after a failed merge sees leftover temps and never re-merges.

**Additional `glob("*.ts")` occurrences** (all in the same file, all
untouched by this plan's other blocks):

| Line | Context | Includes `batch_*.ts`? |
|---|---|---|
| 151 | `_clear_stale_segments` — `stale_count = len(...)` | Yes |
| 154 | `_clear_stale_segments` — `for stale_file in ...` | Yes |
| 849 | `_tally_and_merge` — `downloaded_count` | Yes |
| 1015 | `_download_segment_concurrent` — progress callback count | Yes |
| 1264 | `_log_preserve_segments` — `working_count` | Yes (intentional; compensating control per plan) |

### 9.5 Measurement 4 — `_clear_stale_segments` misses `NNNNN.ts.tmp`

**Finding:** `_clear_stale_segments` does **not** reconcile the
`NNNNN.ts.tmp` temp files that the two `os.replace` publish sites create.

The temp pattern is `output_path.with_suffix(output_path.suffix + ".tmp")`
at two sites (`segment_downloader.py:204` and `:267`), producing e.g.
`00000.ts.tmp`. This name:

- Does **not** match `glob("*.ts")` (used at lines 151, 154 in
  `_clear_stale_segments`).
- Does **not** match `glob("*")` either — well, it *does* match `glob("*")`
  in `_cleanup_segments`, but `_cleanup_segments` runs only after a
  successful merge, and a `.ts.tmp` left by a crashed segment write is
  never published by `os.replace` so it survives to the next session.
- Is **not** matched by the `f"{i:05d}.ts"` enumeration in
  `_merge_segments_batched` (ffmpeg_utils.py:593, 600).

Additionally, `_clear_stale_segments` has a `.signature` short-circuit
at lines 146–149:

```python
    if signature_file.exists():
        stored = signature_file.read_text(encoding="utf-8").strip()
        if stored == signature:
            return            # <-- short-circuits ALL clearing
```

When the signature matches, the function returns **before** any glob runs
— so even the `*.ts` sweep (which would miss `.ts.tmp` anyway) never
executes. A failed run that wrote a matching `.signature` leaves
everything: segments, batch temps, and `.ts.tmp` residue.

**Test coverage gap:** `grep` over `tests/` for `os.replace` returns
**0 results** — no test exercises the publish path, so no oracle can
observe the `.ts.tmp` residue class.

### 9.6 Measurement 5 — `TestCleanupSegments` does NOT exercise a non-regular entry

**Finding:** `tests/test_hls_downloader.py::TestCleanupSegments`
(lines 210–235) drives `_cleanup_segments` with real files but **never
creates a non-regular entry** (directory or symlink) inside the segments
directory.

The two tests:

1. `test_cleanup_removes_segment_files` — creates `00001.ts`, `00002.ts`.
2. `test_cleanup_handles_non_empty_directory` — creates `00001.ts` +
   `batch.txt`. The "non-empty" refers to the segments_dir itself being
   non-empty, **not** to a subdirectory entry within it.

Neither test places a subdirectory inside `segments_dir`. The
`ART-003` gap — `PermissionError [WinError 5]` on a directory entry — is
**not exercised**. This matches plan §1.1.3's correction ("the real
`ART-003` gap is narrower and stated exactly: no test exercises a
non-regular entry").

### 9.7 Measurement 6 — `TestMergeSegmentsBatched` HAS the failure-preservation test

**Finding:** `tests/test_ffmpeg_utils.py::TestMergeSegmentsBatched`
**does** contain the "batch failure preserves inputs and earlier batch
temps" test, at line 646:

```python
    @pytest.mark.asyncio
    async def test_batch_failure_preserves_inputs_and_earlier_batch_temps(
        self, tmp_path: Path
    ) -> None:
```

This test (NET-001 oracle) asserts that a failure in the second batch:
- Leaves all 250 original segments intact.
- Leaves `batch_00000.ts` (the first batch's temp) intact.
- Removes `batch_00100.ts` (the failed second batch's temp is never
  created).

This is the **D-13 preservation oracle** that P12-B6 acceptance criterion 5
requires to stay green unchanged. The test was not weakened by the
additive merge refactor.

### 9.8 Measurement 7 — deferral comments still point at `ART-004` / `ART-012`

**Finding:** Both in-code deferral comments are **still present** and
**still point at the unfixed findings**.

**`ffmpeg_utils.py`** — `_merge_segments_batched`, lines 616–640:

```python
        # D-13: the input segments are deleted here, and only here, because
        # this is the first point at which the whole merge is known to have
        # succeeded. ...
        #
        # `missing_ok=True` because `returncode == 0` from the final stage
        # attests only to the batch temps ...
        #
        # Deferred (same tag): a graceful stage failure now leaves the temps
        # beside a complete segment set, so the `*.ts` counts in
        # segment_downloader.py also count `batch_*.ts` and a resumed run will
        # not re-trigger the merge. Excluding the merge temps is phase 07's
        # ART-004; this block edits no `*.ts` glob. The compensating control
        # is `_log_preserve_segments`, which now reports the working
        # directory's `*.ts` count and the clear-the-directory action instead
        # of implying the directory is resumable as it stands. The merge peak
        # also moves from 2x to 3x the segment bytes; the sizing belongs to
        # phase 07's ART-012.
```

**`segment_downloader.py`** — `_log_preserve_segments`, lines 1256–1263:

```python
    # D-13: reported on every non-success exit, count 0 included. ...
    # The count below is deliberately labelled: it is every `*.ts` in
    # the working directory, and a failed merge leaves `batch_*.ts` temps
    # there, which a `*.ts` glob cannot distinguish from segments. Excluding
    # them is phase 07's ART-004; until then the count is stated as a
    # working-directory count and the action is to clear the directory.
```

Both notes are intact. The `ART-004` deferral is discharged when B6
narrows the merge-decision count (if `D-4 → (i)`), and both must be
updated per plan §6.6 acceptance criterion 6.

**`_merge_batch_segments`** (lines 396–404) also carries a D-13 note
about additivity, but does **not** mention `ART-004` — only
`NET-001`/`phase 03`. It is unaffected by B6.

### 9.9 `TestPreserveSegmentsReporter` — three pinned tests (verified)

`tests/test_segment_downloader.py::TestPreserveSegmentsReporter`
(lines 419–472) — all three present and unchanged:

1. **`test_reports_zero_count_directory`** (line 422): zero-count dir →
   `logger.info` called once, `working_dir_ts_count == 0`, asserts
   `"not a count of resumable segments"` and `"clear the working directory"`.
2. **`test_count_includes_merge_temps_and_says_so`** (line 441): 2 segments
   + 1 `batch_00000.ts` → `working_dir_ts_count == 3`, names `ART-004` in
   its docstring, asserts `count_note` contains both
   `"including any batch_*.ts"` and `"not a count of resumable segments"`.
3. **`test_missing_directory_emits_nothing`** (line 464): missing dir →
   `logger.info` not called.

If `D-4` resolves to **(ii)** (narrow both counts), test 2 must be
edited and the `count_note` text changes. If **(i)** (narrow only the
merge decision), all three stay green unchanged.

### 9.10 Architectural summary — the cleanup/sweep insertion points

The segment path's filesystem surface and the three B6 entry points:

```
download_hls_with_resume
  └── _run_download_session
        ├── _fetch_playlist_with_retry
        ├── _clear_stale_segments        ← B6: widen sweep to *.ts.tmp
        │     └── (signature short-circuit at .signature)
        └── _process_downloaded_segments
              └── _tally_and_merge
                    ├── glob("*.ts") → downloaded_count  ← B6: exclude batch_*.ts
                    ├── _merge_segments_batched           ← B6: discharge ART-004 note
                    └── if result:                         ← B6: guard exists; B7 adds sites
                          _cleanup_segments               ← B6: add is_file() guard

_log_preserve_segments  ← B6: discharge ART-004 note (compensating control)
_merge_segments_batched ← B6: discharge ART-004 note (deferral comment)
```

`downloader.py` is a re-export facade (§2.2 `C3`); its `__all__`
exports `_cleanup_segments` (line 118) but does not call it — fixes go
in the owning module.

### 9.11 Risks specific to P12-B6

| Risk | Severity | Detail |
|---|---|---|
| `D-4` fork (i vs ii) | Medium | (ii) requires editing a pinned test and changes the `count_note` text; (i) keeps all three `TestPreserveSegmentsReporter` tests green. The decision is a product-call on whether the reporter's number is an inventory or a resume estimate. |
| `.ts.tmp` sweep placement | Medium | (a) extend `_clear_stale_segments` only — leaves residue for a `.signature`-matching failed run; (b) extend `_cleanup_segments` too. Plan §3.4 prefers both. |
| `_cleanup_segments` guard shape | High (I1) | Must be phrased by intent (`is_file()` / `is_dir()`), not by catching `IsADirectoryError`, which is POSIX-only. The existing `except OSError` on `rmdir()` is not a model — it silently swallows `PermissionError` on Windows too. |
| `.signature` short-circuit interaction | Medium | B6 is the only block allowed to change the short-circuit (§4.3 row 8). If B6 extends the sweep without addressing the short-circuit, a matching-signature run still skips clearing entirely. The plan §6.6 names `_clear_stale_segments`'s sweep as in-scope but does not explicitly require touching the short-circuit — the Implementer must decide. |
| Line-count drift on `ffmpeg_utils.py` | Low | 646 on-disk vs. 493 claimed in §2.6. The deferral comments are at different lines than the plan's implied positions, but the symbols are found by name (§2.6 discipline), so no anchor is lost. |

---

## 10. P12-B10 Auditor context (`context_a`)

Live-tree audit of the implementation relevant to `P12-B10` — deduplicate by
**resolved output filename** before dispatch, last occurrence wins, earlier
occurrences skipped and performing no media transfer (`ART-006`, Decision A).
Inspected against the current working tree at task time.

### 10.0 Live-tree baseline state (re-measured; drifts from §2.0)

The plan's §2.0 gates were run against `HEAD = 58bb7ce`. At task time the
committed `HEAD` is **`12af960`** (`fix(security): detect traversal by component, not substring`).
The tree has advanced past the baseline; `P12-B1` is already committed and the
gate figures have moved. `src/` and `tests/` are **clean** in the working tree
(`git status` shows no `M` on any file under `src/` or `tests/`).

**Re-measured standing gates at `12af960`:**

| # | Command | Result at `12af960` | Delta vs §2.0 (`58bb7ce`) |
|---|---|---|---|
| G1 | `uv run pytest tests/ -q -rs` | **1045 passed, 3 skipped, 1 warning** in 56.78s | +293 passed; skip count 3 (unchanged total, **composition changed** — see below) |
| G2 | `uv run ruff check src tests` | `All checks passed!` | unchanged |
| G3 | `uv run ruff format --check src tests` | **`55 files already formatted`** (GREEN) | **was RED** — the pre-existing `tests/test_hls_downloader.py` reformat is **resolved** on this tree, not inherited as red |
| G4 | `uv run mypy src` | `Success: no issues found in 31 source files` | unchanged |
| G5 | `uv run mypy src tests` | **`95 errors in 9 files`** (checked 55) | **was 86 in 8 files** — net +9 errors, +1 file |
| G6 | `uv run ruff check .` | `All checks passed!` | unchanged |

**Skip composition changed (material for B10's own gate accounting).** §2.0
pins the skip floor at 3 and names them as the `D-11` mode oracles (two in
`tests/test_config.py`, one in `tests/test_hls_downloader.py::TestCreateTempCookieFile`).
The **live** three skips are `POSIX-only: killpg` tests —
`tests/test_ffmpeg_utils.py:166`, `tests/test_ffmpeg_utils.py:189`, and
`tests/test_hls_downloader.py:4723`. The `D-11` mode-oracle skip set the plan
was written against is **not present on this tree**. B10's gate check must
re-measure the skip set rather than inherit §7.1's "3 at rest" wording, which
names a specific oracle composition that no longer matches.

**New `G5` error directly relevant to B10's machinery.** `tests/test_batch_downloader.py:901`
— a test helper subclasses a captured class (`class _CountingTrackedSemaphore(original_cls)`)
and mypy reports `Variable "original_cls" is not valid as a type [valid-type]`.
It is in `TestBatchLiveTaskBounding.test_no_half_claimed_batch_permit_after_stop`,
the same file B10 extends. B10 must not increase the `mypy src tests` total
(§7.1 gate lock); its own test additions must add zero `src/` errors and keep
the test-file delta at net-zero or better.

**Consequence for the baseline the plan recorded.** §2.6 asserted "every file
carrying a phase-07 anchor is unchanged except the loader's own files" at
`58bb7ce`. That is **no longer true**: `P12-B1` is committed, so
`utils/security.py::validate_output_path` is changed (substring `".." in
str(path)` → component-wise `".." in path.parts` at lines 56 and 68). `_resolve_output_file`
itself (lines 91–120) is **unchanged**, and `repo_root` is **unchanged** (still
`parent.parent.parent`, still one level too deep — `P12-B2`'s domain). So B10
reads a `validate_output_path` that is already component-wise correct and a
`_resolve_output_file` that is unchanged-from-baseline; the one drift that
matters to B10 is that `repo_root` is still wrong, which only affects the
`warning=False` suppression call site, not the key derivation.

### 10.1 The `download_video` pipeline (`services/downloader.py`)

`download_video` (signature `downloader.py:275`; body `275–360`) is the shared
orchestration entry for both `download` and `batch`. It does **not** accept
pre-extracted data:

```python
async def download_video(                        # downloader.py:275
    url: str,
    quality: QualitySpec,
    output: Path,
    method: DownloadMethod,
    settings: Settings,
    *,
    log_available_qualities: bool = False,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    semaphore: SemaphoreLike | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    output_index: int = 0,
    echo: bool = True,
    title_callback: Callable[[str], None] | None = None,
) -> Path | None:
```

The live pipeline is **extract → title_callback → resolve → dispatch**, in this
order (no pre-pass today):

```python
extractor = VKVideoExtractor(settings=settings, backoff_coordinator=backoff_coordinator)   # 323
video = await extractor.extract_streams(url)                                                # 324  <-- network
if title_callback is not None and video.title:                                              # 326
    title_callback(sanitize_title(video.title))                                             # 327
...
stream = selector.select(video.streams, quality)                                            # 343
output_file = _resolve_output_file(video, output, settings, output_index)                   # 345  <-- KEY
return await perform_download(                                                             # 347
    url,
    str(quality),
    output_file,
    method,
    extractor,
    settings,
    ...
    video_data=video,        # 357
    selected_stream=stream,   # 358
    echo=echo,
)
```

**Key findings from this pipeline:**

1. **Extraction precedes resolution** (line 324 before line 345). The resolved
   filename is not knowable before a network call — `title` and `id` arrive with
   `extract_streams`. This is exactly the `DEF-6` conflict the plan records
   (§1.4, §3.8). It is **live and unsatisfied**, not theoretical.
2. **`download_video` does NOT accept `video_data`/`selected_stream`** — only
   `perform_download` does (params `downloader.py:141–142`; used at `195–197`:
   `if video_data is not None and selected_stream is not None: streams =
   video_data.streams; m3u8_url = str(selected_stream.url)`). So `download_video`
   **always re-extracts**. The plan's §2.2 `C10` ("`perform_download` already
   accepts pre-extracted `video_data` and `selected_stream` precisely so
   extraction can be skipped") is accurate **as far as it goes** — but the
   contract lives on `perform_download`, not on the `download_video` entry point
   the batch calls. A two-phase pre-pass that "hands the buffered extraction
   forward" (§3.8 line 560) is **not currently possible** through `download_video`;
   it requires `download_video` to gain the params and to skip its own extract.
   Plan row 18b confirms `download_video` is B10's sole writer, so that param
   addition is **in scope**, not out of scope.
3. `output_index` is threaded straight through to `_resolve_output_file(video,
   output, settings, output_index)` (line 345). It is the **only** input that
   can disambiguate two same-`id` entries without a title (fallback
   `f"{index}_{video.id}.mp4"`, `security.py:118`).

### 10.2 The `batch` URL reader and the single-URL `download` path (`src/vkdownloader/cli.py`)

The `batch` command (`cli.py:475`, `batch_download`) reads and validates URLs
into `valid_urls` / `skipped_count` **only** for malformed input — it does **not**
dedup for collisions here:

```python
valid_urls: list[str] = []                                    # 520
skipped_count = 0                                             # 521
...
raw_urls = urls_file.read_text()                              # 534
for line in raw_urls.splitlines():                            # 540
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    if not is_valid_video_url(stripped):                      # 544  <-- format check only
        logger.warning("invalid_url_in_batch", url=sanitize_url_for_log(stripped))
        skipped_count += 1
        continue
    valid_urls.append(stripped)
...
exit_code = asyncio.run(
    run_batch(valid_urls, quality_spec, DownloadMethod(method), settings, output, skipped_count)  # 560-569
)
```

`is_valid_video_url` validates the **VK video URL shape** (regex), not uniqueness.
`skipped_count` here is the **invalid-URL count**, and it is passed through to
`run_batch` → `_run_batch_with_progress` → `_print_batch_summary(..., skipped_count)`,
which renders it as the **first** "Skipped (invalid URLs)" line
(`batch_downloader.py:507-508`). A **second** "Skipped (duplicates)" line is
already rendered for `ProgressStatus.SKIPPED` entries (`batch_downloader.py:509-510`)
— today that bucket is populated only by the exact-URL `seen_urls` check, not by
filename-collision skips. This second line is the reporting spine B10 must wire
a filename-dedup skip into; it does **not** need a new line of its own.

**Single-URL `download` vs `batch` — the difference that matters to B10:**

| Aspect | `download` (`cli.py:394-401`) | `batch` (`run_batch` → `_run_batch_with_progress`) |
|---|---|---|
| Entry call | `download_video(url, quality_spec, output, method, settings, log_available_qualities=True)` | `_download_single(url, ..., DownloadContext(index=i, ...))` → `download_video(...)` |
| `output_index` | default `0` (not passed) | `i` = enumerate position (line 241, 345) |
| `semaphore` | not passed (None) | shared `asyncio.Semaphore(max_concurrent_downloads)` via `_TrackedSemaphore` |
| `title_callback` / `progress_callback` | not passed | `_on_title`/`_on_progress` wired to `reporter` |
| Reporter | none | `RichProgressReporter` per run |
| Dedup | **none** (one URL) | `seen_urls` exact-URL dedup (10.4) |
| Post-result echo | `f"Downloaded: {result}"` / `"Download failed"` | `_print_batch_summary` four-bucket accounting |
| Cancellation | `KeyboardInterrupt` re-raised → exit 130 | `ProgressStatus.CANCELLED` via shutdown Event → exit 130 |

**B10 constraint:** §6.10 acceptance criterion 6 — "The single-URL `download`
command is unchanged and does not pay for the registry." The reader has
**no** registry and must stay that way; the pre-pass lives in the batch path
only.

### 10.3 `_resolve_output_file` — the dedup key producer (`utils/security.py:91-120`)

Confirmed **unchanged** from the plan's description (last commit `e59523c` for
the function; B1 only touched `validate_output_path`):

```python
def _resolve_output_file(video, output, settings, index) -> Path:        # 91
    output_path = output if str(output) != "." else settings.download_dir
    output_path = Path(output_path).resolve()
    validated_output = validate_output_path(output_path, warning=False)  # 111
    validated_output.mkdir(parents=True, exist_ok=True)                  # 112  <-- C9 side effect
    safe_title = sanitize_title(video.title) if video.title else None
    if safe_title:
        output_file = validated_output / f"{safe_title}_{video.id}.mp4"  # 116
    else:
        output_file = validated_output / f"{index}_{video.id}.mp4"      # 118
    return output_file
```

Three facts the key depends on:

1. **The key is the resolved `Path`**, returned (not the composed string).
   `safe_title` is already sanitised by `sanitize_title` (post-`B3`/`B4`/`B5`
   normalisation), so two titles that sanitise to the same component — e.g.
   `a?b` and `a:b` (both → `a_b`) — yield the same filename **here**. B10's
   "sanitised-title collision deduped" oracle (§6.10 criterion 4 direction 1) is
   therefore meaningful **only because B3/B4/B5 have landed**; `sanitize_title`
   on this tree already replaces the nine illegal chars (`security.py:31`) but
   the control-char and device-name halves are still pinned at plan baseline.
2. **`mkdir` runs unconditionally** (line 112) — this is `C9`. A pre-pass that
   calls `_resolve_output_file` for every entry (including a skipped one)
   **creates the output directory for skipped entries**. The directory is
   shared by every entry in the batch, so the side effect is harmless-but-
   observable and B10 must assert it rather than assume it (§6.10 criterion 9).
3. **`warning=False`** suppresses the `ART-009` repo-root warning at this call
   site. Under Decision A the pre-pass resolves every entry, so this is the site
   the plan's new `B10 → B2` edge is about (§4.1): if `B2` makes the warning fire,
   it should do so through the pre-pass, not be re-added at a call site B10 is
   restructuring.

### 10.4 The fan-out, `output_index`, and the reporting path (`services/batch_downloader.py`)

`_run_batch_with_progress` (`batch_downloader.py:294`) is the fan-out. It
already contains a **Tier 1 exact-URL dedup** on `seen_urls` — this is **not**
the filename-based dedup Decision A wants, and it sits *inside* the fill-phase
loop rather than as a separate resolution phase:

```python
seen_urls: set[str] = set()                              # 347  <-- URL-keyed, not filename-keyed
urls_left = iter(enumerate(urls))                         # 348
...
for i, url in urls_left:                                  # 374
    # Tier 1 dedup (DEC-W R1): exact-URL duplicates are skipped
    # before any network call ...                         # 375-379
    if url in seen_urls:                                  # 380  <-- URL match, not path match
        logger.info("duplicate_url_skipped", url=_strip_auth_params(url), index=i)
        reporter.start_task(i)
        reporter.finish_task(i, ProgressStatus.SKIPPED)
        by_index[i] = (url, "", ProgressStatus.SKIPPED.value)
        continue
    seen_urls.add(url)
    if len(pending) >= settings.max_concurrent_downloads: # 387  <-- bounded pump
        ...
    pending[
        asyncio.create_task(                              # 391  <-- task created per non-dup URL
            _download_single(url, quality, output, method, settings,
                             DownloadContext(index=i, ...))
        )
    ] = i
```

**What this means for B10:**

- The existing dedup is keyed on the **raw URL string**. Two *different* URLs
  that resolve to the *same* filename (e.g. `a?b` and `a:b` with the same
  `id`, or a re-listing) are **not** deduped — each becomes its own task and
  one overwrites the other at `.part`/`os.replace` time. This is the `ART-006`
  gap Decision A closes.
- There is **no separate resolution phase before the fan-out**. Option (b) —
  the chosen shape — must insert one: extract + resolve every entry, build a
  filename→index registry, drop earlier collisions to `ProgressStatus.SKIPPED`
  *before* `asyncio.create_task` runs, then fan out survivors only.
- `output_index` is threaded as the enumerate position: `i` (`for i, url in
  urls_left`) → `DownloadContext(index=i)` (line 400) → `context.index` in
  `_download_single` (line 182) → `download_video(output_index=index, ...)`
  (line 241) → `_resolve_output_file(video, output, settings, output_index)`
  (line 345). So `index` is a **positional** index, not a survivor count. After
  B10 drops collisions, the survivors keep their original enumerate indices (so
  `by_index` ordering at line 420 and the `results = [by_index[i] for i in
  range(len(urls))]` restoration still work); only dispatched tasks are created.

**`_print_batch_summary` (`batch_downloader.py:457-545`)** — the reporting
spine B10 reuses, shape:
`_print_batch_summary(results: list[tuple[str,str,str]], peak_concurrent_videos: int, skipped_count: int = 0) -> int`

- Per-line: `f"{url}: {status}"` + optional ` -> {output_path}` (line 485).
- Four explicit buckets, **no subtraction rule** (lines 491-503):
  `successful`, `cancelled`, `skipped` (counts `ProgressStatus.SKIPPED.value`),
  `failed` (every status not in SUCCESS/CANCELLED/SKIPPED). This existing
  four-bucket logic is what stops a dedup skip being mis-counted as a failure
  (the comment at 489-490 names `OUT-009` as the regression it prevents).
- Rendered lines: "Skipped (invalid URLs): {skipped_count}" (507-508, only if
  `skipped_count > 0`) and "Skipped (duplicates): {skipped}" (509-510, only if
  `skipped > 0`). A filename-dedup skip must join the **(duplicates)** bucket,
  not the invalid-URL one — §6.10 criterion 3's "distinct summary line."
- Exit code: `130` if any cancelled (wins), else `1` if `failed > 0`, else `0`
  (line 542, 545). A dedup skip is neither success nor failure, so it leaves
  the code at `0` on a clean batch — matching `TestBatchDedupSkip` (10.8).
- `skipped_count` (invalid-URL count from the reader) is the **third** arg,
  separate from the per-item `SKIPPED` count; B10 must keep these two counts
  separate (plan row 18/§5.6 T12: "the invalid-URL `skipped_count` path must
  stay green unchanged; the dedup skip gets its own line").

### 10.5 `ProgressStatus.SKIPPED` (`models/enums.py`)

Exits and exists. Members (`enums.py:82-105`):

```
IN_PROGRESS = "in_progress"      # 97  -- the only non-terminal state
SUCCESS     = "success"          # 99
FAILED      = "failed"           # 101
SKIPPED     = "skipped"          # 103  -- produced by the batch-level dedup
CANCELLED   = "cancelled"        # 105
```

`TERMINAL_STATUSES` (`112-114`) is derived: `frozenset(member for member in
ProgressStatus if member != ProgressStatus.IN_PROGRESS)`. So `SKIPPED` is
already a terminal status wired into the progress display's `render`/status
column (`tests/test_progress_display.py:92` maps `ProgressStatus.SKIPPED` →
`⊘`), and `_to_progress_status` (`batch_downloader.py:107-124`) maps a
`"skipped"` literal to it. B10 consumes it; it does **not** define it (§6.10
"Do not touch … `ProgressStatus.SKIPPED` — it already exists").

**Stale docstring caveat.** `ProgressStatus`'s own docstring (line 90-91) says
`SKIPPED` is "produced by the batch-level dedup check in `_run_batch_with_progress`
when an **exact-URL duplicate** is detected before any network call." After B10,
`SKIPPED` is **also** produced by filename-collision dedup. That sentence must be
updated by B10 (it lives in `enums.py`, which B10 does not otherwise touch —
flag it as a one-line docstring drift, not a code drift).

### 10.6 `_map_exception_to_status` (`exceptions.py:216-229`)

Exists, is **legacy**, and has **zero production call sites** — a dedup skip is
not an exception and must not route through it:

```python
def _map_exception_to_status(exc: Exception) -> str:          # 216
    for exc_type, handler in _EXCEPTION_STATUS_HANDLERS.items():  # 226
        if isinstance(exc, exc_type):
            return handler(exc)
    return f"unexpected_error: {type(exc).__name__}"            # 229
```

`_EXCEPTION_STATUS_HANDLERS` (`240-247`) maps seven domain types:
`ExtractionError→"extraction_error: {e}"`, `DownloadError→"download_error: {e}"`,
`InvalidVideoUrlError→"invalid_url: {e}"`, `QualityNotAvailableError→_quality_not_available_status`,
`QualityParseError→"invalid_quality: {e.quality}"`, `VideoNotFoundError→"video_not_found: {e}"`,
and a `VKDownloadError` fallback → `"download_error: {e}"`.

**Two auditor observations:**

1. **Dead in production.** `grep` shows the only `src/` references are the
   definition (`exceptions.py:216`), the module docstring (`exceptions.py:6-8`),
   and a comment in `batch_downloader.py:282` ("the documented replacement for
   the legacy `_map_exception_to_status` helper"). The live `_download_single`
   (`160-291`) uses `e.status_label()` for the four domain except arms (lines
   261-277) and `f"unexpected_error: {type(e).__name__}"` for the catch-all
   (line 289). `README.md:157` and `docs/error-handling-logging-research-2025-2026.md`
   both record the shim as backward-compat only. The 14-code-quality plan's
   `B1` (already filed in `.ai/plans/14-code-quality-audit-fixes_fix.md`) is
   slated to delete it. B10 must **not** touch it; the plan §6.10 "Do not touch"
   and §3.8 both say so.
2. **Format drift vs. the docstring.** The docstring (`47-53`) claims return
   examples `"no_streams: <message>"`, `"video_not_found: <message>"`,
   `"download_error: <message>"` — but the live handlers return
   `"extraction_error: {e}"` etc. (with the message), and `status_label()`
   returns the **bare** `"extraction_error"`/`"video_not_found"` (no message).
   This is out of B10's scope, but the test suite `TestMapExceptionToStatus`
   (`tests/test_exceptions.py:14-76`, `201-218`) pins the `: {e}` shape — so if
   any future B10 test accidentally asserts against `_map_exception_to_status`'s
   output it would be asserting a dead path. The B10 oracle should assert
   `ProgressStatus.SKIPPED` and the summary's "Skipped (duplicates)" count, not
   any exception→label mapping.

### 10.7 `tests/test_cli.py::TestBatchCommand` — what exists, what's absent

`TestBatchCommand` (`tests/test_cli.py:277-1100`) exercises the **reader and the
summary renderer** end-to-end through `CliRunner`, but **does not test
duplicates of any kind** — neither exact-URL nor filename-collision:

- `test_batch_empty_file` / `test_batch_file_with_comments_only` /
  `test_batch_file_with_whitespace_only` — empty/comment/whitespace reader.
- `test_batch_statistics_summary` — two URLs, one fails with `VideoNotFoundError`;
  asserts "Failed URLs:" + "video_not_found" appear (`701-774`).
- `test_batch_all_success_exits_zero`, `test_batch_skip_invalid_urls`
  (the `skipped_count` / "Skipped (invalid URLs)" line, `455-498`),
  `test_batch_summary_total_line_names_videos_and_counts_each_video` (`B8` oracle).
- `test_batch_start_finish_task_per_url` — start/finish_task accounting.
- `test_batch_non_tty_reporter_logs_progress`, `test_batch_real_reporter_renders_concurrent_progress`.
- `test_batch_status_lines_success_and_failed`, `test_batch_cancelled_produces_cancelled_status`.
- `test_batch_echo_suppressed_when_reporter_enabled` / `test_batch_echo_not_suppressed_when_reporter_disabled` (echo wiring).
- `test_batch_title_callback_reaches_reporter` (title_callback → `reporter.set_title`).
- `test_batch_old_progress_polling_removed`, `test_batch_no_escape_codes_under_cli_runner`,
  `test_batch_reporter_started_and_stopped`.

**Gap:** none of these feed two URLs that resolve to one filename, and none
assert that `download_video` is called once for a duplicate. §2.5 already says
"this is the whole oracle set is new"; the live file confirms it —
`TestBatchCommand` stays silent on duplicates. B10's §6.10 criterion 1 (exactly
one dispatch, the last) and criterion 2 (no media transfer for the skipped
entry) have **no existing home** and must be authored here (per plan row 20b,
B10's sole test anchor). The class's existing `perform_download` mock shape
(`MagicMock(id=..., title="Test Title", streams=[MagicMock(quality="720")]`)
means a filename-collision oracle must make the two URLs yield **equal**
`sanitized_title` + equal `id` — e.g. `?`/`/`-differing titles, or the same
title — and the B10 oracle should reuse that fixture shape, not invent a new
reader mock.

### 10.8 `tests/test_batch_downloader.py` and the bounded-fan-out classes — location

`TestBatchDownloaderSemaphore` (`:143`), `TestBatchCancellationReporting`
(`:386`), `TestBatchCancelationPropagates` (`:624`), `TestCorrelationInheritance`
(`:674`), `TestBatchLiveTaskBounding` (`:768`), `TestBatchDedupSkip` (`:939`),
`TestBatchSummarySkippedAggregation` (`:1033`) — all in
**`tests/test_batch_downloader.py`** (1069 lines).

**The three bounded-fan-out classes are NOT in this file.** They are in
**`tests/test_segment_downloader.py`** (`grep` confirms):
- `TestSegmentFanoutCompletion` (`:1262`) — CON-006/007/008:
  `_await_and_cancel` distinguishes `NOTHING_TO_DO` (empty task list),
  `COMPLETED` (all settled), and re-raised `CancelledError`; asserts a
  non-cancellation exception settles every sibling before propagating.
- `TestSegmentFanoutBoundedProduction` (`:1436`) — CON-003:
  `_process_downloaded_segments` keeps live `_download_segment_concurrent`
  tasks ≤ `max_concurrent_segments`; asserts all 200 indices reach the merge,
  and stop leaves no orphans / clean semaphore.
- `TestConnectorCeilingsFollowTheSetting` (`:1640`) — the connector ceiling
  tracks the configured limit.

These assert the **segment-layer** fan-out, which B10 must leave untouched
(§6.10 criterion 7: "stay green unchanged — this block changes **what** is
dispatched, not **how** it is bounded"). The `TestBatchLiveTaskBounding` class
in `test_batch_downloader.py` (:768) covers the **batch-layer** ceiling
(max concurrent *videos*, via `asyncio.all_tasks` filtered on
`get_coro().__qualname__ == "_download_single"`).

**`TestBatchDedupSkip` (:939) — the one existing dedup oracle — asserts
exact-URL dedup only:**

- `test_duplicate_url_marked_skipped_not_downloaded` (`:943`): feeds
  `[first_url, first_url, second_url]`; asserts `download_video` called
  **once** per unique URL (`len(download_calls) == 2`), `finish_task(1,
  SKIPPED)` was called on the **reporter** (mocked here), and `results[1] ==
  SKIPPED`. This is **Tier 1 URL dedup**, the contract B10 *augments*, not
  replaces.
- `test_duplicate_skip_summary_reports_skipped_not_failed` (`:995`): asserts
  "Total videos: 2", "Successful: 1", "Failed: 0", "Skipped (duplicates): 1",
  `exit_code == 0`.
- `TestBatchSummarySkippedAggregation` (`:1033`): feeds hand-built `results`
  with a `SKIPPED` entry and asserts it is counted under "Skipped (duplicates)",
  not "Failed" / "Failed URLs:" — independent of any dedup logic.

**Critical nuance for B10:** these two `TestBatchDedupSkip` tests patch
`RichProgressReporter` (so no real rendering) and stub `download_video` — they
do **not** assert that no `_resolve_output_file`/`extract_streams`/media-
transfer ran for the skipped entry. B10's filename-dedup oracle cannot reuse
them as-is; it needs the **no-transfer not-called** assertions (§6.10
criterion 2) layered on top.

### 10.9 Answers to the key questions

- **Is there any existing dedup mechanism?** Yes — `seen_urls: set[str]` in
  `_run_batch_with_progress` (`batch_downloader.py:347,380-386`), keyed on the
  **exact-URL string**, running *inside* the fill-phase loop (Tier 1, DEC-W R1).
  It dedups on URL, not on resolved output filename, and it is **not** a
  pre-dispatch resolution phase. There is **no** filename-keyed registry
  anywhere in `src/` or `tests/`. This is precisely the gap Decision A closes
  (§1.3: "A name-level mutex for within-batch collisions — structurally
  impossible after Decision A").
- **Does `download_video` accept `video_data`/`selected_stream`?** No. Only
  `perform_download` does (`downloader.py:141-142, 195-197`); `download_video`
  always calls `extract_streams` (`275-324`), then passes the result forward to
  `perform_download` as `video_data=video, selected_stream=stream`. So
  `C10` is true of `perform_download` but **not exposed through the batch
  entry point**. Realising §3.8's "pre-pass hands the buffered extraction
  forward" requires `download_video` to gain those params and skip its own
  extract (plan row 18b: B10 is `download_video`'s sole writer — in scope).
- **How is `output_index` threaded?** `urls` enumerated → `i` →
  `DownloadContext(index=i)` (line 400) → `context.index` (182) →
  `download_video(output_index=index, ...)` (241) →
  `_resolve_output_file(video, output, settings, output_index)` (345). Index is
  positional, survives skip-removal (survivors keep original enumerate index so
  `by_index`/`results` restoration at 420 stays correct).
- **What is `_print_batch_summary`'s shape?**
  `_print_batch_summary(results: list[tuple[str,str,str]], peak_concurrent_videos: int, skipped_count: int = 0) -> int`
  (`:457-461`). Renders per-line results, then four explicit buckets (no
  subtraction rule — `:491-503`), then "Skipped (invalid URLs): {skipped_count}"
  (`:507-508`) and conditionally "Skipped (duplicates): {skipped}" (`:509-510`).
  Exit `130` if any cancelled (wins), else `1` if failed>0, else `0`.
- **How does single-URL `download` differ from `batch`?** `download` calls
  `download_video` directly with `output_index=0` (default), no semaphore, no
  reporter, no `title_callback`/`progress_callback`, and no dedup (single URL);
  it echoes "Downloaded: …" / "Download failed" and maps
  `InvalidVideoUrlError`/`KeyboardInterrupt` itself. `batch` routes through
  `run_batch` → `_run_batch_with_progress`, which adds the shared semaphore,
  the bounded pump, the reporter, the title/progress closures, the `output_index=i`
  threading, and the `seen_urls` Tier 1 dedup. B10's pre-pass is a batch-only
  addition; `download` must not gain a registry (§6.10 criterion 6).

### 10.10 What the option-(b) pre-pass must add (and the conflicts it inherits)

A separate resolution phase in `batch_downloader` before fan-out requires a
component that today **does not exist** as a unit. Concretely, B10 must
introduce (in `batch_downloader.py`, per plan row 18c "sole owner"):

1. A per-batch resolution routine that, for each URL, calls extraction to
   obtain `title`+`id`, then `_resolve_output_file(video, output, settings,
   output_index)` to obtain the key — **in order to know the key at all**
   (the `DEF-6` conflict, live at `downloader.py:324` then `:345`).
2. A `dict[resolved_path → index]` registry with **last-wins** semantics
   (Decision A). Collisions are terminalised as `(url, "", SKIPPED.value)`
   via `finish_task` (the `[⊘]` marker, already wired at
   `progress_display.py:92` / `ProgressStatus.SKIPPED`) **before** any
   `asyncio.create_task` — so the "one dispatch and it is the last" and
   "no media transfer for skipped" oracles (§6.10 criteria 1-2) hold.
3. A dispatch that calls `download_video` with the **same** `output_index` the
   registry used, so the survivor's resolved path matches the key the dedup
   ran on. Today the only `download_video` caller in the batch path
   (`_download_single`, line 232) does **not** accept pre-extracted data, so
   either (a) `download_video` grows `video_data`/`selected_stream` params and
   skips its own `extract_streams` (realising `C10`'s stated intent), or (b)
   `_download_single` is rewired to call `perform_download` directly with the
   buffered extraction. The plan prefers "hand the buffered extraction forward,
   not re-fetch" (§3.8 line 560), which **requires** the `download_video`
   param addition — B10 owns that signature change (row 18b).
4. The `mkdir` side effect (`C9`, `security.py:112`) to be asserted, not
   assumed: every resolved entry — including a skipped one — leaves the directory
   present. Harmless (shared dir), but `FileExistsError [WinError 183]` is the
   named B10/I7 risk (§5.1 `I7`) when the target exists as a file.

**Conflicts B10 inherits unchanged:**

- **`DEF-6` (no-network clause vs. key derivation):** the resolved filename
  needs `title`+`id` from `extract_streams`; a literal "no network at all" for a
  skipped entry is unsatisfiable. The plan resolves this to "no **media
  transfer** for a skipped entry" and escalates the tension to the Product Owner
  (§1.4 `DEF-6`, §3.8). B10 delivers the achievable form and must record, in the
  commit body, any narrowing of the no-network clause (§6.10 deliverable).
- **`output_index` vs. filename key:** the key is the resolved `Path`, but the
  fallback name embeds `output_index`. Two same-`id` entries with different
  indices and no title are **not** deduped (they get different names) —
  §6.10 criterion 4 direction 2 depends on this. The pre-pass must key on the
  resolved path, not on `(title, id, index)`.
- **`B10 → B2` edge:** the pre-pass resolves every entry (Decision A), and
  Decision B makes the suppressed warning at `validate_output_path(...,
  warning=False)` (10.3 line 111) the loader path's only user-facing guard.
  `B2` should let the warning fire through the pre-pass, not be re-added at a
  call site B10 is restructuring (§4.1, row 3).
- **`G3` and `G5` are no longer stable baselines:** at `12af960` `G3` is
  **green** (the `test_hls_downloader.py` reformat is resolved) and `G5` is
  **95** (was 86). B10 must re-measure these at execution time, not inherit
  §2.0's figures, and must keep the skip count at the live floor of 3
  (composition: the three `POSIX-only: killpg` skips, **not** the `D-11` oracles
   the plan names).

---

## 11. Implementation task: P12-B10 — dedup by resolved output filename, before dispatch

**Status:** DONE — implemented, tested (1054 passed, 3 skipped), committed as `1d09009`.
**Task file:** `.ai/tasks/p12-b10-dedup-by-resolved-output-filename.yaml`

### 11.1 Semantic scope

`download_video` in `services/downloader.py` — the extract → `title_callback` → `_resolve_output_file` → `perform_download` pipeline. Gained `video_data` / `selected_stream` keyword-only params so the pre-pass can hand the buffered extraction forward rather than re-fetching (§2.2 `C10`; plan row 18b confirms B10 is `download_video`'s sole writer).

`_run_batch_with_progress` in `services/batch_downloader.py` — the fan-out. The pre-pass (option (b), PoO decision) is inserted here, before the fill-phase loop: extract + resolve every URL, build a `dict[resolved_path → index]` registry with last-wins semantics, terminalise losers as `ProgressStatus.SKIPPED` before any `asyncio.create_task`, then dispatch survivors only. `DownloadContext` gains `video_data` / `selected_stream` fields; `_download_single` forwards them into `download_video`.

`_resolve_output_file` in `utils/security.py` — **read only**, the key producer. Not modified (Decision A disambiguates no names, so no suffix is added). Its `mkdir(parents=True, exist_ok=True)` side effect (C9) is asserted, not assumed.

`ProgressStatus.SKIPPED` in `models/enums.py` — **the member is not redefined** (it already exists, already wired into `progress_display.py:92` → `⊘`). Only its docstring is updated to mention the filename-collision tier alongside the existing exact-URL tier.

`_print_batch_summary` in `services/batch_downloader.py` — **no new reporting channel**. The existing four-bucket accounting already isolates `SKIPPED` into its own bucket and renders "Skipped (duplicates): {count}" as a distinct line from "Skipped (invalid URLs): {skipped_count}". The filename-dedup skip joins the existing duplicates bucket; it does not get a new summary line.

`_map_exception_to_status` in `exceptions.py:216` — **not touched**. A dedup skip is not an exception.

The single-URL `download` command in `src/vkdownloader/cli.py` (`download()`, lines 394–401) — **not modified**. It calls `download_video` directly with `output_index=0`, no semaphore, no reporter, no dedup. B10's pre-pass is batch-only.

### 11.2 Implementation sequence

Five phases:

1. **Phase 1 — `download_video` signature.** Add `video_data: VideoWithStreams | None = None` and `selected_stream: Stream | None = None` as keyword-only params. When both are provided, skip `extract_streams` and use the pre-extracted data directly (mirroring `perform_download`'s existing guard at `downloader.py:195`). The `title_callback` still fires with `sanitize_title(video_data.title)`. Update the docstring.

2. **Phase 2 — pre-pass.** Insert a resolution phase in `_run_batch_with_progress` before the fill-phase loop. For each URL, call `extract_streams` to get `title`+`id`, then `_resolve_output_file` to get the resolved `Path`. Build `dict[Path, int]` with last-wins (later index overwrites). Terminalise losers into `by_index` as `(url, "", ProgressStatus.SKIPPED.value)` via `reporter.start_task(i)` + `reporter.finish_task(i, SKIPPED)` — **before** any `asyncio.create_task`. Survivors carry their `video_data` and `selected_stream` forward.

3. **Phase 3 — dispatch wiring.** Add `video_data` and `selected_stream` to `DownloadContext`. Thread them from the pre-pass into `_download_single` → `download_video(...)`. The `output_index` passed to `download_video` must match the index the pre-pass used for resolution. Survivors keep their original enumerate indices so `results = [by_index[i] for i in range(len(urls))]` at `batch_downloader.py:420` still restores ordering.

4. **Phase 4 — reporting.** Update `ProgressStatus.SKIPPED`'s docstring (enums.py) to mention the filename-collision tier. Verify `_print_batch_summary`'s four-bucket accounting already isolates `SKIPPED` and renders the distinct "Skipped (duplicates)" line — no code change needed there, just verification.

5. **Phase 5 — tests.** Add the oracle set (§6.10 criteria 1–9) to `tests/test_cli.py::TestBatchCommand` and extend `tests/test_batch_downloader.py::TestBatchDedupSkip` with no-transfer assertions. One single-URL regression test pins "no registry on the single-URL path."

### 11.3 Architectural constraints

- **Two-tier dedup, not one.** Tier 1 (`seen_urls: set[str]`, the existing exact-URL dedup at `batch_downloader.py:347`) is **kept unchanged**. Tier 2 (resolved-filename) is **added** as the pre-pass. Do not remove Tier 1 — it prevents redundant extraction calls for true duplicate URLs and is tested by `TestBatchDedupSkip`'s existing tests.
- **Batch-only pre-pass.** The pre-pass lives in `_run_batch_with_progress` (called only from `run_batch`). The single-URL `download` command does not call it and does not carry a registry.
- **Last-wins.** The registry is `dict[Path, int]`. When a collision is detected (path already in the dict), the earlier entry (the current registry value) is terminalised as `SKIPPED`; the dict entry is overwritten with the new index. Survivors dispatch exactly once; the survivor is always the last occurrence.
- **No media transfer for skipped.** A skipped entry must not trigger any `asyncio.create_task`, no `download_video` dispatch, no semaphore permit, no yt-dlp subprocess, no segment fetch, no `.part` file, no working tree. The pre-pass terminalises losers **before** task creation — by structure, not by accident.
- **Key is resolved path, not `(title, id)`.** Different titles can sanitise to the same filename (`sanitize_title("a?b")` and `sanitize_title("a:b")` both yield `a_b`); `output_index` discriminates same-`id` entries with different indices and no title. The resolved `Path` gets both directions right.
- **`output_index` is positional, not survivor-count.** Survivors keep their original enumerate indices; `by_index` ordering and the `results` restoration at line 420 are unchanged.
- **No name-level mutex.** Structurally impossible after dedup-before-dispatch (§3.8, §5.4 `C3`). No lock file, no lock primitive. The cross-run case is a recorded residual (§5.7 item 4).
- **`mkdir` side effect asserted.** `_resolve_output_file` calls `mkdir(parents=True, exist_ok=True)` for every entry (C9). A skipped entry's directory is still created. The directory is shared by every entry, so this is harmless-but-observable and must be asserted in a test.
- **`ProgressStatus.SKIPPED` already exists.** It is used, not defined. The enum member itself is not redefined. Only its docstring changes.
- **No new reporting channel.** `_map_exception_to_status` is not the vehicle (a dedup skip is not an exception). No new exception-to-status mapping is added.

### 11.4 Required tests — the 9 acceptance criteria mapped

| §3.8 criterion | Test method | Target class | What it asserts |
|---|---|---|---|
| 1. Two entries → one dispatch, it is the last | `test_dedup_filename_collision_dispatches_only_last` | `TestBatchCommand` | Exactly one `download_video` call; the dispatched URL is the **last** occurrence (asserted by identity, not just count) |
| 2. Skipped entry: no media transfer | `test_dedup_filename_collision_skipped_entry_no_transfer` | `TestBatchCommand` | Patch `download_video`/`perform_download`/subprocess/segment fetch/mkdir; assert all `not_called` for the skipped index |
| 3. Visible at both levels | `test_dedup_filename_collision_visible_in_results_and_summary` | `TestBatchCommand` | `ProgressStatus.SKIPPED` in `results` for the skipped index AND a "Skipped (duplicates):" line distinct from "Skipped (invalid URLs):" in captured output |
| 4a. Key is resolved path — sanitised-title collision | `test_dedup_key_sanitised_title_collision_deduped` | `TestBatchCommand` | Two URLs with different titles that sanitise to one filename (e.g. `"Title?A"` and `"Title:A"`, same id) ARE deduped — exactly one dispatch |
| 4b. Key is resolved path — same id, different index, no title | `test_dedup_key_same_id_different_index_not_deduped` | `TestBatchCommand` | Two entries with same id, different `output_index`, and no title are NOT deduped — both dispatch, two distinct output paths |
| 5. Idempotence | `test_dedup_filename_collision_idempotent_on_rerun` | `TestBatchCommand` | Same URL file run into the same directory twice produces the same skip pattern and the same survivor |
| 6. Single-URL unchanged | `test_single_url_download_no_registry` | `TestBatchCommand` | Single-URL `download` produces no `SKIPPED` status and calls `download_video` exactly once |
| 7. Bounded fan-out unchanged | (existing) | `TestBatchDownloaderSemaphore`, `TestBatchLiveTaskBounding`, `TestSegmentFanoutCompletion`, `TestSegmentFanoutBoundedProduction`, `TestConnectorCeilingsFollowTheSetting` | Must pass **unchanged** — B10 changes what is dispatched, not how it is bounded |
| 8. `mkdir` side effect | `test_dedup_filename_collision_mkdir_side_effect` | `TestBatchCommand` | The output directory exists for a skipped entry (C9); assert it is the shared batch directory |
| 9. Gate accounting | standing gate §7.1 | all | G1/G2/G4/G6 exit 0, G5 non-increasing, G3 unchanged from green-at-12af960, skip count 3 at rest (4 inside B10's commit) |

**Extensions to `TestBatchDedupSkip`** (in `tests/test_batch_downloader.py`):

| Test | What it asserts |
|---|---|
| (new) `test_filename_dedup_no_extract_no_download_for_skipped` | Two entries resolving to the same path: patch `VKVideoExtractor.extract_streams` and `perform_download`; assert **neither** is called for the skipped entry |
| (new) `test_filename_dedup_mkdir_side_effect` | The output directory is created for a skipped entry (C9) |

**Existing tests must pass unchanged:** `TestBatchDedupSkip`'s two existing tests (`test_duplicate_url_marked_skipped_not_downloaded`, `test_duplicate_skip_summary_reports_skipped_not_failed`), `TestBatchSummarySkippedAggregation::test_skipped_entry_counted_as_skipped_not_as_failed`, `TestBatchDownloaderSemaphore`, `TestBatchLiveTaskBounding`.

### 11.5 Honest judgement

- **Pre-pass shape (option (b)).** PoO decision: option (b) — a separate resolution phase in `batch_downloader` before the fan-out. The criterion was whether the batch's progress display stays meaningful during a long batch (§3.8 alternatives). Under (b), the screen shows resolution for all N then downloads; under (a) they interleave. If Decision A's no-network clause is read strictly, (b) is forced because (a) extracts every entry regardless. The `download_video` param addition (phase 1) realises `C10`'s stated intent: "hand the buffered extraction forward, not re-fetch."
- **No-network clause vs. key derivation (DEF-6).** The resolved filename needs `title` and `id` from `extract_streams` (`downloader.py:324`), which is a network call. A literal "no network at all" for a skipped entry is unsatisfiable at this key. The achievable form — no **media transfer** — is delivered and the gap is recorded as `DEF-6`. The commit body must state this narrowing and why.
- **`mkdir` side effect (I7).** `_resolve_output_file`'s `mkdir` runs for every resolved entry, including a skipped one (`C9`). Harmless because the directory is shared; `FileExistsError [WinError 183]` is the named risk when the target exists as a file — out of scope (Decision B: warn only, no refusal) but must be documented in the commit body if observed.
- **Pre-pass extraction bounding.** The pre-pass extracts every entry before any download starts. Extraction is a metadata call, not a media transfer, so it does not count toward `max_concurrent_downloads` (C6). The Implementer must decide whether the pre-pass needs its own concurrency bound or runs sequentially.

### 11.6 Deliverable

One commit.

- **Production code:** `src/vkdownloader/services/downloader.py` (download_video param addition + skip-extract), `src/vkdownloader/services/batch_downloader.py` (pre-pass + dispatch wiring + DownloadContext fields + docstring), `src/vkdownloader/models/enums.py` (SKIPPED docstring only).
- **Test code:** `tests/test_cli.py` (7 new methods in `TestBatchCommand`), `tests/test_batch_downloader.py` (2 new methods extending `TestBatchDedupSkip`).
- **Not modified:** `_resolve_output_file` (security.py), `_map_exception_to_status` (exceptions.py:216), the single-URL `download` command (cli.py), `perform_download`'s existing `video_data`/`selected_stream` contract.
- **Commit constraints:** one commit; no existing test in `TestBatchDedupSkip`, `TestBatchSummarySkippedAggregation`, `TestBatchDownloaderSemaphore`, `TestBatchLiveTaskBounding`, or any bounded-fan-out class is edited — only extended with new methods; no new lock file, no temp-dir abstraction, no `fsync`, no clobber policy, no name suffix, no temp sweep (C5, C7).
- **Commit body names:** (1) the pre-pass shape (option (b)), (2) the `mkdir` side effect (C9), (3) the narrowing of the no-network clause to "no media transfer" and why, (4) any existing tests preserved unchanged.

### 11.7 Dependency metadata

- **Blocked by:** `P12-B1` (both write `validate_output_path` / `security.py`; B10 reads `_resolve_output_file` which calls it). **`P12-B2`** (the new `B10 → B2` edge — the pre-pass is the right place to let the warning fire, not a call site B10 is about to restructure).
- **Blocks:** `P12-B2` (B10 establishes the pre-pass; B2 makes the warning fire through it).
- **Conflict-matrix rows:** §4.3 row 3 (`_resolve_output_file` — read-only for B10), row 18 (`cli.py` batch reader, sole owner), row 18b (`download_video`, sole owner), row 18c (`batch_downloader.py` fan-out and `_print_batch_summary`, sole owner), row 20b (`TestBatchCommand`), row 22 (`test_packaging.py` frozensets — no new file added, so 73/32/2/4 unchanged).
- **Risk tier:** High — but reduced: the within-batch mutex is structurally unnecessary (§3.8), Decision A and B are both closed (no open decision), and `download_video` is B10's sole writer (row 18b).
- **Agent roster:** Implementer, Planner, Validator. (No Auditor — the block inherits the auditor context verbatim in §10. No Researcher — Decision A fixes the answer. Planner stays because the pre-pass shape and `output_index` threading need a defined registry lifetime.)

---

## 12. Implementation task: P12-B6 — make the sweeps match what the tree contains

**Status:** DONE — implemented, tested (256 passed, 3 skipped in scope), committed. Execution position 7 (B1 → B10 → B2 → B4 → B5 → B6).

**Task file:** `.ai/tasks/p12-b6-sweeps-match-tree.yaml`

### 12.1 Semantic scope

One commit, three findings — `ART-003`, `ART-004`, `ART-013` (sweep half). All production
changes land in `src/vkdownloader/services/segment_downloader.py`; one comment-only update
in `src/vkdownloader/services/ffmpeg_utils.py`. The owning module is `segment_downloader.py`;
`src/vkdownloader/services/downloader.py` is a re-export facade (§2.2 `C3`) that exports
`_cleanup_segments` but never calls it.

**`_cleanup_segments` (lines 443–454):** bare `f.unlink()` over `glob("*")` with no
`is_file()` guard and no `missing_ok`. On Windows this raises `PermissionError [WinError 5]`
on a directory entry; on POSIX `IsADirectoryError`. The fix is intent-based: skip
non-regular entries with `if not f.is_file(): continue` and call `f.unlink(missing_ok=True)`.
`glob("*")` already matches `*.ts.tmp`; the guard is what makes unlinking them safe.

**`_tally_and_merge` (line 849):** `downloaded_count = len(list(segments_dir.glob("*.ts")))`
includes `batch_*.ts` temps, so `downloaded_count > len(segments)` and the merge is SKIPPED.
The fix narrows this count only (PoO decision D-4 = option (i)): filter out
`batch_`-prefixed names so the merge-decision count reflects real segments.

**`_clear_stale_segments` (lines 146–157):** sweeps only `*.ts`; the `NNNNN.ts.tmp`
residue created at the two `os.replace` publish sites (lines 204, 267) is never matched.
The fix introduces one suffix constant (`_SEGMENT_TEMP_SUFFIX: Final = ".tmp"`) shared at
both publish sites and the new `*.ts.tmp` glob in `_clear_stale_segments`.

**`_log_preserve_segments` (lines 1247–1275):** reporter count stays a raw working-directory
inventory. Under D-4 option (i) it is NOT narrowed — `TestPreserveSegmentsReporter` stays
green unchanged. Only its D-13/ART-004 deferral comment is updated to record the discharge.

**`ffmpeg_utils._merge_segments_batched` (lines 616–642):** comment-only update. The
D-13 deferral note that assigns the merge-temp count exclusion to ART-004 is updated to
record that the exclusion is now implemented in `_tally_and_merge`. The ART-012 sizing
note stays for B8. No logic is changed.

### 12.2 Implementation sequence

Six steps:

1. **Constant.** Add `_SEGMENT_TEMP_SUFFIX: Final = ".tmp"` near `_PLAYLIST_SIGNATURE_FILE`
   (segment_downloader.py:110). `Final` is already imported (line 14).

2. **`_cleanup_segments` guard (ART-003).** Replace `for f in segments_dir.glob("*"): f.unlink()`
   with an intent-guarded loop: skip non-files with `if not f.is_file(): continue`, then
   `f.unlink(missing_ok=True)`. The `rmdir()` tail and its `try/except OSError` are
   untouched.

3. **`_tally_and_merge` count (ART-004).** Replace
   `downloaded_count = len(list(segments_dir.glob("*.ts")))` with
   `downloaded_count = len([f for f in segments_dir.glob("*.ts") if not f.name.startswith("batch_")])`.
   D-4 = option (i): the reporter's count is not narrowed.

4. **`_clear_stale_segments` .ts.tmp sweep (ART-013).** After the existing `*.ts` unlink
   loop (line 155), add a second loop over `glob(f"*.ts{_SEGMENT_TEMP_SUFFIX}")` calling
   `stale_temp.unlink(missing_ok=True)`. Update the docstring to mention `.ts.tmp` coverage.

5. **Publish sites.** Replace the hard-coded `".tmp"` at both `os.replace` publish sites
   (lines 204, 267: `output_path.with_suffix(output_path.suffix + ".tmp")`) with
   `_SEGMENT_TEMP_SUFFIX`.

6. **Deferral comments.** Update the ART-004 half of the deferral note in
   `ffmpeg_utils._merge_segments_batched` (lines 631–640) and in
   `segment_downloader._log_preserve_segments` (lines 1256–1263) to record that the
   merge-temp count exclusion is now implemented. No logic changes — comment only.

### 12.3 Architectural constraints

- **Intent guard, not exception type.** `is_file()` to skip non-regular entries, NOT
  catching `IsADirectoryError` (POSIX-only). Windows raises `PermissionError [WinError 5]`.
  The existing `try/except OSError` on `rmdir()` must NOT be used as a model — it silently
  swallows `PermissionError`.

- **D-4 = option (i).** Narrow only the merge-decision count. `_log_preserve_segments`'s
  count stays a raw working-directory inventory. `TestPreserveSegmentsReporter`'s three tests
  stay green, unchanged. Do not narrow both counts.

- **Call sites unchanged.** `_cleanup_segments` is still called only under `if result:`
  (segment_downloader.py:867–868). This block adds NO new call sites — B7 owns those.
  Plan §6.6 acceptance criterion 7.

- **`.signature` short-circuit.** B6 is the only block allowed to change it (§4.3 row 8).
  The sweep in `_clear_stale_segments` currently runs only when the signature does NOT match;
  a matching-signature run skips all clearing. The Implementer must decide whether the
  `.ts.tmp` sweep should run even on a matching signature. Honest judgement point — see §12.5.

- **No `os.replace` test.** No test exercises `os.replace` (0 results in tests/). Do not
  introduce `fsync`, a temp-dir abstraction, or a lock file (§2.2 C5).

- **Leaf safety.** `segment_downloader.py` imports from `..config`, `..models.*`,
  `..utils.*`, `.concurrency`, `.downloader_throttle`, `.ffmpeg_utils`, `.quality`.
  No new import — `is_file()`, `missing_ok`, `glob`, `Final` are already in scope.
  `ffmpeg_utils.py` is a leaf (C4): no imports from `segment_downloader`.

- **No file:line references in commit message.** Anchors are symbol names.

- **One suffix constant.** `_SEGMENT_TEMP_SUFFIX` is shared at both publish sites and the
  new glob — the sweep glob and publish sites cannot drift.

### 12.4 Required tests

| Criterion | Test method | Target | What it asserts |
|---|---|---|---|
| Directory entry does not crash cleanup | (new) `test_cleanup_skips_non_regular_entries` | `TestCleanupSegments` | A subdirectory inside `segments_dir` alongside segment files → `_cleanup_segments` returns without raising, file entries are removed |
| Merge reached with leftover batch temps | (new) `test_tally_excludes_batch_temps_and_reaches_merge` | new class in `test_segment_downloader.py` | A tree of NNNNN.ts segments + batch_*.ts temps → `_tally_and_merge` calls `_merge_segments_batched` (patched) instead of returning `None` on count mismatch |
| .ts.tmp does not survive stale sweep | (new) `test_ts_tmp_cleaned_by_stale_sweep` | new class in `test_segment_downloader.py` | A `.ts.tmp` file beside segments does not survive `_clear_stale_segments` when the signature does not match |
| Reporter unchanged | all 3 existing | `TestPreserveSegmentsReporter` | Green, UNCHANGED. `test_count_includes_merge_temps_and_says_so` still asserts `working_dir_ts_count == 3` |
| D-13 preservation oracle | existing | `TestMergeSegmentsBatched::test_batch_failure_preserves_inputs_and_earlier_batch_temps` | Green, UNCHANGED — failure leaves accumulated batch temps intact |
| Standing gate | §7.1 | all | G1/G2/G4/G6 exit 0, G5 non-increasing, skip count 3 |

**Existing tests must pass unchanged:**
- `TestCleanupSegments` (2 tests at test_hls_downloader.py:210–235) — extended only with a new method.
- `TestPreserveSegmentsReporter` (3 tests at test_segment_downloader.py:419–472) — green, unchanged.
- `TestMergeSegmentsBatched::test_batch_failure_preserves_inputs_and_earlier_batch_temps` (test_ffmpeg_utils.py:646) — green, unchanged.

### 12.5 Honest judgement

- **`.signature` short-circuit scope.** B6 may extend `_clear_stale_segments`'s sweep to
  cover `*.ts.tmp` (inside the clearing path, after the signature check) or may move the
  `.ts.tmp` sweep before the short-circuit so it runs regardless of signature match.
  Recommendation: keep it inside the clearing path (smallest diff). The matching-signature
  + `.ts.tmp`-residue case is a narrow edge: the residue is created during an active
  download (between `open()` and `os.replace()`), and if the download was progressing far
  enough to have written a matching `.signature`, the segment is either complete (`.ts` on
  disk, no `.ts.tmp`) or the crash happened before the signature write. Declare the residual
  in the commit body if the Implementer disagrees.

- **D-4 = option (i) confirmed.** The reporter's number is a working-directory inventory
  (`_log_preserve_segments`'s `next_action` says "clear the working directory"; its pinned
  test asserts `working_dir_ts_count == 3` with a `batch_00000.ts` present). Narrowing only
  the merge-decision count is the binding decision.

### 12.6 Deliverable

One commit.

- **Production code:** `src/vkdownloader/services/segment_downloader.py`
  (constant + 4 production changes + 1 comment), `src/vkdownloader/services/ffmpeg_utils.py`
  (1 comment only — D-13/ART-004 discharge in `_merge_segments_batched`).
- **Test code:** `tests/test_hls_downloader.py` (1 new method in
  `TestCleanupSegments`), `tests/test_segment_downloader.py` (extend import block + 1 new
  test class with 2 methods).
- **Not modified:** `_cleanup_segments` call sites (still only under `if result:`), the
  `if result:` guard itself, `_log_preserve_segments`'s count logic (only its comment), the
  `.signature` short-circuit logic (only a decision about sweep placement), `os.replace`
  publish paths (only the suffix literal → constant).
- **Commit constraints:** one commit; `TestPreserveSegmentsReporter` unchanged,
  `TestMergeSegmentsBatched::test_batch_failure_preserves_inputs_and_earlier_batch_temps`
  unchanged, `TestCleanupSegments` extended only (not edited); no new file, no lock file,
  no `fsync`, no temp-dir abstraction (C5, C7); `_SEGMENT_TEMP_SUFFIX` shared at both
  publish sites.
- **Commit body names:** (1) D-4 = option (i) — only the merge-decision count is narrowed,
  (2) the `_.ts.tmp` sweep placement decision (inside the clearing path, after the
  short-circuit), (3) the `is_file()` intent guard as the ART-003 fix (not
  `IsADirectoryError`), (4) the ART-004 deferral discharge, (5) any existing tests preserved
  unchanged.

### 12.7 Dependency metadata

- **Blocked by:** Nothing — no code dependency on prior blocks. B6 writes
  `segment_downloader.py` and `ffmpeg_utils.py`, not `utils/security.py`. Execution-order
  predecessor is B5 by the linearisation (B1 → B10 → B2 → B4 → B5 → B6).
- **Blocks:** `P12-B7` (new cleanup call sites rely on the `is_file()` guard), `P12-B9`
  (ROLLOUT-1: ART-013 residue must be swept before the probe in B9 fires).
- **Conflict-matrix rows:** §4.3 row 6 (`segment_downloader.py`), row 7
  (`_cleanup_segments` guard + call sites; B6 edits the guard, B7 owns new call sites),
  row 8 (`_clear_stale_segments` short-circuit; B6 is the only block that may change it),
  row 9 (`_tally_and_merge` count), row 10 (`TestPreserveSegmentsReporter`), row 13
  (`_merge_segments_batched` deferral comment), row 17 (`TestCleanupSegments`), row 18b
  (`download_video` — not touched).
- **Risk tier:** High — narrows the count that decides whether a merge runs. Mitigated by
  D-13 oracle (batch-failure-preservation test unchanged) and the merge's own
  existence check (the downstream `concat` list file names missing files via
  `FileNotFoundError`, which is the backstop against a narrowed count admitting an
  incomplete set).
- **Agent roster:** Implementer, Auditor, Planner, Validator. (Auditor context in §9.
  Researcher returned empty output (rate-limited); research direction is captured inline
  in the task YAML. Planner stays because the `.signature` short-circuit decision and
  the D-4 option (i) fork need a defined resolution.)

---

## 13. P12-B2 Auditor context (`context_a`)

**Block:** P12-B2 — make the `ART-009` warning reach the user (§3.3 / §6.3)
**PoO decision:** option (a) — warn everywhere (all call sites).
**Full output:** `.ai/audit/problems/12-filesystem-artifacts-p12-b2-context_a.md`

### 13.1 Call-site census (`validate_output_path` — 3 sites)

| # | File | Line | Call | `warning` | Fires? |
|---|---|---|---|---|---|
| 1 | `utils/security.py` (`_resolve_output_file`) | 111 | `validate_output_path(output_path, warning=False)` | `False` | No |
| 2 | `services/segment_downloader.py` (`download_hls_with_resume`) | 1205 | `validate_output_path(request.output_file)` | default `True` | **Yes** |
| 3 | `services/ytdlp_downloader.py` (`download_with_ytdlp_with_resume_fallback`, retry probe) | 909 | `validate_output_path(output_file, warning=False)` | `False` | No |

One site fires; two suppress. **No direct `validate_output_path` call exists in `cli.py`.**

### 13.2 Call-site census (`_resolve_output_file` — 2 sites)

| # | File | Line | Context |
|---|---|---|---|
| 1 | `services/downloader.py` (`download_video`) | 360 | Single-URL `download` path; also batch path via `_download_single` |
| 2 | `services/batch_downloader.py` (pre-pass) | 390 | B10 pre-pass — resolves every URL before dispatch |

Both reach `validate_output_path(..., warning=False)` at security.py:111.

### 13.3 The warning itself

**Code:** `security.py:78–83`

```python
logger.warning(
    "output_path_inside_repository",
    path=str(resolved),
    repo_root=str(repo_root),
    error_code="output_path_in_root",
)
```

| Attribute | Value |
|---|---|
| Event name | `"output_path_inside_repository"` |
| Level | `WARNING` |
| Logger | `structlog.get_logger("vkdownloader.utils.security")` |
| Fields | `path` (resolved), `repo_root` (derived), `error_code` (literal str) |
| Trigger | `resolved.relative_to(repo_root)` succeeds AND `warning` is `True` |
| Channel | structlog JSON sink (per `config.setup_logging`), not `typer.echo` |

**The two `..`-guards (lines 56, 68) `raise DownloadError`** — they are not warnings. There is only **one** `logger.warning` in `validate_output_path`. B1's change (`".." in str(path)` → `".." in path.parts`) is **committed** as `12af960` (the preamble's "uncommitted in working tree" is stale). `_resolve_output_file` body and `warning=False` are unchanged since `e59523c`.

### 13.4 The loader path

The single-URL `download` command does **not** call `validate_output_path` directly. The chain is:

```
cli.download (cli.py:394)
  → download_video (downloader.py:394 → :360)
      → _resolve_output_file (security.py:111) → validate_output_path(warning=False)  ← suppressed
  → perform_download (downloader.py:368)
      → download_with_ytdlp_with_resume_fallback (ytdlp_downloader.py:229)
          → [retry probe, line 909:] validate_output_path(warning=False)  ← suppressed
          → [segment fallback:] download_hls_with_resume → validate_output_path(request.output_file)  ← fires
```

The warning fires **only** on the segment-fallback path. Both the initial resolution and the retry-loop probe on the default loader path suppress it.

### 13.5 The B10 → B2 edge — what needs to change

The B10 pre-pass is **in the working tree**, unmodified (`batch_downloader.py:390` calls `_resolve_output_file`). It reaches `validate_output_path(..., warning=False)` at `security.py:111`.

Per B2 option (a) "warn everywhere":

1. **In `_resolve_output_file` (security.py:111):** remove `warning=False` → default `warning=True`. This single change covers **both** call sites of `_resolve_output_file` (the B10 pre-pass and the single-URL `download` path), since both funnel through this function.
2. **In `ytdlp_downloader.py:909`:** remove `warning=False` → default `warning=True`. This is the second `warning=False` suppression site.
3. **No change** to `segment_downloader.py:1205` — already uses the default.

B2 must change `security.py:111` (inside `_resolve_output_file`), **not** re-add the warning at `batch_downloader.py:390` — B10 is restructuring the pre-pass and that call site should not be touched by B2.

### 13.6 The `repo_root` defect (B2's domain)

**Line 74:** `repo_root = Path(__file__).resolve().parent.parent.parent`

`__file__` = `src/vkdownloader/utils/security.py`:
- `.parent` → `src/vkdownloader/utils/`
- `.parent` → `src/vkdownloader/`
- `.parent` → `src/` ← live value (`C:\py_exp\mko_vkideo\src`)

The repository root is `C:\py_exp\mko_vkideo`. The expression is **one `.parent` short**. This means `resolved.relative_to(repo_root)` only succeeds for paths under `src/` — paths under the rest of the repo (`docs/`, `tests/`, project root) hit `ValueError` (caught, no warning). The warning fires only inside `src/` and is silent everywhere else in the repo, even though Decision B says those paths are accepted. Fix: four `.parent` calls.

### 13.7 Test note for B2's Validator

`tests/test_security.py::test_path_inside_repo_warns` (lines 57–78) **mocks `Path.resolve`**, returning a `MagicMock`. The mock replaces the entire `repo_root` derivation, so the test **cannot detect** that `repo_root` is one level too deep. A B2 oracle must assert the derivation **by value** using the real `repo_root` — e.g., a path under `<repo>/docs/` (not under `src/`) should warn, proving the root is at the right level.

---

