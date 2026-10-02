# Phase 05 — Subprocess and browser boundary: validated findings

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/05-audit-subprocess-browser.md`
**Status:** complete
**Validated:** yes

> **Deviation from the report format, stated once here.** The template
> (`.ai/audit/templates/audit-findings.md`) defines nine mandatory fields per finding
> (`:64-74`) and none of them carries a validation decision — its finding block runs from the
> heading straight into the field table (`:19-33`). The `Validation Note` this phase must
> attach to **every** decided finding therefore has no slot. It is written directly below each
> `### {ID}:` heading, above the retained body. The absence of the slot was filed as `VAL-001`
> by the `02` validation run (`99-validation/02-config-validated-findings.md`) and is not
> re-filed here.
>
> **A second, different limitation, recorded and not papered over.** The source report does
> not carry three of the format's mandatory fields: no `Affected Modules`, no
> `Classification` and no `Recommendation` for any of its sixteen findings, and none of the
> template's Summary / Mandatory Fixes / Advisory Recommendations / Doc Updates sections.
> The practical consequence is that the §5(d) check *"Classification legality — is the
> classification one the format defines, and is it the right one?"* is **not executable for
> any finding in this corpus**: there is no value to adjudicate. That check is therefore
> absent from this artifact rather than passed. It is an input limitation, not a `VAL-`
> finding: the format defines the field correctly and `99-audit-validate.md` §10 reserves
> `VAL-` for a conflict, a merge, an unsafe ordering or a pipeline-document defect.
>
> **How the decisions were reached.** Every finding was re-derived from the artifact it
> names and from the **installed** dependencies — the real `ffmpeg.exe` on `PATH`, the real
> `yt-dlp` in the active environment, the real Playwright driver — not from the report's own
> wording. Sixteen findings, sixteen decisions, two `VAL-` findings against the audit inputs
> themselves. No source file was modified and no finding was deleted; every retained claim and
> every correction is recorded in place.
>
> **What this run did not verify is named as such.** Where the report's own evidence could
> not be reproduced here (one memory figure was re-measured instead, one structural claim was
> checked by reading rather than by driving), the note says which.

---

## R0 — Corpus map, identifier map, decision-record map

Recorded before any check, because these three are the ways this phase manufactures a clean
bill of health. Scope `.ai/`, excluding `.kilo/worktrees/`.

**Corpus map.** The phase range is `01`–`11` plus this file.

| Phase | Handbook | Findings file | Validation store | State |
|---|---|---|---|---|
| 01 entry/architecture | `01-audit-entry-architecture.md` | `01-entry-architecture/findings.md` | present | validated |
| 02 configuration | `02-audit-config.md` | `02-config/findings.md` | present | validated |
| 03 network/resilience | `03-audit-network-resilience.md` | `03-network-resilience/findings.md` | present | validated |
| 04 concurrency/cancellation | `04-audit-concurrency-cancellation.md` | `04-concurrency-cancellation/findings.md` | present | validated |
| 05 subprocess/browser | `05-audit-subprocess-browser.md` | `05-subprocess-browser/findings.md` | **this file** | **the file this run validates** |
| 06 credentials/secrets | `06-audit-credentials-secrets.md` | `06-credentials-secrets/findings.md` | present | validated |
| 07–11 | present | all absent | — | not yet run; out of this run's scope |
| 99 validation | `99-audit-validate.md` | — | this file | running |

No findings file exists outside the `01`–`11` range; there is no corpus drift to report. The
`05` handbook exists, so the gap the `06` run recorded against it (a handbook with no
findings file, `99-validation/06-credentials-secrets-validated-findings.md:38`) is now
closed by this file's existence.

**Identifier map.** Live prefixes in the corpus: `ENT` (01), `CFG` (02), `NET` (03), `CON`
(04), `TRN`/`BRW` (05), `SEC` (06), `VAL` (99). No prefix is unclaimed, and the two prefixes
this phase adjudicates (`TRN`, `BRW`) collide with no other.

**Decision-record map.** The report format has no slot for a decision
(`.ai/audit/templates/audit-findings.md:19-33`, `:64-74`) — an **absent slot**, recorded
here and satisfied by the deviation paragraph above, not a missing decision. All sixteen
findings carry a `Validation Note`; the tally at the end of this artifact reconciles against
sixteen records. The **classification** slot is absent from the *source report* for the same
sixteen findings, which is the second limitation stated in the header.

**Pipeline-document map.** The documents this phase reads for §6's pipeline-document subjects:
`.kilo/commands/audit/*.md` (the command that selects and runs phases), the rewrite command
that edits the validation store in place, the phase handbook directory
`.kilo/commands/audit/phases/` (12 files, `99-audit-validate.md` among them),
`.ai/audit/templates/audit-findings.md`, and the agent role files the pipeline launches.
**This run adjudicates one phase's findings and does not execute block (g) or block (h) as
a pipeline audit** — those blocks are owned by whichever validation run is asked to examine
the pipeline, and no finding in the phase-05 corpus depends on them. Recorded so the absence
is not mistaken for a clean bill of health.

---

## Checkpoint 1 — R1 Copy Source Findings

- **Stage:** R1 Copy Source Findings
- **Findings in scope:** 16 (TRN-001 … TRN-013, BRW-001 … BRW-003)
- **Evidence anchor:** this file, self-contained — every finding's original text is retained
  below, above its decision record. The source report `.ai/audit/05-subprocess-browser/
  findings.md` was opened read-only and is unmodified.
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 2 — R2 Cross-Finding Analysis

- **Stage:** R2 Cross-Finding Analysis
- **Findings in scope:** 16
- **Cross-phase conflicts:** 1 (`VAL-501` — `SEC-004`'s validated form asserts the opposite of
  `TRN-001` about the ffmpeg transport's concealment)
- **Merge candidates:** 0 — `TRN-004`/`TRN-005`/`TRN-006`/`TRN-007` share one mechanism but
  each is separately reachable and separately fixable; they are a **dependency set**, not one
  defect stated four times (see `VAL-502`)
- **Checkpoint status:** closed

## Checkpoint 3 — R3 Validate Each Finding

- **Stage:** R3 Validate Each Finding
- **Findings in scope:** 16 (Validated 11, Reclassified 3, Merged 0, Rejected 2)
- **Evidence anchor:** the per-finding `Validation Note` on each block below; every note names
  the artifact read and the re-derived fact
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 4 — R4 Assess Rollout Safety

- **Stage:** R4 Assess Rollout Safety
- **Unsafe-ordering count:** 2 dependency chains, filed as one finding (`VAL-502`)
- **Findings added:** 2 (`VAL-501`, `VAL-502`)
- **Checkpoint status:** closed

---
## Baselines re-verified this run

Re-run, not inherited. These are the state the decisions below were observed against.

| Command | Result |
|---|---|
| `uv run pytest tests -q` | **498 passed, 4 skipped** in 25.44s — exit 0 |
| `uv run ruff check src/vkdownloader/services/{ytdlp_downloader,ffmpeg_utils,downloader}.py src/vkdownloader/infrastructure/browser.py src/vkdownloader/utils/url_sanitizer.py` | `All checks passed!` — exit 0 |
| `uv run ruff format --check src` | `30 files already formatted` — **exit 0** |
| `uv run mypy` over the same five paths | `Success: no issues found in 5 source files` — exit 0 |

**Two of the source report's baseline statements do not reproduce, and neither is a finding.**

1. **The suite count.** The report records `495 passed, 4 skipped`. The tree is unchanged in
   `src/`, `tests/` and `pyproject.toml` (`git status --short -- src tests pyproject.toml` is
   empty at `ea44b3d`), and the count is **498 passed, 4 skipped**. Nothing in this run
   changed `tests/`. The report's figure is stale by three; no decision depended on it.
2. **`ruff format --check` is clean.** The phase-06 validator recorded `exit 1` with two
   files to reformat (`06-credentials-secrets-validated-findings.md:111`), and the phase-05
   report states the failure no longer reproduces. Re-run here: **exit 0, 30 files already
   formatted.** Both statements agree; recorded because `VAL-` severities in this run were
   composed against a formatting-clean tree.

**Line anchors.** Every anchor cited by a decision-bearing finding was opened against this
tree. **Two are drifted** and are corrected in place in the findings that cite them
(`pyproject.toml:39-40`, `url_sanitizer.py:13-24`); no other drift was found among the
anchors opened. The report's own anchor ledger claims `106 anchors, 106 exact, 0 drifted`;
that count was not reproduced here because this run opened the anchors, not the ledger —
`downloader.py`, `ffmpeg_utils.py`, `ytdlp_downloader.py`, `browser.py` and
`url_sanitizer.py` in full, `pyproject.toml:1-50`, `tests/test_hls_downloader.py:630-809`,
`extractor.py:255-284`, and the `signal_handlers.py` matches behind the signal-handler skip.

**The installed toolchain, read from the machine rather than assumed.**

| Fact | Measured |
|---|---|
| muxer on `PATH` | `C:\ffmpeg\ffmpeg.exe` |
| muxer version | `ffmpeg version N-117624-g9eb7e8d2a4-20241023`, libavutil 59.44.100, libavcodec 61.22.100, libavformat 61.9.100 (a 7.x-lineage nightlies build) |
| `@file` in `ffmpeg -h full` | **no entry** |
| `-/opt` in `ffmpeg -h full` | **no entry** |
| downloader in the active environment | `python -m yt_dlp --version` → `2026.07.04` |
| `--hls-prefer-native` | **accepted** (absent from `--help`, but the parser does not reject it) |
| Playwright browser binaries | **not installed** (`chromium_headless_shell-1228` missing) |

---

## Findings

### TRN-001: HIGH — The response file is never opened: the convention the design rests on is gone

> **Validation Note:**
> - **Action:** reclassified
> - **Type:** `SPEC-DEVIATION` → **`RUNTIME-ERROR`**
> - **Detail:** The claim reproduces, and it is the most consequential claim in this corpus.
>   Re-derived twice, independently of the report's own harness.
>   **(a) Raw, against the real muxer.** A response file written by the product's own
>   `_format_argfile` and invoked as `ffmpeg "@<path>"`:
>   ```
>   A: @argfile PRESENT, network input
>      exit=4294967274   output file created: False
>      [AVFormatContext @ …] Unable to choose an output format for
>        '@C:\Users\…\Temp\vk_ffmpeg_w9g__fhe.args'; use a standard extension for the
>        filename or specify the format manually.
>      Error opening output file @C:\Users\…\Temp\vk_ffmpeg_w9g__fhe.args.
>      Error opening output files: Invalid argument
>   B: @argfile ABSENT (control)                     -> identical, identical wording
>   C: @argfile PRESENT, valid lavfi input           -> identical, output file created: False
>   D: direct argv, no @file, same lavfi input      -> exit=0, output file created: True
>   ```
>   Control **C** is the decisive one: with a response file that names a *valid, self-contained*
>   input and a *writable* output, no output file is produced. Control **D** is the same
>   arguments passed directly and it succeeds. The file is not read — it is not partially
>   read, and the presence or absence of the file changes nothing, which is what a literal
>   output filename does.
>   **(b) Through the product's own code path.** `HLSDownloader.download_with_ffmpeg` driven
>   three times against `http://127.0.0.1:9/none.m3u8`:
>   ```
>   RUN: {'i': 0, 'result': None, 'elapsed_ms': 31.0}
>   RUN: {'i': 1, 'result': None, 'elapsed_ms': 15.0}
>   RUN: {'i': 2, 'result': None, 'elapsed_ms': 32.0}
>   ```
>   each ending in `Unable to choose an output format for '@…vk_ffmpeg_*.args'`, each logging
>   `ffmpeg_download_failed` and each returning `None`. The argv handed to the OS is exactly
>   the two tokens the report names: `['ffmpeg', '@C:\…\vk_ffmpeg_*.args']`.
>   **(c) The report's counts are not endorsed; this run's counts are recorded instead.**
>   The report claims 25/25. This run measured 3/3 through the product path and 4/4 raw
>   invocations. The conclusion does not depend on the count.
>   **(d) `perform_download` silently substitutes.** Read at `downloader.py:550-553`:
>   `if result is None:` → shutdown check → `logger.info("ffmpeg_failed_fallback_to_segment_
>   download")` → `download_hls_with_resume(...)` → `return result` at `:568`. Exact.
>   **(e) The product's own documentation claims the feature works**, which is what makes a
>   silent no-op a defect rather than an unimplemented idea: `README.md:57`
>   (`vkdownloader download "…" --method ffmpeg`), `docs/99-reference/cli-reference.md:66`
>   (`--method | -m | str | auto | Download method: yt-dlp, ffmpeg, or auto`) and `:96`
>   (a worked `--method ffmpeg` example), `docs/01-tools/quality-selection.md:96-99`,
>   `docs/01-tools/vkdownloader-overview.md:138`, `docs/11-guides/vkdownloader-limitations.md:131`.
>   **(f) The concealment rationale is void.** `downloader.py:96-99` states the response file
>   exists "so that sensitive values (e.g. signed m3u8 URLs with CDN tokens) never appear in
>   the process command-line arguments". Verified: they do not appear in the argv — because
>   nothing is ever passed to the muxer. The mechanism protects nothing.
>   **(g) Why the `Type` changes.** §5(d): *"Observed failure — a finding describing something
>   seen to fail is checked against the runtime-failure label first. Never reclassified away
>   because a role file omits the label."* This is not a contradiction of a declared rule; it
>   is a feature that was observed failing seven times in this run. `RUNTIME-ERROR` is the
>   format's label for that.
>   **(h) One correction to the evidence.** The `Subject` line cites `pyproject.toml:39-40` for
>   "the asset is packaged". That range is the comment explaining the wheel artefact; the
>   declaration itself is `pyproject.toml:44`
>   (`artifacts = ["src/vkdownloader/stealth.min.js"]`). The anchor is drifted by four lines
>   and is immaterial to this finding (the argfile is not a packaged asset), but it is
>   corrected here and at `BRW-003`, where it is load-bearing.
> - **Severity re-derived: HIGH → CRITICAL.** Two independent grounds, both from this run:
>   *The defect.* `--method ffmpeg` is a documented, shipped CLI option
>   (`README.md:57`; `docs/99-reference/cli-reference.md:66,96`). Selecting it executes
>   **none** of the transport the operator selected, substitutes a different one, and can
>   return a successful download — so the operator never learns their flag did nothing. The
>   only evidence is one INFO record. This is total feature failure with a silent substitute,
>   not a degradation. The counter-argument weighed and rejected: the segment fallback usually
>   still yields a file, which lowers the *blast radius* but does not lower the severity,
>   because the failure mode is precisely "it appears to have worked".
>   *The ordering condition.* `99-audit-validate.md:367` sets CRITICAL at "a fix that cannot
>   be ordered safely because a prerequisite of it is itself a finding". TRN-001 has no
>   safe fix on its own: the installed muxer has neither `@file` nor `-/opt`, so every repair
>   either moves the signed m3u8 URL and the cookie-file path onto the command line — which is
>   the exposure `SEC-004` (phase 06) exists to prevent — or deletes the transport, which
>   contradicts six documentation sites. Both routes land on another phase's finding. Filed
>   with the dependency chain as `VAL-502`.
> - **See also:** `VAL-501` (phase 06 asserts the opposite of this finding about the same
>   subject), `VAL-502` (fix ordering), `TRN-002` (its first half is inert while this stands
>   and live once this is fixed), `TRN-010` and `SEC-004` (the argv/argfile asymmetry), `BRW-002`
>   (rejected below, for the same reachability reason).

---
> **Retained source text — TRN-001.** *Type `[SPEC-DEVIATION]` (reclassified above to
> `RUNTIME-ERROR`). Subject the muxer transport's argument vector,
> `src/vkdownloader/services/downloader.py:92-124` (`_temp_argfile`), `:302-309` (the
> invocation), `:96-99` (the stated purpose of the convention), `pyproject.toml:39-40` (the
> asset is packaged).*
>
> **What was observed.** The application writes every muxer argument into a temporary file and
> invokes `ffmpeg @<path>`. The purpose, stated in the code's own docstring, is that
> "sensitive values (signed CDN URLs, cookie file paths) never appear in the process
> command-line arguments". The muxer this application discovers on `PATH` does not expand
> `@file` at all: it takes the token as a literal output filename.
>
> `C:\ffmpeg\ffmpeg.exe`, `ffmpeg -version` → `ffmpeg version N-117624-g9eb7e8d2a4-20241023`
> (an ffmpeg 7.x-lineage build; ffmpeg 7.0 replaced the whole-argument `@file` form with
> `-/opt <path>`, which loads option *values* from a file and is not a substitute here).
> `ffmpeg -h full` contains no `@file` entry.
>
> Twenty-five real invocations of `HLSDownloader.download_with_ffmpeg`, each with its own
> freshly written response file, produced this child output, verbatim, 25 times out of 25:
> ```
> [out#0 @ ...] Unable to choose an output format for '@C:\Users\NMATVE~1\AppData\Local\Temp\vk_ffmpeg_i_r7iyso.args'; use a standard extension for the filename or specify the format manually.
> Error opening output file @C:\Users\NMATVE~1\AppData\Local\Temp\vk_ffmpeg_i_r7iyso.args.
> Error opening output files: Invalid argument
> ```
> Three control invocations calibrate the wording: with a hand-written response file **present**
> and with the same path **absent**, the real muxer behaves identically and does not read the
> file in either case. Distribution over the twenty-five runs: `{"not-expanded": 25}`.
>
> **Failure scenario.** `vkdownloader download <url> --method ffmpeg`. The muxer exits non-zero
> in about 30 ms without ever opening the response file, so the input URL is never fetched.
> `download_with_ffmpeg` logs `ffmpeg_download_failed` and returns `None`; `perform_download`
> (`downloader.py:550-568`) then logs one INFO record,
> `ffmpeg_failed_fallback_to_segment_download`, and silently switches to the segment
> downloader. The operator's selected transport never runs, and the only evidence is a single
> INFO line.
>
> **Consequence beyond the failure.** The concealment mechanism the code justifies does not
> exist on this tool, so two things are true at once: the transport does not work, *and* the
> rationale recorded at `downloader.py:96-99` for the response-file design is not achieved by
> the mechanism it names.

---

### TRN-002: HIGH — The response file is destroyed before the child opens it, and a failed destroy skips the child-signalling guarantee

> **Validation Note:**
> - **Action:** reclassified
> - **Type:** `BEST-PRACTICE` (maintainability of a correct pattern) → **`SPEC-DEVIATION`**
> - **Detail:** Both halves reproduce; the finding is sound and is filed against a real
>   contradiction of the code's own guarantee.
>   **Ordering half — confirmed structurally, and independently of the report's admission that
>   it could not be observed.** The `async with _temp_argfile(ffmpeg_args)` block opens at
>   `downloader.py:302` and closes on `:309`, immediately after
>   `asyncio.create_subprocess_exec` returns at `:305-309`. Leaving the block runs
>   `Path(path).unlink(missing_ok=True)` at `downloader.py:124`. The `try` at `:311` whose
>   `finally` at `:400-409` guarantees `cancel_subprocess` is **outside** the `async with`.
>   Measured at the spawn: `LIFETIME: {'exists_at_spawn': True, 'argv': ['ffmpeg',
>   '@C:\\…\\vk_ffmpeg_5ibpa5vu.args']}` — the file is present when the child is created, and
>   the destroy runs on the next statement.
>   **Failed-destroy half — reproduced independently, and it is the half that matters.**
>   Driving the product's own destroy step against a path whose removal fails (a handle held
>   open without `FILE_SHARE_DELETE`, exactly as the report describes):
>   ```
>   OUTCOME: {'exception': "PermissionError: [WinError 32] The process cannot access the
>             file because it is being used by another process:
>             'C:\\…\\Temp\\vk_ffmpeg_m1x8k0bv.args'"}
>   CHILD_PID: 15372
>   CHILD_ALIVE_AFTER_RETURN: True
>   ```
>   The exception escapes `_temp_argfile.__aexit__`, propagates past `downloader.py:310`,
>   never reaches the `try` at `:311`, never runs the `finally` at `:400-409`, and
>   `cancel_subprocess` is never called. The child is alive when the call returns. This is a
>   structural certainty, not a race: nothing between `:309` and `:311` can catch it, and the
>   outer `finally` at `:410-413` only unlinks the cookie file.
>   **Why the `Type` changes.** The report hedged with a parenthetical
>   (`BEST-PRACTICE` … `[SPEC-DEVIATION]` on the guarantee at `downloader.py:400-409`), which
>   the format's single `Type` field does not admit. `SPEC-DEVIATION` is the correct label and
>   the contradiction is explicit in the source: `downloader.py:401-402` reads *"Guarantee
>   ffmpeg is terminated even on CancelledError or unhandled exception, preventing orphaned
>   processes."* A guarantee the code demonstrably does not provide is a stated rule the
>   implementation violates.
>   **One qualification, carried forward to `VAL-502`.** The ordering half is currently
>   *inert*: because the muxer never opens the file (`TRN-001`), deleting it immediately
>   after spawn is harmless today. It becomes a live defect the moment `TRN-001` is fixed.
>   The failed-destroy half is **not** contingent — the child is spawned whether or not it
>   reads anything, so a failed unlink orphans a live `ffmpeg.exe` on the current tree.
> - **Severity:** HIGH, re-derived and unchanged. Reachable without any harness: any process
>   holding the temp file transiently — a virus scanner, a search indexer — turns a clean
>   download into a raised `PermissionError` with an un-reaped muxer behind it.
> - **See also:** `TRN-001` (the precondition that makes the ordering half inert today),
>   `VAL-502` (the ordering constraint between the two fixes), `TRN-012` (the same
>   termination ladder, read differently).

---
> **Retained source text — TRN-002.** *Type `[BEST-PRACTICE]` … `[SPEC-DEVIATION]` on the
> guarantee at `downloader.py:400-409` (reclassified above to `SPEC-DEVIATION`). Subject
> `downloader.py:302-309` (spawn inside the `async with` block), `:124` (the destroy step in
> the context manager's exit), `:311` / `:400-409` (the `try`/`finally` that guarantees
> `cancel_subprocess`).*
>
> **What was observed — the ordering.** The child is spawned *inside* `async with
> _temp_argfile(...)`, and the `async with` block is left on the very next statement
> (`downloader.py:302-309`). Leaving the block runs `Path(path).unlink(missing_ok=True)` at
> `downloader.py:124`. The `try`/`finally` that guarantees the child is terminated
> (`downloader.py:400-409`) is not entered until `downloader.py:311`. Between the
> `create_subprocess_exec` call returning and the child opening the file, the parent therefore
> destroys the file, and a failure to destroy it escapes *above* the guarantee that would have
> signalled the child.
>
> This ordering could not be observed end to end on this platform, because the muxer never
> reaches the open (TRN-001). It is stated as structure, with the distribution recorded as
> distribution: 25 of 25 runs the child never opened the file, for the independent reason
> above. Structural facts are reported as structural; the run count is not offered as evidence
> of the ordering.
>
> **What was observed — the failed destroy.** The product's own destroy step was driven
> against a path whose removal fails, with no replacement of any product code: a watcher
> process opened each `vk_ffmpeg_*.args` file as soon as it appeared and held the handle (on
> Windows an open handle without `FILE_SHARE_DELETE` makes `DeleteFileW` fail). Result:
> ```
> destroy_step_exception: PermissionError: [WinError 32] The process cannot access the file
>                          because it is being used by another process:
>                          'C:\Users\NMATVE~1\AppData\Local\Temp\vk_ffmpeg_30j44y7u.args'
> child_pid: 24208
> child_alive_after_escape: true
> survivors: [24208]
> parent_returned: None
> ```
> The exception escapes `_temp_argfile`'s exit, so `download_with_ffmpeg` never reaches
> `downloader.py:311`; the `finally` at `:400-409` is skipped; no `cancel_subprocess` is ever
> called; and the spawned child is still running when the call returns. This is the only row of
> the suite with a live child, and it produced a survivor.
>
> **Failure scenario.** On any machine whose muxer does expand `@file`: if the deletion wins
> the race, the child sees a missing response file and reports "no such file"; if the child has
> the file open when the parent deletes, the parent's `unlink` raises, the failure replaces the
> in-flight download, and the muxer is left running with no one to reap it.

---

### TRN-003: HIGH — No process boundary around any invocation; a process the child creates for itself outlives the command

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced, and the reproduction is stronger and simpler than the report's
>   three-exit-path stub matrix.
>   **Structural half — confirmed exactly.** A repository-wide search of `src/` for
>   `start_new_session`, `setsid`, `process_group`, `CREATE_NEW_PROCESS_GROUP`,
>   `CREATE_BREAKAWAY_FROM_JOB`, `creationflags`, `startupinfo`, `JobObject`,
>   `AssignProcessToJobObject` and `taskkill` returns **no file found** — zero hits. The
>   process-creating sites are exactly the six the report names: `ytdlp_downloader.py:631`,
>   `downloader.py:305`, `ffmpeg_utils.py:297`, `ffmpeg_utils.py:344`, `browser.py:38`
>   (`async_playwright().start()`) and `browser.py:40` (`chromium.launch(...)`). The ladder
>   at `ffmpeg_utils.py:179-207` addresses `process.pid` and nothing else — read and
>   confirmed.
>   **Behavioural half — reproduced directly.** A stub child that spawns a process of its own,
>   then the product's own `cancel_subprocess` on the direct child:
>   ```
>   step 2: direct=23816 grandchild=13016
>   step 4: cancel_subprocess returned True
>   step 5: direct_alive=False grandchild_alive=True
>   step 6: direct_returncode=1
>   ```
>   The direct child is dead, the call reports success, and the descendant is untouched. This
>   is the finding's claim with no harness in between.
>   **One correction to the failure scenario.** The scenario names "the muxer that yt-dlp
>   started to merge the streams". The vector passes `--hls-prefer-native`
>   (`ytdlp_downloader.py:272`), which directs yt-dlp to use its own HLS downloader instead of
>   shelling out to a muxer; the flag is accepted by the installed `yt-dlp 2026.07.04`
>   (verified) though absent from its `--help`. On an HLS manifest, therefore, the example
>   does not fire, and a merge child is contingent on the format yt-dlp selects. The
>   structural defect and the reproduction above are unaffected — the boundary is absent
>   whether or not this particular descendant happens to exist on this particular format.
> - **Severity:** HIGH, re-derived and unchanged. The report's own argument for not going
>   higher is accepted and re-checked: the process that holds the credential material is the
>   direct child (`--cookies` is passed to yt-dlp at `ytdlp_downloader.py:305`/`:308`), and
>   that one is killed. The surviving descendant holds an output file open and nobody can
>   address it.
> - **See also:** `TRN-012` (the same ladder, its return contract), `BRW-001`/`CON-004`
>   (phase 04 owns whether the driver stop is reached).

---
> **Retained source text — TRN-003.** *Type `[BEST-PRACTICE]`. Subject every spawn site:
> `ytdlp_downloader.py:631-635`, `downloader.py:305-309`, `ffmpeg_utils.py:297`,
> `ffmpeg_utils.py:344`, `browser.py:38` (the Playwright driver), `browser.py:40-43` (the
> browser).*
>
> **What was observed.** An AST survey of the whole source tree finds five process-creating
> call sites and no boundary around any of them. Searching the whole tree for
> `start_new_session`, `setsid`, `process_group`, `CREATE_NEW_PROCESS_GROUP`,
> `CREATE_BREAKAWAY_FROM_JOB`, `creationflags`, `startupinfo`, `JobObject`,
> `AssignProcessToJobObject` and `taskkill` returns **no hit in any file**. The only thing
> addressed by the termination ladder is the direct child's own pid
> (`ffmpeg_utils.py:198-207`).
>
> A stub child that records its own pid, starts a process of its own choosing, records that
> pid too, and sleeps was driven once per exit path through `_download_with_ytdlp`. After the
> parent's method returned, every recorded pid was probed against the process table:
>
> | Exit Path | Direct child | Grandchild alive after return |
> | --- | --- | --- |
> | success (exit 0) | reaped | **yes** |
> | non-zero exit (3) | reaped | **yes** |
> | cancellation (stop set, child killed) | killed | **yes** |
>
> Survivor count: 1 per path, in every run. On the cancellation path the direct child was
> signalled and the process it had started for itself was not — the ladder addresses one pid of
> the two the run created, and no boundary exists that could reach the other.
>
> The Playwright driver was observed from the operating system while the real driver was
> started: a direct child of the application process, `node.exe …playwright\driver\package\
> cli.js run-driver`, inside no boundary, and only `playwright.stop()` (`browser.py:87`) ever
> addresses it.
>
> **Failure scenario.** `Ctrl+C` during a download, or a stop set by the batch coordinator.
> `cancel_subprocess` terminates the yt-dlp child; the muxer that yt-dlp started to merge the
> streams keeps running, holding the output file open. Nothing in the application can address
> it: the ladder knows one pid, and there is no process group, session or job object to search.
> The batch coordinator's concurrency accounting is meanwhile free to start the next video.
>
> **Why not CRITICAL.** The CRITICAL condition — an external process outliving the command
> *holding a credential* — was evaluated against the observed route and is not met: the process
> that holds the credential material is the direct child (yt-dlp is the one given `--cookies`),
> and that one is killed. The surviving descendant is recorded and addressed by nobody. HIGH
> is the composed severity.

---

### TRN-004: HIGH — A reader failure becomes the verdict, and the reaper can then never return

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced, and this run's measurement is **stronger** than the report's: the
>   wait does not merely fail to return while the child runs, it does not return **after the
>   child is killed**.
>   ```
>   [TRN-004] child pid=23252
>   [TRN-004] reader done=True error=ValueError('Separator is not found, and chunk exceed the
>              limit') lines_yielded=0
>   [TRN-004] process.wait() DID-NOT-RETURN-WITHIN-8s AFTER KILL -> parent wedged
>   ```
>   The reader's bound was read off the object the product reads, not assumed:
>   `asyncio.streams._DEFAULT_LIMIT = 65536`, and no spawn call in the tree passes `limit=`
>   (searched). `stream.readline()` at `ffmpeg_utils.py:60` is unbounded, so a single line
>   above 64 KiB raises `ValueError` out of `iter_process_lines` (`ffmpeg_utils.py:55-63`),
>   which propagates through `read_progress` (`ffmpeg_utils.py:160`) and through the
>   `_monitor_progress` / `_drain_stderr` closures at `downloader.py:337-352` or
>   `ytdlp_downloader.py:661-669`.
>   **The reaper mechanism, verified in the standard library rather than inferred.** On
>   CPython 3.12.1 (this environment), `asyncio.base_subprocess.BaseSubprocessTransport._wait()`
>   returns its result only from `_call_connection_lost`, which is reached only from
>   `_try_finish()`, which requires `self._returncode is not None` **and** every pipe to be
>   `disconnected`. A reader that dies mid-stream leaves the transport paused with data
>   undrained, the pipe never reaches EOF, `_try_finish()` never completes, and
>   `process.wait()` is structurally incapable of returning. `ytdlp_downloader.py:681-682`
>   and `downloader.py:370-371` both await it with no bound.
>   The consequence the report names is therefore not "slow" but **permanent and
>   unrecoverable**: the parent emits no verdict of any kind — not a failure, not a
>   cancellation, not a completion — and cannot be interrupted by the wait, since killing the
>   child does not release the pipe.
> - **Severity:** HIGH, re-derived and unchanged, on the strengthened evidence.
> - **See also:** `TRN-005`, `TRN-006` (three independent routes into the same wedge),
>   `TRN-007` (the unbounded wait that carries it).

---
> **Retained source text — TRN-004.** *Type `[BEST-PRACTICE]`. Subject
> `ffmpeg_utils.py:29-63` (`iter_process_lines`; `readline()` at `:60`, no `limit=` anywhere —
> the token does not appear in any spawn call in the tree), `ytdlp_downloader.py:671-682`,
> `downloader.py:328-371`.*
>
> **What was observed.** The reader's size bound is the `asyncio.StreamReader` default, read
> off the object the product reads: **65 536 bytes**, never set by the application. A child
> that writes one line of 1 MiB and then stops:
> ```
> parent_outcome: DID-NOT-RETURN-WITHIN-WALL-CLOCK      (15 s wall clock, 20.0 s elapsed)
> parent_log_has_verdict: false                          (only "starting_ytdlp_download")
> reader_declared_bound_bytes: 65536
> reader_lines_yielded: 0
> reader_error: ValueError: Separator is not found, and chunk exceed the limit
> ```
> The child's own bytes were not consumed, no progress was reported, and **no verdict of any
> kind was produced** — not a failure, not a cancellation, not a completion.
>
> **Failure scenario.** The reader raises, so `output_chunks` stops growing, so the child
> eventually blocks writing to a pipe nobody drains, so `process.wait()` — which on this
> platform is not signalled until the output pipe reaches end of stream — never returns. The
> unbounded `await process.wait()` at `ytdlp_downloader.py:681-682` therefore never returns
> either. The call hangs indefinitely and the caller cannot tell a slow download from a wedged
> one. The same shape exists on the muxer side at `downloader.py:370-371`.

---

### TRN-005: HIGH — The muxer's reader stops at its own end-of-stream marker; the re-wait behind it never returns

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced end to end through the product's own reader and its own completion
>   helper, with this run's numbers matching the report's closely:
>   ```
>   [TRN-005] yielded=2 collected=42B tail_present=False child_running=True
>   [TRN-005] helper returned after 0.031s; child_returncode=None (child STILL RUNNING)
>   [TRN-005] unbounded re-wait DID-NOT-RETURN-WITHIN-6s
>   ```
>   (the report records `completion_helper_returned_after_s: 0.033`).
>   **Truncation half confirmed and deterministic.** The child wrote a `progress=end` marker and
>   then `TAIL-1`, `TAIL-2`. The `stderr_collector` received **42 bytes** and the tail is not
>   in it. The end condition is `ffmpeg_utils.py:174-175` — `yield progress` then `if value ==
>   "end": break` — so the point at which the parent stops reading is fixed by the stream, not
>   racy. `ffmpeg_download_failed` (`downloader.py:388-395`) therefore reports a prefix of what
>   the muxer actually said.
>   **Why the helper returns early.** `_await_first_and_cancel_others`
>   (`ytdlp_downloader.py:86-108`) waits `FIRST_COMPLETED` and cancels the rest. The monitor
>   task completes at the marker, so the `process.wait()` task is cancelled while the child is
>   alive; `downloader.py:370-371` then performs the second, unbounded `await process.wait()`.
>   The code's own comment at `downloader.py:354-358` anticipates the re-wait but does not
>   bound it.
> - **Severity:** HIGH, re-derived and unchanged.
> - **See also:** `TRN-004`, `TRN-006` (the same wedge by a different route), `TRN-007`.

---
> **Retained source text — TRN-005.** *Type `[BEST-PRACTICE]`. Subject
> `ffmpeg_utils.py:174-175` (`break` on `progress=end`), `downloader.py:354-371` (the re-wait
> the code's own comment anticipates), `ytdlp_downloader.py:86-108` (the helper that cancels
> the wait task).*
>
> **What was observed.** `read_progress` yields one object and then **breaks out of its loop**
> when it sees `progress=end`, so the reader task completes while the child is still running;
> `_await_first_and_cancel_others` cancels the wait task; and the code then performs a second,
> unbounded `await process.wait()`. A real child process writing that stream, through the
> product's own reader and its own completion helper:
> ```
> completion_helper_returned_after_s: 0.033
> child_still_running_when_helper_returned: true
> unbounded_rewait_outcome: DID-NOT-RETURN-WITHIN-15s
> ```
> With ordinary post-marker output — the marker, then 32 MiB:
> ```
> bytes_collected_before_the_marker: 60
> completion_helper_returned_after_s: 0.033
> unbounded_rewait_outcome: DID-NOT-RETURN-WITHIN-10s
> child_still_alive_at_the_end: true
> ```
> The child blocks on a full pipe that the product has stopped draining, and the re-wait has no
> bound to release it.
>
> **Failure scenario.** Any muxer message after its last progress block — an error, a warning,
> a trailer — larger than a pipe buffer deadlocks the download. The caller is never told;
> `download_with_ffmpeg` never returns.
>
> **The same reader also truncates deterministically.** The child wrote 4 109 bytes of tail
> plus a further `frame=2` line after the marker; the product's own `stderr_collector` received
> **60 bytes**, ending exactly at `progress=end` (`tail_present_in_collected_buffer: false`,
> `lines_after_the_marker_present: false`). The point at which the parent stops reading is fixed
> by the stream, so the truncation is certain rather than racy: `ffmpeg_download_failed`
> (`downloader.py:388-395`) reports a prefix of what the muxer actually said. Recorded here as
> part of the same defect — the reader's end condition is the wrong one.

---

### TRN-006: HIGH — A non-numeric value on the muxer's progress stream kills the reader, and the exception is swallowed

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced.
>   ```
>   [TRN-006] reader DIED ValueError: invalid literal for int() with base 10: 'abc' yielded=0
>   [TRN-006] handler['frame'] = <function <lambda> at 0x...>
>   ```
>   `_PROGRESS_KEY_HANDLERS["frame"]` (`ffmpeg_utils.py:112`) is
>   `int(v) if v != "N/A" else None`; the loop at `ffmpeg_utils.py:160-170` calls it unguarded
>   and has no `try`. The `ValueError` leaves `read_progress`, the task dies, and
>   `_await_first_and_cancel_others` (`ytdlp_downloader.py:97-108`) returns the failed task in
>   `done` and re-raises nothing — no caller inspects it, so the failure produces no log record
>   and no exception, exactly as filed. The state reached is `TRN-005`'s.
>   **The contrast the report draws is confirmed.** `_parse_ytdlp_progress`
>   (`ytdlp_downloader.py:145-195`) is regex-guarded: `_YTDLP_PROGRESS_RE` requires
>   `\d+(?:\.\d+)?` before the unit, so both a non-numeric percentage and the protocol's own
>   `N/A` size return `None` (`.search()` → `match is None` → `return None` at `:186-188`).
>   **One correction to the failure scenario's likelihood argument.** The scenario says the
>   trigger is "one of the value kinds the protocol itself permits". That overstates it: the
>   handlers **do** guard the protocol's own placeholder — every entry in
>   `_PROGRESS_KEY_HANDLERS` (`ffmpeg_utils.py:111-119`) tests `v != "N/A"` before converting,
>   so `N/A` is handled on every key. The residual trigger is a value that is neither numeric
>   nor the literal `N/A` — a future or alternate build, or a malformed line. That lowers the
>   trigger's likelihood; it does not change the failure mode, which is the silent wedge.
> - **Severity:** HIGH, re-derived and unchanged. The mechanism and its consequence are
>   identical to `TRN-005`'s, and the route into it is real even if narrow.
> - **See also:** `TRN-005` (the same wedge), `TRN-007`.

---
> **Retained source text — TRN-006.** *Type `[BEST-PRACTICE]`. Subject
> `ffmpeg_utils.py:111-119` (`_PROGRESS_KEY_HANDLERS`: `int(v)` / `float(v)`),
> `ffmpeg_utils.py:160-177` (the loop that calls them),
> `ytdlp_downloader.py:86-108` (`_await_first_and_cancel_others`).*
>
> **What was observed.** One progress line, `frame=abc`, from a real child process into the
> product's own reader:
> ```
> muxer_reader_state_after_2s: done
> muxer_reader_error: ValueError: invalid literal for int() with base 10: 'abc'
> muxer_reader_yielded: []
> muxer_child_still_alive: true
> child_rewait_outcome: DID-NOT-RETURN-WITHIN-5s
> ```
> The reader task dies. `_await_first_and_cancel_others` returns the failed task in `done` and
> re-raises nothing; no caller inspects it, so the failure produces no log record and no
> exception. The result is the same wedged state as TRN-005, reached from a different cause.
>
> For contrast, the downloader's progress parser on the same surface is regex-guarded and
> returns `None` for both a non-numeric percentage and the protocol's own `N/A` placeholder:
> ```
> ytdlp_non_numeric_pct: null        ("[download]  abc% of 10.00MiB at 1.00MiB/s ETA 00:09")
> ytdlp_placeholder_size: null       ("[download]   1.0% of N/A at 1.00MiB/s ETA 00:09")
> ```
>
> **Failure scenario.** The muxer emits one `key=value` line whose value is not a bare number
> — the value kinds the protocol itself permits, and anything a future or alternate build
> adds. The reader dies silently, the child is never drained, and `download_with_ffmpeg` never
> returns.

---

### TRN-007: MEDIUM — The re-wait after output consumption carries no bound of its own

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced.
>   ```
>   [TRN-007] re-wait DID-NOT-RETURN-WITHIN-6s (child produced output and did not exit)
>   ```
>   A child emitting a well-formed yt-dlp progress line and then not exiting leaves
>   `ytdlp_downloader.py:681-682` waiting indefinitely. Read and confirmed: that `await
>   process.wait()` carries no `asyncio.wait_for`, and neither does its twin at
>   `downloader.py:370-371`.
>   **The contrast against the bounded path is exact.** `_await_ffmpeg_with_timeout`
>   (`ffmpeg_utils.py:217-242`) wraps `process.communicate()` in
>   `asyncio.wait_for(..., timeout=timeout)` and takes its bound from the `download_timeout`
>   parameter (`:238`); the two download paths have no equivalent. So the report's claim — the
>   merge transport is bounded and the download transports are not — is correct as filed.
>   **The distinction from `NET-007` is correct and is kept.** `NET-007` (phase 03) records a
>   documented decision that no whole-operation budget is imposed
>   (`ytdlp_downloader.py:580-582`); this is the narrower wait after output consumption. They
>   are complement, not duplicate — `99-audit-validate.md` §5(b).
> - **Severity:** MEDIUM, re-derived and unchanged on its own account. Its weight in the
>   report comes from what it enables: once a reader has stopped (`TRN-004`, `TRN-005`,
>   `TRN-006`), this wait is the only thing that could release the child, and it has no bound.
>   That relationship is recorded in `VAL-502` rather than inflating this row.
> - **See also:** `TRN-004`, `TRN-005`, `TRN-006`; `NET-007` (phase 03, the documented
>   decision this is not a re-file of).

---
> **Retained source text — TRN-007.** *Type `[BEST-PRACTICE]`. Subject
> `ytdlp_downloader.py:681-682`, `downloader.py:370-371`; contrast `ffmpeg_utils.py:238`.*
>
> **What was observed.** A child that emits its output and then never exits:
> ```
> parent_outcome: DID-NOT-RETURN-WITHIN-15s
> child_alive_after: [<pid>]      (killed by the harness afterwards)
> parent_log: only "starting_ytdlp_download" and one debug progress record
> ```
> The same operation for the merge transport is bounded: `ffmpeg_utils.py:238` wraps
> `process.communicate()` in `asyncio.wait_for(..., timeout=timeout)` with `download_timeout`.
> The download paths carry no equivalent. Each call is individually unbounded; the observed
> wall clock is 15 s against a wait designed to have no limit.
>
> **Failure scenario.** Any child that produces output and does not exit — a stalled connection
> held open by a server, a merged process waiting on a lock — holds the download open for as
> long as it likes, and nothing in the call can end it. This row is the structure that turns
> TRN-004, TRN-005 and TRN-006 from "slow" into "permanent": once the reader has stopped, the
> only thing that could release the child is this wait, and it has no bound.
>
> **Not re-filed from NET-007.** NET-007 records the deliberate absence of a whole-operation
> download budget (`ytdlp_downloader.py:580-582`). This finding is the narrower case: the
> wait that follows output consumption, with the child already finished, carries no bound of
> its own.

---

### TRN-008: MEDIUM — The discovery probe's answer is discarded; a missing dependency changes no branch and surfaces three different ways

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced and confirmed by reading, including the report's most important
>   detail.
>   **The caller discards the answer.** `check_ffmpeg_available` has exactly one call site in
>   `src/` — `downloader.py:468`, the bare expression statement `check_ffmpeg_available()`
>   inside `perform_download` — verified by searching the whole package. Read off the
>   function's own source: `['check_ffmpeg_available()']`. No branch anywhere depends on the
>   value; the function returns `bool` and the return is dropped.
>   **The answer is cached and never re-derived.** `ffmpeg_utils.py:78-89`:
>   ```
>   if _ffmpeg_available is None:
>       _ffmpeg_available = shutil.which("ffmpeg") is not None
>   ```
>   Measured on this machine: `probe 1st=True 2nd=True which=True`; the module cache reads
>   `True` and is only re-derived when it is `None`. A machine that loses the muxer
>   mid-session keeps the cached `True` and emits no further warning.
>   **The three surfacings are as filed.** A missing muxer on the muxer path raises
>   `FileNotFoundError` from `downloader.py:305`; on the merge path the same raw error escapes;
>   on the downloader path a missing module is caught at `ytdlp_downloader.py:707-714` and
>   recorded as `download_failed`. The resume path's mislabelling is confirmed by reading
>   `ytdlp_downloader.py:547-551` (`except (ExtractionError, OSError)` catches the merge's
>   `FileNotFoundError`, which is an `OSError`, and logs it as `failed_to_refresh_token`) —
>   and the merge docstring at `ffmpeg_utils.py:470-478` says exactly this about itself, so
>   the row is corroborated by the code it names.
>   **The ENT-001 dependency is real.** The only actionable text anywhere is the
>   `ffmpeg_not_found` warning at `ffmpeg_utils.py:82-88`, and per phase 01's `ENT-001` that
>   warning frequently reaches the console instead of the configured log file. Cross-referenced,
>   not re-filed.
> - **Severity:** MEDIUM, re-derived and unchanged. A missing dependency surfaces as an opaque
>   traceback, or — worse — as a token problem the user will act on in the wrong direction.
> - **See also:** `TRN-001` (a present-but-unusable muxer is a different failure of the same
>   dependency, and produces *no* warning at all); `ENT-001` (phase 01, where the warning goes).

---
> **Retained source text — TRN-008.** *Type `[BEST-PRACTICE]`. Subject
> `ffmpeg_utils.py:66-89` (the probe and its cache), `downloader.py:466-468` (the only caller;
> the return value is discarded), `ytdlp_downloader.py:547-551` (the resume path's
> `except (ExtractionError, OSError)`), documented in the merge docstring at
> `ffmpeg_utils.py:474-478`.*
>
> **Probe's answer, and whether it re-probes.** One fresh process, a binary ahead on the search
> path, then the machine changed under it:
> ```
> {"first": true, "second": true, "machine_changed": true,
>  "which_after_change": null, "third": true, "muxer_dirs_removed": ["C:\\ffmpeg"]}
> ```
> Two calls both answer from the real lookup path; the third still answers `True` after the only
> muxer on the machine was removed from `PATH` and `shutil.which("ffmpeg")` returns `null`. A
> fresh process whose `PATH` holds no muxer answers `{"which": null, "probe": false}` with one
> `ffmpeg_not_found` warning. The answer is cached for the process and never re-derived.
>
> **Whether the caller's branch changes.** With the probe forced to return `False`, the muxer
> path runs identically and still spawns: `{"probe_returned": false, "outcome": "returned
> None"}`. `downloader.py:468` calls the probe and throws the answer away. There is one caller
> in the tree; no branch anywhere depends on the value.
>
> **What the absence actually does, captured verbatim.** The probe's answer was asserted
> `False` **before** each run, never after.
> - Muxer transport, no muxer on the search path — the process exit status and the tail of the
>   traceback: `process_exit_status: 1`, ending `FileNotFoundError: [WinError 2] The system
>   cannot find the file specified` raised from `downloader.py:305`.
> - Merge transport, same conditions — `ESCAPED=FileNotFoundError: [WinError 2] …`,
>   `process_exit_status: 1`.
> - Downloader transport, module not importable — the child exits 1 and the parent records it
>   and returns `None`: `download_failed … error="ModuleNotFoundError: No module named 'yt_dlp'"`.
>
> One absence, three surfacings: a raw traceback with exit 1, the same raw traceback, and a
> structured failure record. At the CLI a traceback is caught by `cli.py:221-224` and reduced to
> "An error occurred during download". Worse, on the resume path the merge's
> `FileNotFoundError` is an `OSError` and is caught by `except (ExtractionError, OSError)` at
> `ytdlp_downloader.py:547-551` — the swallow the merge docstring at
> `ffmpeg_utils.py:474-478` describes in its own words ("which would swallow a
> FileNotFoundError here, relabel it `failed_to_refresh_token` and return None, losing the
> message") — so the missing muxer is reported to the user as `failed_to_refresh_token`.
>
> **Failure scenario.** ffmpeg is not installed. Every download that needs it either fails with
> an opaque traceback or is reported as a token problem. The only actionable text anywhere is
> the one `ffmpeg_not_found` warning the probe emits — and per ENT-001 that warning is
> frequently written to the console instead of the log file the operator is asked to read. A
> machine that loses ffmpeg mid-session keeps the cached `True` and produces none of it.

---

### TRN-009: MEDIUM — The redaction cannot match a filesystem path, and the terminal echo applies none

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Every row of the transform table was reproduced against the product's own
>   `sanitize_text_for_log`, and the report's table is exact. One row was added by this run
>   from `TRN-001`'s own evidence:
>   ```
>   [TRN-009] absolute URL with a token:      changed=True   -> https://cdn.vkvideo.ru/***REDACTED***
>   [TRN-009] filesystem path:                changed=False
>           C:\Users\operator\AppData\Local\Temp\vk_cookies_ab12cd34.cookies.txt  (unchanged)
>   [TRN-009] argument fragment --cookies:    changed=False   (unchanged)
>   [TRN-009] argument fragment with a URL:   changed=True    (URL part only)
>   [TRN-009] error text with URL in brackets: changed=True   (URL part only)
>   [TRN-009] muxer echo of the argfile path: changed=False   (ADDED by this run)
>           Error opening output file @C:\Users\op\AppData\Local\Temp\vk_ffmpeg_i_r7iyso.args.
>   ```
>   The mechanism is as filed: `sanitize_text_for_log` (`url_sanitizer.py:33-47`) is a single
>   `_URL_REGEX.sub` over `https?://[^\s'\"<>]+` (`url_sanitizer.py:8`). It has no alternative
>   branch, so a shape that is not a URL cannot match. The two call sites' comments at
>   `ytdlp_downloader.py:691-693` and `downloader.py:385-387` both claim it redacts "signed CDN
>   URLs **or cookie file paths**"; the first half is true and the second is not.
>   **The sink table is confirmed by reading** at `ytdlp_downloader.py:227` and `:224` (the
>   echo path writes to `sys.stderr` with no transform), `ffmpeg_utils.py:311`
>   (`batch_merge_failed`, `error[:200]` of raw stderr) and `:363` (`final_merge_failed`,
>   `stderr.decode()[:200]`).
>   **One anchor correction.** The `Subject` cites `url_sanitizer.py:13-24` for the transform.
>   That range is `_strip_auth_params`'s docstring and first statements; the transform is the
>   regex at `url_sanitizer.py:8` and `sanitize_text_for_log` at `:33-47`. The report's own
>   body cites `:8` correctly, so this is a drifted `Subject` line, not a wrong claim.
>   **Ownership boundary respected.** Whether a filesystem path is a secret is phase 06's
>   judgement (`SEC-004`, `SEC-006`). This row owns the mechanism and the enumeration only,
>   as the report itself scopes it.
> - **Severity:** MEDIUM, re-derived and unchanged. The report's own restraint is correct and
>   kept: the exposure judgement is not this phase's to make, but the mechanism gap is.
> - **See also:** `SEC-005` / `SEC-006` (phase 06, the exposure and the credential artefact);
>   `TRN-001` (the row added above is `TRN-001`'s own child output arriving unredacted).

---
> **Retained source text — TRN-009.** *Type `[SPEC-DEVIATION]`. Subject
> `url_sanitizer.py:13-24` (corrected above to `:8` and `:33-47`); the sites
> `ytdlp_downloader.py:691-695` and `downloader.py:385-390` (both comment that the transform
> redacts "signed CDN URLs **or cookie file paths**"), `ytdlp_downloader.py:198-228` (the echo
> path, no transform), `ffmpeg_utils.py:311` and `ffmpeg_utils.py:363` (no transform).*
>
> **The transform, against a declared corpus.**
>
> | Input | Changed | Result |
> | --- | --- | --- |
> | absolute URL with a token | yes | `https://cdn.vkvideo.ru/***REDACTED***` |
> | filesystem path | **no** | `C:\Users\operator\AppData\Local\Temp\vk_cookies_ab12cd34.cookies.txt` unchanged |
> | argument fragment `--cookies <path>` | **no** | unchanged |
> | plain text | no | unchanged |
> | argument fragment containing a URL | yes (URL part only) | `…Referer: https://cdn.vkvideo.ru/***REDACTED***` |
> | error text with a URL in brackets | yes (URL part only) | `[download]  Failed: https://cdn.vkvideo.ru/***REDACTED***` |
>
> The transform is a single regex over `https?://…` (`url_sanitizer.py:8`). It cannot match a
> filesystem path, and both call sites' comments say it does. On the muxer path the real child
> output proves the gap end to end: the temp response-file path
> `C:\Users\NMATVE~1\AppData\Local\Temp\vk_ffmpeg_i_r7iyso.args` reaches
> `ffmpeg_download_failed` verbatim, through the transforming site.
>
> **The same bytes on two surfaces.** One stub child, driven end to end through
> `_download_with_ytdlp` with the echo path on and a cookie file present:
> - *Terminal* (`_echo_ytdlp_line` → `sys.stderr`, no transform):
>   `STUB-ARGV … --cookies C:\Users\NMATVE~1\AppData\Local\Temp\vk_cookies_undexud6.cookies.txt https://vkvideo.ru/video-1_2?sign=SYNTHETICTOKEN123&exp=9999999999`
> - *Log record* (`download_failed`, `sanitize_text_for_log`):
>   `error='STUB-ARGV … --cookies C:\\Users\\NMATVE~1\\AppData\\Local\\Temp\\vk_cookies_undexud6.cookies.txt https://vkvideo.ru/***REDACTED*** …'`
>
> The URLs are redacted in the log; the cookie file path survives in both. The terminal write is
> a second surface for the same bytes with a different rule applied to it.
>
> **Every site where child output becomes a log record, a terminal write or a stored buffer:**
>
> | Site | Transform |
> | --- | --- |
> | `ytdlp_downloader.py:227` (terminal, echo on) | none |
> | `ytdlp_downloader.py:224` (terminal, progress rewrite) | none |
> | `ytdlp_downloader.py:694-696` (log record) | `sanitize_text_for_log` |
> | `downloader.py:388-390` (log record) | `sanitize_text_for_log` |
> | `ffmpeg_utils.py:311` (`batch_merge_failed`) | none (`error[:200]`) |
> | `ffmpeg_utils.py:363` (`final_merge_failed`) | none (`stderr.decode()[:200]`) |
> | `ytdlp_downloader.py:655`, `:669`; `ffmpeg_utils.py:164`; `downloader.py:352` (stored buffers) | none; consumed by the sites above |
>
> **Failure scenario.** yt-dlp echoes its own invocation, or the muxer echoes the path it was
> handed. The signed URLs are stripped on the log path and not on the terminal path; the cookie
> file path is stripped on neither, despite the two comments saying so. Whether a path is a
> secret is phase 06's judgement; the mechanism — a transform that cannot match the shape this
> site carries, applied at some sinks and not at others — is this phase's.
>
> **Cross-reference, not re-filed.** Phase 06's validator recorded that SEC-005's surface table
> omits `ffmpeg_utils.py:310-311` and `:363`. This phase reached them independently, from the
> muxer transport's own evidence, and adds them to the table rather than restating SEC-005.

---

### TRN-010: MEDIUM — The two transports carry different vectors, and only one has any concealment mechanism

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by reading the two builders and the spawn sites, and — for the
>   concealment claim — falsified in its strong form by `TRN-001`.
>   **The vectors are as filed.** `_build_ytdlp_cli_command` (`ytdlp_downloader.py:231-310`)
>   appends `--cookies <path>` at `:305`/`:308`, and `_download_with_ytdlp` appends the media
>   URL as the final positional argument at `:623`. The muxer side is the two tokens
>   `['ffmpeg', '@<argfile>']` at `downloader.py:302-309`, re-measured by this run through a
>   spawn spy: `LIFETIME: {'exists_at_spawn': True, 'argv': ['ffmpeg',
>   '@C:\\…\\vk_ffmpeg_5ibpa5vu.args']}`.
>   **The environment claim is confirmed.** Searching `src/` for `env=` and `cwd=` returns
>   **no match**. No spawn call narrows what the child inherits, and no `shutil.which` guard or
>   allow-list narrows the executable resolution.
>   **The argfile content claim is confirmed**, including the multi-line `-headers` value that
>   a line-oriented reader would split — snapshotted from the product's own `_temp_argfile`:
>   ```
>   "-y\n-progress\npipe:2\n-nostats\n-headers\n
>    'User-Agent: UA\r\nReferer: https://vkvideo.ru/\r\n'\n-i\n
>    'http://127.0.0.1:9/x.m3u8?sign=TOK'\n-c\ncopy\nout.mp4\n"
>   ```
>   The report is right that this survives the `TRN-001` fix and should be corrected in the
>   same change.
>   **The "one transport conceals" claim does not survive.** With `TRN-001` established,
>   neither transport conceals anything: the ffmpeg transport's concealment protects values
>   that are never transmitted. The *asymmetry* the report describes is therefore real as a
>   statement about the code's declared intent and false as a statement about achieved
>   concealment. The row is kept — the declared intent is stated at `downloader.py:96-99` and
>   `downloader.py:258-261` and one transport honours it while the other never claimed to —
>   but the scope is narrowed to match `TRN-001`'s evidence.
>   **The cross-reference note is directionally correct and under-specified.** The report says
>   "`SEC-001`'s asymmetry argument weakens once `TRN-001` is fixed, because the concealment
>   the muxer transport claims turns out not to work: whichever transport is changed, the
>   other has to follow." Judged on this run's evidence: the judgement holds **only if**
>   `TRN-001` is repaired by moving the arguments onto the command line, which is the only
>   repair available on a muxer that has neither `@file` nor `-/opt`. Under that repair the
>   ffmpeg transport's argv would carry the signed m3u8 URL and the cookie-file path, the
>   asymmetry would collapse into uniform exposure, and `SEC-004`'s framing ("one transport
>   satisfies the stated intent, therefore the other should too") would no longer be
>   supportable. Under any repair that keeps a working indirection the asymmetry stands as
>   filed. The note is recorded as **conditional**, not as a settled conclusion.
> - **Severity:** MEDIUM, re-derived and unchanged. The two findings' fixes must be chosen
>   together; that coupling is filed as `VAL-502` rather than raised here.
> - **See also:** `TRN-001` (the concealment is vacuous today), `SEC-001`/`SEC-004` (phase 06,
>   the credential side and its asymmetry argument), `VAL-501`, `VAL-502`.

---
> **Retained source text — TRN-010.** *Type `[BEST-PRACTICE]`. Subject
> `ytdlp_downloader.py:260-299` + `:301-317` + `:623` (the downloader vector),
> `downloader.py:92-124` + `:302-309` (the muxer vector), the spawn calls at
> `ytdlp_downloader.py:631-635`, `downloader.py:305-309`, `ffmpeg_utils.py:297`,
> `ffmpeg_utils.py:344`.*
>
> **Both vectors, read off the objects that produce them.** The builder called directly with a
> synthetic media URL and a synthetic credential path:
> ```
> [python.exe, -u, -m, yt_dlp, --encoding, utf-8, -o, <out>, -f, best[height<=720],
>  --newline, --hls-prefer-native, --no-warnings, --socket-timeout, 300, -R, 3,
>  --fragment-retries, 3, -N, 4, --throttled-rate, 100000, --user-agent, <ua>,
>  --referer, https://vkvideo.ru/, --cookies, C:\...\vk_cookies_f1qhfhyn.cookies.txt,
>  https://vkvideo.ru/video-1_2?sign=SYNTHETICTOKEN123&exp=9999999999]
> ```
> `media_url_is_in_vector: true`, `cookie_file_path_is_in_vector: true`. The URL is appended by
> the caller at `ytdlp_downloader.py:623`, not by the builder.
>
> The muxer vector, captured while the child received it: `["ffmpeg", "@<argfile>"]` — neither
> form appears. The response file's real contents, snapshotted while the file existed:
> ```
> -y
> -progress
> pipe:2
> -nostats
> -headers 'User-Agent: …\n\nReferer: https://vkvideo.ru/\n\n'
> -i 'https://vkvideo.ru/video-1_2?sign=SYNTHETICTOKEN123&exp=9999999999&cookies=file:C:\Users\NMATVE~1\AppData\Local\Temp\vk_cookies_cl_r82ea.cookies.txt'
> -c
> copy '<output>'
> ```
> `media_url_in_response_file: true`, `credential_path_in_response_file: false` for the
> standalone call; with a cookie file the credential path is inside the file too. So one
> transport conceals and the other does not — the two halves of the same decision, applied to
> one transport only.
>
> A second structural observation from the same snapshot: the multi-line `-headers` value is
> written as one argument, but the response file is line-oriented, so the value would be split
> across three lines by any reader of that format. Moot while TRN-001 stands; recorded because
> it survives the fix.
>
> **The child's inheritance.** The child was asked what it received and diffed against the
> parent, key by key:
> ```
> parent_key_count: 115, child_key_count: 116
> keys_only_in_child: ["VKD_PROBE_MARKER"]      (set by the harness as a marker)
> keys_only_in_parent: []
> keys_with_different_values: []
> inherited_probe_marker: "set-by-parent"
> child_cwd == parent_cwd
> ```
> The full environment is inherited unchanged and the working directory is inherited; no spawn
> call in the tree passes `env=` or `cwd=`. Nothing narrows what the child can see.
>
> **Failure scenario.** On a shared or locked-down host, every value the application holds for
> the child — proxy configuration, tokens in the environment, the working directory's meaning —
> is handed over wholesale, while the mechanism the code relies on to hide the download
> arguments exists on only one of the two transports.
>
> **Cross-reference, not re-filed.** SEC-001 (phase 06) reaches the same asymmetry from the
> credential side: the cookie-file path is argv element 28 of 30 on the downloader transport
> while its ffmpeg sibling uses a response file. That finding owns the artefact's permissions
> and lifetime; this one owns only the divergence between the two vectors, and its fix is the
> same shape — give the downloader transport the mechanism the muxer transport claims to
> have. Note that SEC-001's asymmetry argument weakens once TRN-001 is fixed, because the
> concealment the muxer transport claims turns out not to work: whichever transport is changed,
> the other has to follow.

---

### TRN-011: MEDIUM — Child output is accumulated without a bound

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced, with the amplification re-measured rather than inherited.
>   ```
>   [TRN-011] sanity rss()=59834368 (non-zero => the probe works)
>   [TRN-011] child_bytes=52429000 (50.0 MiB)
>   [TRN-011] rss_before=59834368 after_list=121290752 after_join=173727744
>   [TRN-011] growth=113893376 = 108.6 MiB = 2.17x the child's own output
>   ```
>   The report records `106.6 MiB for 50 MiB of child output` (2.13×). This run measured 108.6
>   MiB (2.17×) — the same figure to within the noise of a different allocator path, so the
>   claim is confirmed rather than merely restated.
>   **The bound is structural, not incidental.** `output_chunks: list[bytes]`
>   (`ytdlp_downloader.py:637`) receives one append per line from both drain paths
>   (`:655` and `:669`) and is joined whole at `:684`, then decoded and transformed on failure
>   (`:694-695`). Nothing in the call caps it.
>   **The batching arithmetic in the scenario is checked and accepted.** `max_concurrent_
>   downloads` reads 4 from `Settings` on this machine and the finding states the accepted
>   maximum is 16; the amplification therefore multiplies across the batch. The report is right
>   that `echo=False` discards these lines (`_echo_ytdlp_line` returns early at
>   `ytdlp_downloader.py:211-220`), so the memory is spent on output nobody asked to see.
> - **Severity:** MEDIUM, re-derived and unchanged. Bounded, not unbounded — the child's own
>   output size is the ceiling — and it degrades rather than corrupts.
> - **See also:** `TRN-005` (the tail-truncation that means the buffer is also the wrong
>   record of what the child said).

---
> **Retained source text — TRN-011.** *Type `[BEST-PRACTICE]`. Subject
> `ytdlp_downloader.py:637` (`output_chunks: list[bytes]`), `:655`, `:669`, `:684`
> (`b"".join(output_chunks)`).*
>
> **What was observed.** A child writing 50 MiB on one stream, with `echo=False` so that
> nothing is displayed at all:
> ```
> child_bytes_written: 52428800
> peak_working_set_before_bytes: 60948480
> peak_working_set_after_bytes:  172707840
> peak_growth_bytes:           111759360        (106.6 MiB for 50 MiB of child output)
> outcome: returned <output path>
> ```
> The bound is the child's own output size, and the amplification is the list-of-chunks plus
> the join, measured at roughly 2×. Nothing in the call bounds it; the list grows for the whole
> life of the download, and on failure the joined buffer is decoded and then transformed,
> adding two more copies.
>
> **Failure scenario.** A chatty child (verbose errors, a long warning block) in a batch run
> multiplies the peak by the concurrency: `max_concurrent_downloads` defaults to 4 and is
> accepted up to 16, so 16 concurrent downloads of a 50 MiB-output child cost the process on
> the order of 1.7 GiB of working set for output nobody asked to see — the echo path
> discarded every one of those lines.

---

### TRN-012: MEDIUM — The termination ladder reports "not clean" for a process that is already gone

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced exactly, including the return sequence the report tabulates.
>   ```
>   [TRN-012] cancel_subprocess returns = [True, False, False]; proc.returncode=1
>   ```
>   The report's table is `1st call → True`, `2nd call → False`, `3rd call → False`, and this
>   run's three consecutive calls on one handle give exactly `[True, False, False]`.
>   **The `False` arm is identified correctly.** `cancel_subprocess` (`ffmpeg_utils.py:179-207`)
>   returns `False` only from `except ProcessLookupError` at `:206-207`, which fires precisely
>   when the handle has already been reaped. The report's reading is right that the call sites
>   invert the meaning: `downloader.py:321`, `:342`, `:376`, `:404`; `ytdlp_downloader.py:640`,
>   `:718` — each writes a `*_cancel_not_clean` warning with the pid on `False`.
>   **The composition claim is confirmed by reading, exactly as the report itself scopes it.**
>   `downloader.py:375-381` calls `cancel_subprocess(process)` unconditionally in the stop
>   branch, after `_on_shutdown` at `:320-326` has already cancelled the same handle through
>   the reader. The second call returns `False` and the warning is logged for a process the
>   first call already terminated. The report marks this **partial** and this run agrees with
>   that marking: the two components are established, the end-to-end log line was not driven,
>   and the report is candid that the real muxer exits in ~30 ms (`TRN-001`) so the stop
>   branch is not reached with a live child. **No correction is entered here** — the evidence
>   quality marker the report applies is the right one.
>   **One thing the report states that is worth keeping explicit:** the function's own
>   docstring (`ffmpeg_utils.py:193-194`) says *"True if process was cancelled, False if process
>   was already gone"*. The function is therefore **correct as documented**; the defect is
>   entirely in the call sites' reading of its contract. That distinction narrows the fix to
>   the call sites and is recorded so the remedy is not aimed at the wrong function.
> - **Severity:** MEDIUM, re-derived and unchanged. A false "not clean" warning on every
>   cancellation is diagnostic noise on a path that is already reporting a stop.
> - **See also:** `TRN-002` (the same ladder, whose caller is skipped entirely on a failed
>   destroy), `TRN-003` (the ladder's reach, one pid).

---
> **Retained source text — TRN-012.** *Type `[BEST-PRACTICE]`. Subject
> `ffmpeg_utils.py:179-207` (`cancel_subprocess`); the call sites that treat `False` as
> "still running": `ytdlp_downloader.py:640-645`, `ytdlp_downloader.py:717-723`,
> `downloader.py:320-326`, `downloader.py:341-347`, `downloader.py:375-381`,
> `downloader.py:403-409`.*
>
> **What was observed.** The ladder driven through each branch with a real handle, then twice
> more against the same handle, then against a dead one:
>
> | Case | Return | Raised |
> | --- | --- | --- |
> | 1st call, child alive then exits | `True` | — |
> | 2nd call, same handle, already exited | **`False`** | — |
> | 3rd call, same handle, already exited | `False` | — |
> | call against a long-lived child (`timeout=1.0`) | `True` | — |
>
> `False` is returned by the `except ProcessLookupError` arm at `ffmpeg_utils.py:206-207`,
> which fires precisely when the handle has already been reaped — that is, when the process is
> **already gone and the outcome is clean**. Every call site in the tree reads `False` as "not
> clean" and logs `*_cancel_not_clean` with the pid. A process that was never started cannot be
> constructed through the public API; that row is recorded as a gap.
>
> **Where the composition actually happens.** `downloader.py:375-381` calls
> `cancel_subprocess` unconditionally in the stop branch, after `_on_shutdown`
> (`downloader.py:320-326`) has already cancelled the same handle through the reader. The
> second call returns `False` and the warning is logged for a process that the first call
> already terminated.
>
> **Verification status: partial.** The second-call return value and the two call sites were
> both established, but the composition could not be driven end to end on this platform: the
> real muxer exits in about 30 ms (TRN-001), so the stop branch is not reached with a live
> child. Recorded as structure with the measured component, not as an observed log line.

---

### TRN-013: ~~LOW — One batch bound is a literal where configured values sit beside it~~ [REJECTED]

> **Rejection reason (ground: low value at this scale · stylistic preference).** The
> measurement is exact and is confirmed — `batch_size = 100` is a literal at
> `ffmpeg_utils.py:480`, the signature beside it takes `download_timeout: float = 300.0` at
> `ffmpeg_utils.py:452`, and `Settings` on this machine reports
> `download_timeout=300, max_concurrent_downloads=4, max_retries=3`. What fails is the fourth
> criterion, operational value, and the evidence for the rejection is stronger than the
> evidence for the finding:
>
> 1. **There is no defect behind the observation.** The stated consequence — "a user on a slow
>    link or with a memory-constrained host cannot raise the merge batch smaller" — names
>    nothing that goes wrong. `download_timeout` already bounds each batch's merge
>    (`ffmpeg_utils.py:238`), and `_check_merge_space` (`:398-448`) already accounts for the
>    2×-plus-margin the merge needs (`:367-395`) independently of `batch_size`. Making the
>    constant configurable would add a `Settings` field, a validator bound and a documented
>    default to change no observable behaviour.
> 2. **The rationale the finding rests on is itself stale, which is a reason to reject rather
>    than to accept.** The docstring at `ffmpeg_utils.py:454` reads *"Merge segments in
>    batches to avoid command line limits"*. There is no command-line limit to avoid on this
>    path: `_merge_batch_segments` writes a concat file list to disk
>    (`ffmpeg_utils.py:290-293`) and `_build_ffmpeg_concat_command` (`:245-269`) passes only
>    that path plus two output names — six arguments in total. `batch_size = 100` is not
>    serving the purpose its own docstring gives it. That is a different observation from the
>    one filed, it belongs to the phase that owns `_merge_segments_batched`, and it is
>    recorded here so the next run does not re-derive the configurability ask from a docstring
>    that does not describe the code.
> 3. **Project direction.** `.kilo/rules/project.md` rule 5 (*avoid overengineering; prefer
>    simple, obvious, and maintainable solutions*) and rule 7 (*do not introduce new
>    abstractions without strong justification*) both weigh against a configuration knob added
>    for a constant with no demonstrated consequence. `99-audit-validate.md` §5(d) states the
>    same rule for `BEST-PRACTICE`: reject when the ROI is negative for the project's scale.
>
> **Retained so the next run does not re-derive it.** The claim, its evidence and the
> measurements above are kept verbatim below. **Severity unchanged at LOW** — a rejected
> finding keeps the severity it carried (`99-audit-validate.md:377`).

> **Retained source text — TRN-013.** *Type `[BEST-PRACTICE]`. Subject `ffmpeg_utils.py:480`
> (`batch_size = 100`), against `ffmpeg_utils.py:452` (`download_timeout: float = 300.0`),
> `config.py` (`download_timeout`, `max_concurrent_downloads`, `max_retries`).*
>
> **What was observed.** The quantity that decides how much the muxer is asked to do in one
> call is read off the object, not assumed:
> ```
> batch_size_literal: 100
> signature: (segments_dir, output_file, count, download_timeout: float = 300.0) -> Path | None
> configured_bounds_beside_it: {"download_timeout": 300, "max_concurrent_downloads": 4, "max_retries": 3}
> ```
> The merge is issued in batches of 100 segments, and the number is not configurable while the
> timeout, concurrency and retry counts beside it are.
>
> **Failure scenario.** A user on a slow link or with a memory-constrained host cannot raise
> the merge batch smaller, and an operator debugging a merge that fails on a large set has one
> fewer knob than the two parameters next to it imply.

---
### BRW-001: HIGH — The launch failure's cause is discarded, and the failure-handling statement itself raises

> **Validation Note:**
> - **Action:** reclassified
> - **Type:** `SPEC-DEVIATION` → **`RUNTIME-ERROR`**
> - **Detail:** The outcome reproduces exactly, and the second mechanism is confirmed from the
>   raised traceback rather than inferred. One correction is entered against the evidence.
>   Driving the product's own `BrowserManager.__aenter__` on this machine, where the browser
>   binaries are genuinely absent:
>   ```
>   [BRW-001] surfaced_to_caller: UnicodeEncodeError: 'charmap' codec can't encode characters
>              in position 55-76: character maps to <undefined>
>   [BRW-001] __cause__=None __context__=Error
>   [BRW-001] context chain:
>     [0] playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at
>         C:\Users\NMatveichev\AppData\Local\ms-playwright\
>         chromium_headless_shell-1228\chrome-headless-shell-win64\chrome-headless-shell.exe
>     [1] logger.error("browser_launch_failed", exc_info=True)
>         -> codecs.charmap_encode(...) -> UnicodeEncodeError
>   ```
>   Both mechanisms are confirmed. `browser.py:45` is
>   `logger.error("browser_launch_failed", exc_info=True)`; the traceback it is asked to render
>   contains the box-drawing characters of Playwright's banner, and the console stream is
>   cp1251, so the statement raises. `browser.py:47`'s `raise ExtractionError(...)` is never
>   reached, and the caller receives neither the missing executable, nor the
>   "playwright install" remedy, nor the application's own exception type.
>   **One correction to the evidence.** The report states that `raise ... from None` "sets
>   `__cause__` and `__context__` to `None`". That is wrong, and the measurement above shows
>   it: `__cause__` is `None`, `__context__` is the live `playwright._impl._errors.Error`.
>   `from None` sets `__suppress_context__ = True`, which removes the cause from the *displayed*
>   traceback while leaving `__context__` populated. The operational conclusion the report draws
>   is unaffected — the cause is invisible to the user either way — but the mechanism as stated
>   is corrected so the fix is not aimed at the wrong behaviour. The remedy is to **carry** the
>   cause into the `ExtractionError` text, not to remove a `__context__` that is still there.
>   **Why the `Type` changes.** §5(d): this is something *seen to fail*, not a contradiction of
>   a declared rule. The traceback above is the observation. `RUNTIME-ERROR` is the format's
>   label for it.
>   **Complement with `ENT-002`, not a duplicate of it.** The encoding defect and the
>   unconfigured-logging defect are phase 01's (`ENT-001`, `ENT-002`) and are not re-argued.
>   What is this row's alone is the second mechanism: that even with logging repaired, the
>   deliberate `from None` leaves the user with a bare *"Failed to launch browser for video
>   extraction"* naming neither the binary nor how to obtain it. Two findings on one subject
>   from different sides are complement (`99-audit-validate.md` §5(b)), so both are retained and
>   cross-referenced.
> - **Severity:** HIGH, re-derived and unchanged, and the strongest case for it in this corpus
>   after `TRN-001`: the Playwright browser binaries are absent on this machine entirely, so
>   every `--cookie-source browser` user hits this, and the one piece of text that would let
>   them fix it (`playwright install`) is destroyed by the code meant to log it.
> - **See also:** `ENT-001`/`ENT-002` (phase 01, the logging and encoding defects);
>   `CON-004`/`CON-005` (phase 04, the release path, including the withdrawn "permanent leak"
>   — `browser.py:84-92` does call `playwright.stop()`, confirmed by reading `:87`).

---
> **Retained source text — BRW-001.** *Type `[SPEC-DEVIATION]` (reclassified above to
> `RUNTIME-ERROR`). Subject `browser.py:44-47` (`except Exception: logger.error(...); ...;
> raise ExtractionError(...) from None`).*
>
> **What the failing launch says.** The real launch was performed and its message captured
> verbatim:
> ```
> BrowserType.launch: Executable doesn't exist at
>   C:\Users\NMatveichev\AppData\Local\ms-playwright\chromium_headless_shell-1228\chrome-headless-shell-win64\chrome-headless-shell.exe
> ╔══════════════════════════════════════╗
> ║ Looks like Playwright was just installed or updated.  ║
> ║ Please run the following command to download new browsers: ║
> ║     playwright install   ║
> ╚══════════════════════════════════════╝
> ```
>
> **What the application surfaced, driving the product's own `__aenter__`:**
> ```
> surfaced_to_caller: "UnicodeEncodeError: 'charmap' codec can't encode characters
>                      in position 55-76: character maps to <undefined>"
> ```
> The caller receives neither the missing executable nor the remedy nor even the
> application's own `ExtractionError`. Two mechanisms combine:
> 1. `raise ... from None` (`browser.py:47`) sets `__cause__` and `__context__` to `None` —
>    the actionable Playwright message is discarded by design, and the `ExtractionError` text
>    names neither the binary nor how to get it. *(Mechanism corrected above: it sets
>    `__cause__` and `__suppress_context__`, not `__context__`.)*
> 2. The `logger.error("browser_launch_failed", exc_info=True)` on the line before it
>    (`browser.py:45`) itself raises, because the traceback it is asked to render contains
>    box-drawing characters and the console stream is cp1251. The `ExtractionError` is
>    therefore never constructed at all.
>
> **Failure scenario.** A user installs the package, runs
> `vkdownloader download <url> --cookie-source browser`, and gets a `UnicodeEncodeError`. The
> one piece of information that would have fixed the problem — "run `playwright install`" —
> exists only in the traceback that the statement meant to log and then failed to write.
>
> **Cross-reference, not re-filed.** The encoding defect itself is ENT-002 (phase 01):
> logging is not configured on this path, so the record goes to the console and the configured
> log file is never created.

---

### BRW-002: ~~MEDIUM — The context created on every acquire is bound to no release~~ [REJECTED]

> **Rejection reason (ground: stale — the measurement is right, the stated consequence is not
> reachable on the only call path in the tree).** The measurement reproduces exactly:
> ```
> [BRW-002] contexts_created=2 pages_created=2 contexts_closed=[False, False]
> [BRW-002] manager attributes=['_stealth_path', 'browser', 'playwright', 'settings']
> ```
> `create_stealth_page` does call `browser.new_context(...)` on every acquire
> (`browser.py:103-108`), the returned context is a local, nothing in the class stores it,
> closes it or returns it, and the only release in the class is `self.browser.close()`
> (`browser.py:77`). All of that is confirmed. The rejection is on the consequence:
>
> **"A batch run of 200 videos holds 200 contexts and 200 pages alive inside one browser for
> the whole run" does not follow, because there is no run-long browser.** `create_stealth_page`
> has exactly one call site in `src/` — `extractor.py:269` — and that call sits inside
> `async with BrowserManager(self.settings) as browser:` at `extractor.py:268`. Each extraction
> therefore constructs its own manager, acquires one context, and leaves the block, where
> `BrowserManager.__aexit__` (`browser.py:53-92`) runs `await asyncio.wait_for(
> self.browser.close(), timeout=_BROWSER_CLOSE_TIMEOUT)` at `:77`. Closing the browser closes
> every context it owns. The context's lifetime is one extraction, which is exactly what the
> missing release path was costing, so the accumulation the finding describes cannot occur.
>
> **The one path where it could occur is already owned elsewhere, and the report says so.**
> `browser.py:75` guards the close with `and not shutdown_event.is_set()`, so when a stop is
> set the browser is not closed — that is `CON-004` (phase 04, HIGH, confirmed), and the
> report's own *Scope note* already hands it there rather than re-arguing it. Even on that
> path, the `finally` at `browser.py:84-92` runs `await asyncio.wait_for(self.playwright.stop(),
> …)` at `:87`, which tears the driver down and the browser with it. So neither the default
> path nor the stop path leaves 200 contexts alive.
>
> **What survives, and is not a finding.** A method that creates a resource it cannot release
> is an API asymmetry — a trap for the next caller who keeps a manager alive — and this run
> records it as exactly that. It is not a defect at this project's scale: there is one call
> site, and its contract is satisfied by the enclosing context manager. Recording it as a
> finding would encode a consequence the tree cannot produce.
>
> **Retained so the next run does not re-derive it.** The claim, its evidence and the
> measurement above are kept verbatim below. **Severity unchanged at MEDIUM** — a rejected
> finding keeps the severity it carried (`99-audit-validate.md:377`).

---
> **Retained source text — BRW-002.** *Type `[BEST-PRACTICE]`. Subject `browser.py:94-116`
> (`create_stealth_page`); the release path `browser.py:53-92`.*
>
> **What was observed.** The acquire path driven with stand-in objects (the real browser
> binaries are not installed on this machine — see §Skips):
> ```
> contexts_created: 2                     (for 2 calls to create_stealth_page)
> pages_created: 2
> contexts_closed: [false, false]
> manager_stores_context: false
> manager_attribute_names: ["_launch_args", "_stealth_path", "browser", "playwright", "settings"]
> pages_are_distinct: true
> ```
> `browser.new_context(...)` is called on every acquire (`browser.py:103-108`), the returned
> context is a local (`browser.py:103`), and no step in the class binds it to anything: it is
> not stored on the manager, not returned, and not closed. The only release in the class is
> `self.browser.close()` (`browser.py:77`), which closes the browser and with it every context
> it owns. `create_stealth_page` is called once per extraction, so one context and one page
> accumulate per video for the life of the manager.
>
> **Identity parameters passed to the context**, recorded rather than judged:
> `viewport={"width": 1920, "height": 1080}`, `user_agent=<settings.user_agent>`,
> `locale=<settings.locale>`, `timezone_id=<settings.timezone>`. All four derive from
> `Settings`; none is fixed in code. The launch argument is a single token,
> `--disable-blink-features=AutomationControlled` (`browser.py:42`), whose only purpose is to
> suppress an automation signal — whether the browser honours it is a property of the browser
> and is out of scope by design.
>
> **Failure scenario.** A batch run of 200 videos holds 200 contexts and 200 pages alive inside
> one browser for the whole run, none of them visible to the manager. Per-video teardown is not
> possible, because nothing in the acquire path hands back what it created.
>
> **Scope note.** The acquire side only. Whether release is reached at all on any path is
> CON-004 (phase 04) and is not re-argued here.

---

### BRW-003: MEDIUM — The injected asset's absence is silent at every log level

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced, and the anchor the report cites for the packaging is corrected.
>   ```
>   [BRW-003] real asset exists=True size=2608
>   [BRW-003] asset_path=no-such-directory\stealth.min.js exists=False
>   [BRW-003] scripts_applied=[]
>   [BRW-003] page_returned=True
>   ```
>   `browser.py:112-114` is
>   `if self._stealth_path.exists(): await page.add_init_script(path=…); logger.debug(
>   "stealth_script_applied")`. There is **no `else` branch**: the absence produces no record at
>   any level, and the method returns a usable page either way. The single record the call
>   writes is the ordinary `creating_stealth_page` entry at `:101`, which says a stealth page
>   was created — not that the script was not applied.
>   **Anchor correction.** The `Subject` cites `pyproject.toml:39-40` for the asset being a
>   wheel artifact. Those lines are the explanatory comment; the declaration is
>   `pyproject.toml:44`, `artifacts = ["src/vkdownloader/stealth.min.js"]`. The asset's
>   existence is confirmed independently (`src/vkdownloader/stealth.min.js`, 2 608 bytes), so
>   the claim stands on the corrected anchor.
>   **Architectural fit.** The fix the finding implies — an explicit `else: logger.warning(...)`
>   naming the path — matches a pattern the project already uses: `check_ffmpeg_available`
>   warns on a missing dependency (`ffmpeg_utils.py:82-88`) and `_check_merge_space` logs a
>   probe failure and proceeds (`ffmpeg_utils.py:422-423`). This finding introduces no new
>   pattern.
> - **Severity:** MEDIUM, re-derived and unchanged. Extraction proceeds with the browser's
>   ordinary fingerprint, the extraction is more likely to be detected, and the only clue is a
>   downstream extraction failure that nothing connects to this branch.
> - **See also:** `BRW-001` (the same handler family, a different silent failure).

> **Retained source text — BRW-003.** *Type `[BEST-PRACTICE]`. Subject `browser.py:112-114`
> (`if self._stealth_path.exists(): await page.add_init_script(...); logger.debug(
> "stealth_script_applied")`).*
>
> **What was observed.** The asset exists in the repository
> (`src/vkdownloader/stealth.min.js`, 2 608 bytes) and is declared as a wheel artifact
> (`pyproject.toml:39-40`). The manager was then pointed at a location that holds none — the
> state the branch is written for — and the acquire path driven with stand-in objects, with
> logging at DEBUG into a file:
> ```
> asset_path_used: "no-such-directory\\stealth.min.js"
> page_returned: true
> log_records_written_during_the_call:
>   {"event": "creating_stealth_page", "level": "debug", "timestamp": "…"}
> injection_happened: false
> ```
> One record — the normal entry — and nothing about the missing asset at any level. The call
> still returns a usable page. With the asset present, the same drive produces
> `add_init_script("…\\stealth.min.js")` and the `stealth_script_applied` record.
>
> **Failure scenario.** The asset is absent in the environment the application runs in — a
> wheel built without the data file, a partial deployment, a renamed file. Extraction proceeds
> with the browser's ordinary fingerprint, is more likely to be detected, and the only clue is
> an extraction failure some way downstream with nothing connecting it to this branch. The log
> says a stealth page was created; it does not say the script was not applied.

---
## Retained from the source report — documented skips

> Retained verbatim as part of the self-contained record (R1). **No decision is recorded
> against these rows**: they are skips, not findings, and each one names the phase that owns
> the defect it defers to. This run spot-checked the two whose claims a retained finding
> depends on and records the result; the rest are carried for the next reader, unverified.

| Row | Reason | This run |
|---|---|---|
| Signal-handler registration path (`asyncio/unix_events.py` `add_signal_handler`) | On Windows `loop.add_signal_handler` raises `NotImplementedError`; the `signal.signal` fallback at `signal_handlers.py:40-54` is what runs. Unreachable, not a defect. The real defect there — nothing restores the handler — is CON-001 (phase 04). | **Confirmed by reading.** `signal_handlers.py:43` is the `loop.add_signal_handler` call, `:45` catches `NotImplementedError`, `:48` and `:53` are the `signal.signal` fallbacks. The deferral to CON-001 is correct. |
| The grace branch of the termination ladder (`except TimeoutError: process.kill()` at `ffmpeg_utils.py:202-205`) | The standard library maps the graceful request and the forceful one to the same unconditional termination call on this platform, so no child can be made to ignore the first request and the branch cannot be entered. `timeout=5.0` (`ffmpeg_utils.py:182`) is the only grace any child receives. | Not re-driven. Accepted: the claim is a property of `asyncio.subprocess.Process.terminate()` on Windows and nothing in the tree changes it. |
| A real browser launch, a real context, a real init script | The Playwright browser binaries are not installed on this machine (`chromium_headless_shell-1228` missing, confirmed by the verbatim launch error in BRW-001). | **Confirmed.** `BRW-001` drove a real launch on this machine and the missing-executable error is reproduced verbatim in that finding above. |
| The Playwright driver's working directory and environment size | The installed Playwright version does not expose the driver's process object through the public or the private attributes the harness tried. The command line was read from the operating system instead, and is quoted in TRN-003. | Not re-driven. Accepted. |
| R2's stub-based observation of the response file at the moment the child opens it | A stub cannot shadow the real muxer on this platform: `CreateProcess` resolves a bare name on `PATH` with the `.exe` extension only, so a `ffmpeg.CMD` stub is found by the discovery probe and ignored by the invocation. | **Confirmed and superseded.** `TRN-001` established that the real muxer never reads the file at all, so the stub-shadowing problem no longer has any observation to make. |

## Retained from the source report — R9 baselines and checked-and-clean

> Retained as part of the record. **The baseline block is superseded** by the re-run in this
> artifact's *Baselines re-verified this run* section above; the two statements that did not
> reproduce are named there (the suite count, and `ruff format --check`'s exit status, which
> is clean on this tree). The checked-and-clean rows are retained; three that a retained
> finding's contrast depends on were re-checked here.

- **Escalation ladder's first call** returns `True` for a live child and for one that exits
  inside the grace, and the `ProcessLookupError` arm is the only source of `False`
  (`TRN-012` records what that arm is mistaken for). — **Re-checked:** `TRN-012`'s three-call
  sequence `[True, False, False]` confirms both halves.
- **The downloader's progress parser** is regex-guarded: a non-numeric percentage, the `N/A`
  placeholder, and a non-`[download]` line all return `None` and produce no progress and no
  exception. The muxer's is not (`TRN-006`). — **Re-checked by reading**
  `ytdlp_downloader.py:145-155` and `:186-188`; `TRN-006`'s Validation Note carries the
  correction that the muxer's handlers *do* guard the protocol's own `N/A`.
- **Every flag the child vector passes exists in the installed tool.** `--version` reports
  `2026.07.04`; each of the fifteen flags was passed alone and then with a value. The three
  absent from the short `--help` text (`--hls-prefer-native`, `--referer`, `--user-agent`)
  are accepted by the installed parser. — **Spot-checked:** `python -m yt_dlp --version` →
  `2026.07.04`, and `--hls-prefer-native` is accepted (absent from `--help`, no
  "No such option"). The other two are in the short help.
- **Format selectors**, read off the builder for every `QualityEnum` value:
  `240→best[height<=240]` … `best→best`, `worst→best`. The `worst` entry is NET-003 (phase 03)
  and is not re-filed here. — **Confirmed by reading** `ytdlp_downloader.py:256-257`:
  `f"best[height<={quality_str}]" if quality_str and quality_str.isdigit() else "best"`, so
  a non-numeric quality including `worst` yields `best`.
- **Declared version floors** — `yt-dlp>=2024.0.0` (`pyproject.toml:27`),
  `playwright>=1.45.0` (`pyproject.toml:20`). Confirmed at `pyproject.toml:20` and `:27`.
- **Termination escalation order** — `cancel_subprocess` addresses the direct child and nothing
  else; the grace values in use are 5 s (`ffmpeg_utils.py:182`), 300 s (`download_timeout`) for
  the merge (`ffmpeg_utils.py:238`), and 10 s (`_BROWSER_CLOSE_TIMEOUT`, `browser.py:16`).
  Confirmed at each anchor.
- **The cookie file's removal on every path** — `ytdlp_downloader.py:725-728` and
  `downloader.py:410-413` — is phase 06's row. Confirmed at both anchors; not re-filed.
- **The child-wait path and the displaced SIGINT handler** are CON-001 (phase 04) and are not
  re-filed. Not re-derived.

### Harness notes (retained)

All scratch code for this validation run lived under `.temp/val05/` (gitignored) and has been
removed. **Nothing in the repository was modified** — `git status --short -- src tests
pyproject.toml` is empty at `ea44b3d`. The injected asset was not moved or renamed; the
manager was pointed at a location holding none, which is the state `BRW-003`'s silent branch
is written for. Third-party origins were never contacted: the muxer was pointed at
`http://127.0.0.1:9` (connection refused) or at `lavfi`; the browser launch was attempted
against genuinely absent binaries; and every stand-in child was a local `python -c` process.
Every child this run started outside `ffmpeg.exe` was terminated by the end of its harness.

---
## Findings this phase filed against the audit inputs

> `VAL-` is reserved for defects in the audit inputs themselves
> (`99-audit-validate.md` §10): a cross-phase conflict, a merge, an unsafe ordering, a
> pipeline-document defect. **Neither finding below is a product-code finding**, and the
> defects they name belong to the phases that filed them. Identifier block `VAL-5xx` is used
> because `001–007`, `101–112`, `401–410` and `601–603` are taken by earlier validation runs
> in this store; `VAL-001` in particular already carries three unrelated meanings.

### VAL-501 — CRITICAL — Phase 06 and phase 05 assert incompatible facts about the ffmpeg transport's concealment

| Field | Value |
|-------|-------|
| **ID** | VAL-501 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.ai/audit/06-credentials-secrets/findings.md` (its validated form), `.ai/audit/05-subprocess-browser/findings.md` |
| **Classification** | mandatory |

**Description.** Two phases state, about one subject — whether the ffmpeg transport's
response file satisfies the concealment the product declares for it — answers that cannot both
hold.

**Evidence.**

*Claim A — phase 06, `SEC-004`, heading (`.ai/audit/06-credentials-secrets/findings.md:328`,
retained in `99-validation/06-credentials-secrets-validated-findings.md:581`):*

> "The credential file's path is disclosed in the yt-dlp command line **while the sibling
> ffmpeg transport satisfies the product's own stated intent** for the same value"

and its R5(d) table (`:379-384`, retained at `…-validated-findings.md:641-644`):

> | Declared intent (verbatim) | ffmpeg transport |
> | `downloader.py:97-99` — "sensitive values … never appear in the process command-line arguments — they are only visible inside the temp file" | **MET** (argfile) |
> | `downloader.py:258-261` — "since the URL is now inside the argfile (SEC-001), the cookie file path is also protected from the process listing." | **MET** (argfile) |

The finding's calibration, retained at `…-validated-findings.md:584`, rests on that column:
*"The sibling transport is as described … one of two transports carrying the same value meets
the stated invariant; the other does not, with no stated exception."*

*Claim B — phase 05, `TRN-001`:* the response file is never opened, so nothing the invariant
protects is ever passed to the tool. Re-derived in this run: 3/3 invocations of
`HLSDownloader.download_with_ffmpeg` and 4/4 raw `ffmpeg "@<path>"` invocations, with control
**C** (a response file naming a valid `lavfi` input and a writable output) producing no output
file and control **D** (the same arguments passed directly) producing one.

**Which claim the evidence supports.** **Claim B.** "Satisfies the stated intent" requires the
sensitive value to reach the muxer while hidden from the process listing. On the installed muxer
it reaches nothing. `MET (argfile)` is true only in the vacuous sense that the value is absent
from the argv — which is also why it is absent: nothing is transmitted. The two claims are
about the same subject and cannot both be recorded.

**Recommendation.** Phase 06 re-derives the ffmpeg column of `SEC-004`'s R5(d) table against
`TRN-001`'s evidence before `SEC-004` is used to justify any fix. Specifically: the asymmetry
framing — *"one transport satisfies the stated intent, therefore the other should too"* —
does not hold on the current tree, because the ffmpeg transport satisfies it vacuously. What
survives of `SEC-004` is not an asymmetry but a **uniform** statement about the *declared*
intent, and it becomes a real asymmetry again only if and when `TRN-001` is repaired in a way
that keeps a working indirection. The claim this run makes is **about the two reports**, not
about the product: `SEC-004`'s evidence for the ffmpeg column must be re-taken. This phase
does not re-file `SEC-004` and does not own its subject.

**Severity CRITICAL**, per `99-audit-validate.md:367`: two phases assert incompatible facts
about the same subject. Consequence: a fix driven by `SEC-004`'s asymmetry framing would move
the yt-dlp transport's cookie path into an indirection for a benefit that, on this tree, the
other transport does not actually obtain — while the transport that genuinely cannot obtain it
goes unfixed.

**See also.** `TRN-001`, `TRN-010`, `SEC-001`, `SEC-004`; `VAL-502`.

---

### VAL-502 — CRITICAL — Two dependency chains between accepted findings, neither named by any finding

| Field | Value |
|-------|-------|
| **ID** | VAL-502 |
| **Severity** | CRITICAL |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.ai/audit/05-subprocess-browser/findings.md`, `.ai/audit/06-credentials-secrets/findings.md` |
| **Classification** | mandatory |

**Description.** R4 (`99-audit-validate.md:165-170`) found two dependency chains among this
corpus's accepted findings that no finding states. Both are consequences of `TRN-001` and
neither can be ordered around.

**Chain 1 — fixing `TRN-001` activates a latent half of `TRN-002`.**

`TRN-002`'s ordering half — the response file is destroyed at `downloader.py:124` on the
statement after the spawn at `:305-309`, while the `try`/`finally` that guarantees
`cancel_subprocess` (`:400-409`) is not entered until `:311` — is **inert today**, precisely
because the muxer never opens the file. That is the report's own admission, and this run
confirms it. The moment `TRN-001` is repaired so that the child *does* read the file, the
ordering becomes a live race, and any consumer that opens the file lazily rather than at
`open()` makes the destroy win and the download fail with "no such file". The two fixes must
therefore land **together**: the destroy has to move inside the `try` in the same change that
makes the response file work. Applying `TRN-001` first does not merely leave a known defect
open — it converts a benign ordering into a data-loss ordering on a path that currently has no
data.

**Chain 2 — the shape of the `TRN-001` fix is a decision `SEC-004` already owns.**

The installed muxer has neither `@file` nor `-/opt`, so there is no repair that both restores
the transport and keeps the arguments off the command line. Every available repair either
(A) puts the signed m3u8 URL and the cookie-file path into the ffmpeg argv, which is the
exposure `SEC-004` exists to prevent, or (B) retires the transport, which contradicts six
documentation sites (`README.md:57`; `docs/99-reference/cli-reference.md:66,96`;
`docs/01-tools/quality-selection.md:96-99`; `docs/01-tools/vkdownloader-overview.md:138`;
`docs/11-guides/vkdownloader-limitations.md:131`). Under (A) — the only repair available on this
muxer — `SEC-004`'s ffmpeg column flips from vacuously `MET` to genuinely `NOT MET`, and
`TRN-010`'s asymmetry collapses into uniform exposure. **No finding in either corpus records
that the transport-shape decision is a prerequisite of `TRN-001`, `TRN-010` and `SEC-004`
simultaneously.**

**The third dependency, recorded and not filed as a chain.** `TRN-004`, `TRN-005`, `TRN-006`
and `TRN-007` share one mechanism — a reader that stops leaves `process.wait()` structurally
unable to return — and `TRN-007` is what carries it. They are **four separately reachable
routes into one wedge, each separately fixable**, so they are a dependency set and not one
defect stated four times. They are therefore **not** merged, and no merge candidate is filed.
This is recorded so a later run does not mistake the adjacency for a duplicate.

**Evidence.** All four products of this run: `TRN-002`'s `LIFETIME: {'exists_at_spawn': True,
…}` plus its reproduced `PermissionError` escape with a live child; `TRN-004`'s
`process.wait() DID-NOT-RETURN-WITHIN-8s AFTER KILL`; `TRN-005`'s `helper returned after
0.031s; child_returncode=None` followed by `unbounded re-wait DID-NOT-RETURN-WITHIN-6s`;
`TRN-007`'s `re-wait DID-NOT-RETURN-WITHIN-6s`. Ordering is read from `downloader.py:302-311`
and `ffmpeg_utils.py:217-242`.

**Recommendation.** Record both chains against the findings that own them before any of
`TRN-001`, `TRN-002`, `TRN-010` or `SEC-004` is scheduled, and treat the transport-shape
decision — not the `@file` removal — as the unit of work. The decision belongs to the phase
that owns the transport's documented contract; this phase records the constraint and does not
make it.

**Severity CRITICAL**, per `99-audit-validate.md:367`: a fix that cannot be ordered safely
because a prerequisite of it is itself a finding. Both chains are of that shape.

**See also.** `TRN-001`, `TRN-002`, `TRN-004`, `TRN-005`, `TRN-006`, `TRN-007`, `TRN-010`;
`SEC-001`, `SEC-004`; `VAL-501`.

---
## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 11 | TRN-003, TRN-004, TRN-005, TRN-006, TRN-007, TRN-008, TRN-009, TRN-010, TRN-011, TRN-012, BRW-003 |
| Reclassified | 3 | TRN-001, TRN-002, BRW-001 |
| Merged | 0 | — |
| Rejected | 2 | TRN-013, BRW-002 |
| VAL- (cross-phase / rollout) | 2 | VAL-501, VAL-502 |

### Reconciliation

Source corpus: **16** findings (`TRN-001` … `TRN-013` = 13, `BRW-001` … `BRW-003` = 3).
Decisions recorded in this artifact: **16** — 14 `Validation Note` blocks (11 validated,
3 reclassified) and 2 `Rejection reason` blocks in the form §11's decision table prescribes for
a rejection. `11 validated + 3 reclassified + 0 merged + 2 rejected = 16`. The two `VAL-` rows
are findings this phase originated and are counted separately from the 16, exactly as
`99-audit-validate.md` §10 requires.

### Severity composition (independent of the decision)

| Finding | Carried | Re-derived | Change |
|---------|---------|-----------|--------|
| TRN-001 | HIGH | **CRITICAL** | escalated — shipped `--method ffmpeg` is a silent no-op, and its fix has a prerequisite that is itself a finding |
| TRN-002 | HIGH | HIGH | — |
| TRN-003 | HIGH | HIGH | — |
| TRN-004 | HIGH | HIGH | evidence strengthened (the wait does not return even after `kill`) |
| TRN-005 | HIGH | HIGH | — |
| TRN-006 | HIGH | HIGH | — |
| TRN-007 | MEDIUM | MEDIUM | — |
| TRN-008 | MEDIUM | MEDIUM | — |
| TRN-009 | MEDIUM | MEDIUM | — |
| TRN-010 | MEDIUM | MEDIUM | scope narrowed by TRN-001 |
| TRN-011 | MEDIUM | MEDIUM | — |
| TRN-012 | MEDIUM | MEDIUM | — |
| TRN-013 | LOW | LOW | rejected; severity kept (`99-audit-validate.md:377`) |
| BRW-001 | HIGH | HIGH | — |
| BRW-002 | MEDIUM | MEDIUM | rejected; severity kept |
| BRW-003 | MEDIUM | MEDIUM | — |
| VAL-501 | — | **CRITICAL** | new (cross-phase conflict) |
| VAL-502 | — | **CRITICAL** | new (rollout-ordering blocker) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| TRN-013 | One batch bound is a literal where configured values sit beside it | **Low value at this scale / stylistic preference.** The measurement is exact; there is no defect behind it — `download_timeout` already bounds each batch and `_check_merge_space` already accounts for the merge's space independently of `batch_size`. The finding's own rationale is stale: `ffmpeg_utils.py:454` justifies the batch by "command line limits", but the path writes a concat file list and passes six arguments. Full reason retained in the finding's rejection block. |
| BRW-002 | The context created on every acquire is bound to no release | **Stale.** The measurement reproduces exactly (`contexts_created=2`, `contexts_closed=[False, False]`, manager does not store it), but the stated consequence is unreachable: the only call site is `extractor.py:269` inside `async with BrowserManager(...)` at `:268`, and `__aexit__` closes the browser at `browser.py:77`, which closes every context it owns. The one path where it could accumulate is `CON-004`'s, and the report's own scope note already hands it there. Full reason retained in the finding's rejection block. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| — | — | **No merges.** `TRN-004`/`TRN-005`/`TRN-006`/`TRN-007` share one mechanism and were examined as merge candidates; they are four separately reachable routes into one wedge, each separately fixable, so they are a dependency set rather than one defect stated four times. Recorded in `VAL-502` so the adjacency is not later mistaken for a duplicate. A zero count writes a zero and no row is manufactured to fill the shape. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| TRN-001 | SPEC-DEVIATION | RUNTIME-ERROR | Observed failing seven times in this run (3/3 through the product path, 4/4 raw, with a direct-argv control that succeeds). §5(d) requires the runtime-failure label be checked first and forbids reclassifying away from it. |
| TRN-002 | BEST-PRACTICE | SPEC-DEVIATION | The code's own comment at `downloader.py:401-402` claims *"Guarantee ffmpeg is terminated … preventing orphaned processes"*; the reproduced `PermissionError` escape shows the guarantee does not hold. A stated rule the implementation violates. The report carried both labels in parentheses; the format's single `Type` field admits one. |
| BRW-001 | SPEC-DEVIATION | RUNTIME-ERROR | Observed failing: `UnicodeEncodeError` is what the caller receives, and the raised traceback shows `logger.error(..., exc_info=True)` at `browser.py:45` is what raises. |

### Cross-references recorded, not re-filed

| Cross-reference | Owner | Note |
|---|---|---|
| `ENT-001`, `ENT-002` (phase 01) | phase 01 | BRW-001 is **complement**, not duplicate: `ENT-002` owns the encoding defect, BRW-001 owns the `from None` cause-loss that survives its repair. |
| `CON-001` (phase 04) | phase 04 | Displaced SIGINT handler; cited by the source's skip table and by the checked-and-clean list. |
| `CON-004`, `CON-005` (phase 04) | phase 04 | Browser release. **`CON-004`'s withdrawn "permanent leak" is independently confirmed withdrawn**: `browser.py:84-92` is a `finally:` that runs `await asyncio.wait_for(self.playwright.stop(), …)` at `:87`. This is the same `finally` that makes `BRW-002`'s rejection sound, and it is recorded here rather than in `BRW-002` so the reasoning is available to the next reader. |
| `NET-003` (phase 03) | phase 03 | `--quality worst` → `best`; confirmed by reading `ytdlp_downloader.py:256-257`, not re-argued. |
| `NET-007` (phase 03) | phase 03 | Recommendation withdrawn; the documented no-whole-operation-budget decision at `ytdlp_downloader.py:580-582` is what makes `TRN-007`'s narrower scope correct. |
| `SEC-001` … `SEC-004` (phase 06) | phase 06 | `SEC-001`'s 0o666-measurement and `SEC-004`'s argv-element-28 claim are not re-derived. **`SEC-004`'s ffmpeg column conflicts with `TRN-001` and is filed as `VAL-501`; this run does not re-file `SEC-004` itself.** |
| `CFG-001` (phase 02) | — | **Fixed** by `ea44b3d`; not re-validated as open, per the run's instruction. No finding in this corpus depends on it. |
| `docs/STRUCT.md` omits `ytdlp_downloader.py` | phase 09 | Confirmed (`docs/STRUCT.md:18-36` lists `browser.py`, `batch_downloader.py`, `downloader.py`, `ffmpeg_utils.py`, `segment_downloader.py` and not `ytdlp_downloader.py`). A structural-description defect under R-E, owned by phase 09. **Recorded as a cross-reference and not filed** — it is not a `VAL-` class (conflict / merge / ordering / pipeline document) and it is not this phase's subject. |

### Corrections entered against the source report's evidence

Six. None changes a decision; all are recorded so the next run does not inherit the original.

| # | Where | Correction |
|---|---|---|
| 1 | `TRN-001`, `BRW-003` — `Subject` | `pyproject.toml:39-40` is the explanatory comment; the wheel-artefact declaration is `pyproject.toml:44`. |
| 2 | `TRN-009` — `Subject` | `url_sanitizer.py:13-24` is `_strip_auth_params`; the transform is `_URL_REGEX` at `:8` and `sanitize_text_for_log` at `:33-47`. The report's own body cites `:8` correctly. |
| 3 | `BRW-001` — evidence | `raise … from None` sets `__cause__` and `__suppress_context__`, **not** `__context__`. Measured: `__cause__=None`, `__context__=playwright._impl._errors.Error`. |
| 4 | `TRN-003` — failure scenario | The named merge child is contingent: the vector passes `--hls-prefer-native` (`ytdlp_downloader.py:272`), which steers yt-dlp away from a muxer for HLS. |
| 5 | `TRN-006` — failure scenario | The handlers **do** guard the protocol's `N/A` on every key; the residual trigger is a value that is neither numeric nor `N/A`. |
| 6 | `TRN-010` — cross-reference note | The `SEC-001` asymmetry judgement is **conditional**, true only if `TRN-001` is repaired by moving the arguments onto the command line. |
| — | R9 baselines | `495 passed, 4 skipped` does not reproduce — this tree gives `498 passed, 4 skipped`. `ruff format --check src` is **exit 0** (`30 files already formatted`), so the phase-06 validator's exit 1 no longer reproduces either. |
| — | R9 anchor ledger | The claim `106 anchors, 106 exact, 0 drifted` was not reproduced as a count. Every anchor behind a decision was opened; two are drifted (rows 1 and 2 above) and no other drift was found. |

---

**End of the validation artifact for phase 05.** Sixteen source findings, sixteen decisions,
two `VAL-` findings against the audit inputs. No source file was modified; the source report
`.ai/audit/05-subprocess-browser/findings.md` is unmodified and this file is the only artifact
this run wrote.
