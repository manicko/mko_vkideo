# Phase 03 Audit Findings — Network Resilience (Validated)

**Executor:** audit-executor · **Validator:** validator
**Template:** `.kilo/commands/audit/phases/03-audit-network-resilience.md`
**Report format:** `.ai/audit/templates/audit-findings.md`
**Source report (read-only):** `.ai/audit/03-network-resilience/findings.md`
**Status:** complete · **Validated:** yes

> **Deviation from the report format, stated once here.** The template defines nine
> mandatory fields per finding and none of them carries a validation decision — its
> finding block runs from the heading straight into the field table. The `Validation
> Note` this phase is required to attach to **every** decided finding therefore has no
> slot in the format. It is written directly below each `### {ID}:` heading, above the
> field table, and the absence of the slot is filed as `VAL-006`. This is the only
> deviation from the format in this artifact.

**What this artifact is.** A judgment record about the 18 findings in the phase 03
report. Every finding was re-derived from the source it names, not from the report's
wording; the report's own evidence was not treated as trustworthy. This artifact is
self-contained: the re-derived fact is quoted in each Validation Note, so a reader
never has to open the source report to know what was checked and what was found.

---

## Checkpoint 0 — R0 Discovery

*Emits no checkpoint of its own; recorded here because a tally of zero is admissible
only once these three maps are recorded.*

**R0.1 — Corpus map.** Phases in the `01`–`11` range that hold a findings file, and
whether a handbook exists for each:

| Phase | Handbook | Findings file | Findings |
|---|---|---|---|
| 01 entry-architecture | present | present | validated (`99-validation/01-…`) |
| 02 config | present | present | validated (`99-validation/02-…`) |
| **03 network-resilience** | present | present | **18 (this artifact)** |
| 04 concurrency-cancellation | present | present | not yet validated |
| 05–11 | present | **absent** | — |

No gap in either direction for `01`–`04`. For `05`–`11` a handbook exists with no
findings file; that is the expected state of a partially-executed run, not a gap in
this run's scope. `.ai/audit/99-validation/` holds two validated artifacts; the third
is this one.

**R0.2 — Identifier map.** Live prefixes in the current catalogue: `ENT`, `CFG`, `NE`,
`CON`, and the `VAL-` prefix this phase owns. All are two characters, all are distinct,
and no two live prefixes share a first two characters. `NE` (phase 03) collides with no
live prefix. The worktree `.kilo/worktrees/southern-bandana/.ai/audit/` holds a **stale
nine-phase catalogue** under different numbers (`01-audit-cli`, `02-audit-config`,
`03-audit-services`, `04-audit-security`, `05-audit-integrations`, `06-audit-data-flow`,
`07-audit-tests`, `08-audit-quality`, `09-structural-quality`). Its prefixes are **not
adopted** by this phase and none of its numbers was counted anywhere below. Note the
numbering collision risk: the stale catalogue's `03` is *services*, the live one is
*network-resilience*; a match counted from the worktree is wrong in the direction that
makes this phase look better covered.

**R0.3 — Decision-record map.** For each of the four decisions (validated /
reclassified / merged / rejected) the report format's finding block offers **no slot**.
The `Validation Note` block is therefore carried in a position the format does not
define, in every finding in this artifact — an **absent slot**, not a missing decision.
Filed as `VAL-006`.

**R0.4 — Pipeline-document map.** Documents the audit pipeline reads or writes, and the
denominator for the pipeline checks:

| Document | Declares it does | Opened by this run |
|---|---|---|
| `.kilo/commands/audit/audit-multi-phase.md` | selects phases, launches executors and validators, gates each stage, prints the closing summary | yes |
| `.kilo/commands/audit/phases/NN-*.md` (13 files) | per-phase method, checks, severities | `03`, `99`, plus `01`/`02`/`04`/`06`/`09` where a cross-phase claim was tested |
| `.kilo/commands/audit/audit-orphaned.md` | reachability census for orphaned files | yes |
| `.kilo/commands/audit/tests/audit-tests-full.md` | test-audit command; owns the "next available number" instruction | yes |
| `.kilo/commands/audit/templates/audit-findings.md` | the report format and its four vocabularies | yes |
| `.kilo/agents/auditor.md`, `.kilo/agents/validator.md` | the two roles the pipeline launches | yes |
| `.ai/audit/{NN}-{slug}/findings.md` | per-phase findings | read-only; `03` opened, `01`/`02`/`04` opened for conflict tests |
| `.ai/audit/99-validation/*-validated-findings.md` | per-phase validated findings | `01`, `02` read for format; this one written |

Not opened and therefore not checked: `.kilo/commands/audit/audit-refine.md`,
`audit-phase-refine.md`, `audit-phase-gaps.md`, and the three other test-audit
commands. No check in this artifact depends on them, so no row for them is claimed.

---

## Checkpoint 1 — R1 Copy Source Findings

- **Stage:** R1 Copy Source Findings
- **Findings in scope:** 18
- **Evidence anchor:** `.ai/audit/03-network-resilience/findings.md`, 1407 lines, read
  in full. Copied to this artifact; **the source was not modified** (`git status` on
  the source path is clean at the end of this run).
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

---

## Checkpoint 2 — R2 Cross-Finding Analysis

- **Stage:** R2 Cross-Finding Analysis
- **Findings in scope:** 18 (Validated 15, Reclassified 1, Merged 0, Rejected 0 as of
  Checkpoint 3; the 2 further `VAL-` findings minted here are counted separately)
- **Cross-phase conflict count:** 1 — filed as `VAL-001`
- **Merge-candidate count:** 0 full merges; 1 partial overlap recorded in place
  (`NET-002` / `NET-010`, both retained, cross-referenced)
- **Evidence anchor:** phase 04's `CON-009` and `CON-003` read verbatim; connector and
  session construction sites counted; the live prefixes of phases 01–04 compared.
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

**R2 findings, stated in full.**

- **One conflict, on one number.** `NET-014` asserts that at the default
  configuration "the connector is the binding constraint the setting was meant to be",
  i.e. a process-wide ceiling of 10. `CON-009` asserts 4 units × 10 = **40** total
  connections at the same default. Both cannot hold. `CON-009` is the one the evidence
  supports: `_create_connector` has exactly one call site
  (`segment_downloader.py:795`), inside `_run_download_session`, which runs once per
  video, and each call is paired with its own `ClientSession` (`:797`). There is no
  process-wide pool. Filed as `VAL-001`.
- **No merge.** No two phase-03 findings share a root cause once named. The closest
  candidates were tested and are complements, not duplicates:
  `NET-004` (which *base address* the refreshed parts resolve against) and `NET-005`
  (which *stream of the refreshed set* is chosen) are two halves of one refresh path and
  neither absorbs the other. `NET-002` (the manifest layer has no retry policy) and
  `NET-010` (a transport-level failure is retried with zero delay) overlap on exactly
  one bullet — the manifest layer's `continue` at `segment_downloader.py:504-505` — but
  `NET-010`'s other two bullets are the media-part strategies, which `NET-002` does not
  touch. Both are retained; `NET-002` absorbs the overlapping bullet by scope, and both
  Validation Notes say so.
- **`NET-002` is distinct from the `max_retries` plumbing owned by phase 02.** Phase 02's
  `CFG-002` is about `model_copy(update=...)` at `downloader.py:652-653` admitting
  values outside the declared `ge=1 le=10` range and reaching the consumer. `NET-002` is
  about `_fetch_playlist_with_retry` not consulting `max_retries` as a policy at all. The
  two have different subjects, different files, and different root causes; a fix to
  either does not touch the other. No merge, and no cross-phase conflict: phase 02 makes
  no claim about how the manifest layer uses the value.
- **Two seams were respected, not overridden.** `NET-014` disclaims the
  `TCPConnector(limit=10)` literal as phase 04's; `CON-009` disclaims the request *rate*
  as phase 03's. Neither double-files. `NET-005` and `NET-008` each name the other
  phase's rendering half rather than filing it. These are correct carve-outs, and the
  one place the seam produced a factual disagreement is `VAL-001`.

---

## Checkpoint 3 — R3 Validate Each Finding

- **Stage:** R3 Validate Each Finding
- **Findings in scope:** 18
- **Decision tally:** Validated 15 · Reclassified 1 · Merged 0 · Rejected 0
- **Severity re-derived:** 4 corrected (NET-006 HIGH→MEDIUM, NET-007 HIGH→MEDIUM,
  NET-011 MEDIUM→LOW, NET-013 MEDIUM→LOW) · 14 confirmed unchanged
- **Evidence anchor:** every claim re-derived from the named source file, and the
  re-derived fact quoted in the finding's own Validation Note. Baselines re-run (§
  Baselines below) and the source report's own R10 coverage declaration re-tested.
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

---

## Checkpoint 4 — R4 Assess Rollout Safety

- **Stage:** R4 Assess Rollout Safety
- **Findings in scope:** the 18 decided findings, read as an ordered fix plan
- **Unsafe-ordering count:** 1 — filed as `VAL-002`
- **Findings added by this phase:** 7 (`VAL-001` … `VAL-007`)
- **Circular dependencies:** 0
- **Hidden dependency chains:** 1, recorded below, not filed as a finding
- **Fragile insertion points:** 0 among the accepted findings' own recommendations
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

**R4 findings, stated in full.**

- **Unsafe ordering, one site.** Four accepted findings prescribe edits inside the same
  40-line function, `_fetch_playlist_with_retry` (`segment_downloader.py:484-523`):
  `NET-004` changes its **return type** (`str | None` → a tuple carrying the address the
  manifest actually came from); `NET-002` rewrites the loop body's status branch and
  adds a parameter; `NET-009` adds a `backoff_coordinator` parameter to its signature;
  `NET-010` rewrites the transport-failure path — the same `continue` at `:504-505`
  that `NET-002` names. Applied independently, in either order, at least one of the four
  edits lands on a line another has already moved. Filed as `VAL-002`.
- **No circular dependency.** `NET-001` (the merge destroys its own inputs) and
  `NET-007` (a per-request budget governs a local concat) are the pair most likely to
  be circular; they are not. Each can be fixed first, in either order, without the
  other. What exists between them is a *coupling, not an ordering constraint*: lowering
  `download_timeout` shortens each merge stage's budget, so it makes the `NET-001`
  loss more likely. That raises `NET-001`'s blast radius; it does not order the fixes.
- **No fragile insertion point.** Every accepted finding anchors to a named function,
  class, field or lifecycle boundary. None anchors to a line number alone in a way that
  a sibling fix would move. `NET-001`'s recommendation names
  `_perform_final_merge`'s success path and `_merge_batch_segments`'s unlink loop — both
  stable symbols.
- **One hidden chain, recorded, not filed.** `NET-001` defers "the retention/residue
  side of the leftover `batch_*.ts` and `batch_list_*.txt` files" to phase `07`. Phase
  `07` has produced no findings file. A fixer acting on `NET-001` alone will leave
  `final_list.txt` and a failed `batch_*.ts` on disk after a failure, because
  `_perform_final_merge` unlinks its list only on the success path
  (`ffmpeg_utils.py:358`) and nothing else removes it. That is a real residue, but it
  is phase `07`'s subject and is **not** filed here. It is named so the dependency is
  not discovered late.

---

## Findings

### NET-001: A successful batch merge destroys its own inputs, and the failure path destroys the only remaining copy — silently

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived independently from `src/vkdownloader/services/ffmpeg_utils.py`
>   with the process-launch boundary replaced by a local stub that reads the concat list
>   and exits with a chosen status. The claim reproduces exactly. 250 segments, final
>   merge forced to fail: `_merge_segments_batched` returned `None`, **0 of 250**
>   originals survived, the output was absent. 150 segments, same forced failure: **0 of
>   150**. 250 segments with the *second* batch forced to fail: **150 of 250** survived,
>   indices `00100`–`00249`; `00000`–`00099` were destroyed, and so was the
>   `batch_00000.ts` that had replaced them, because the `finally` at `:511-515` unlinks
>   every accumulated temp. The mechanism in the report's description is the mechanism in
>   the code: `_merge_batch_segments` unlinks its own inputs at `:314-317` immediately on
>   success, and the `finally` unlinks the batch temps on every non-success exit.
>   The silence claim is confirmed: `_log_preserve_segments` is guarded on
>   `segment_count > 0` (`segment_downloader.py:938`), so a total loss emits nothing. The
>   miscount claim is confirmed: the reporter counts `*.ts`, which includes a failed
>   `batch_*.ts`.
>   **Two corrections to the report's evidence, neither of which changes the finding.**
>   (1) The inventory at stage exit is **not** empty: `_perform_final_merge` unlinks
>   `final_list.txt` only on its success path (`ffmpeg_utils.py:358`), so the list file
>   survives the failure. (2) "The process records nothing whatsoever — no output file,
>   no exception, no residue line" is inaccurate. `_perform_final_merge` emits
>   `logger.error("final_merge_failed", …)` (`:363`) and the batch stage emits
>   `batch_merge_failed` (`:311`). What is true, and is the substance of the finding: the
>   `error` record is reduced by the batch layer to a bare status string
>   (`batch_downloader.py:126-156`, printed at `:431-432`), and nothing anywhere states
>   that the whole transfer must be repeated.
> - **Severity re-derived from this run's own evidence: CRITICAL — confirmed.** The
>   loss is total, deterministic, irreversible and silent to the operator, and it is the
>   only irreversible loss in the report. The report's `RUNTIME-ERROR` type is correct
>   under the format's guide: something was observed failing.
> - **See also:** `NET-007` (a lowered `download_timeout` shortens each merge stage's
>   budget, so it makes this loss more likely — a coupling, not an ordering constraint);
>   Checkpoint 4, *hidden chain* (the surviving `final_list.txt` is phase `07`'s subject).

| Field | Value |
|-------|-------|
| **ID** | NET-001 |
| **Severity** | CRITICAL |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** `_merge_segments_batched` runs ⌈N/100⌉ batch stages and
one final stage. Each batch stage unlinks its own input segments on success
(`ffmpeg_utils.py:314-317`) before any later stage has run. If a later stage fails, the
`finally` at `:511-515` unlinks the batch temps that had been produced. Both copies of
the already-merged bytes are then gone. The residue reporter
(`segment_downloader.py:930-939`) is guarded on `count > 0` and emits nothing in exactly
the case where nothing survived.

**Evidence (this run):** the process-launch boundary replaced by a local stub; three
cases; 250 / 150 / 250 segments; results quoted in the Validation Note above.

**Recommendation (as reported, unchanged; the report's carve-out to phase `07` for the
leftover `batch_*.ts` / `batch_list_*.txt` files is accepted):** make the batch stage
non-destructive until the whole merge has succeeded — delete the input segments only in
`_perform_final_merge`'s success path, not per batch at `:314-317`. Remove or restrict
the `finally` unlink at `:511-515`. Have `_log_preserve_segments` report unconditionally,
count 0 included, so "nothing was kept" is stated rather than inferred.

---

### NET-002: The manifest-fetch layer has no retry policy — a 429 or 5xx on the playlist abandons the transfer on the first response, and the status is never recorded

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from `src/vkdownloader/services/segment_downloader.py` with a
>   stubbed session, one run per status, `max_retries=3`. Every row of the report's
>   Matrix 1 reproduces: statuses 200, 400, 401, 403, 404, 408, 410, 425, 429, 500, 501,
>   502, 503, 504, 507 each produced **exactly 1 request** and returned `None` for every
>   status but 200. A connection-level exception produced **3 requests** and returned
>   `None`. The mechanism is `segment_downloader.py:512-513`
>   (`if status not in (403, 410) or not extractor: return None`) reached before the loop
>   can iterate, and `:504-505` (`continue` with no delay) for the transport path. The
>   logging claim is confirmed by reading: `_fetch_single_playlist` logs only
>   `playlist_fetch_failed` on `aiohttp.ClientError` (`:461-463`); no status value is
>   carried into any log line on the status path, and `_fetch_playlist_with_retry` has no
>   `backoff_coordinator` parameter to notify.
>   **Distinctness confirmed.** This is *not* the `max_retries` plumbing phase 02 owns
>   (`CFG-002`, `model_copy(update=…)` at `downloader.py:652-653` admitting out-of-range
>   values). Different subject, different file, different cause; neither fix touches the
>   other. It also does not duplicate `NET-010` — see the *See also* line.
> - **Severity re-derived from this run's own evidence: HIGH — confirmed.** A
>   rate-limited playlist GET abandons the entire transfer on the first response, with no
>   retry, no delay and no diagnosis, on precisely the condition the retry machinery
>   exists to survive. The transport-failure path *is* retried, so a transient network
>   error is covered; a status response is not. That asymmetry is the finding.
> - **See also:** `NET-010` — its first bullet (the manifest layer's `continue` at
>   `:504-505`) is **subsumed by this finding** and is not re-filed there; `NET-010`'s
>   media-part bullets are distinct and are retained under that ID. `NET-009` (the
>   manifest layer cannot consult the shared pause). `VAL-002` (all of these prescribe
>   edits inside the same function).

| Field | Value |
|-------|-------|
| **ID** | NET-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** `_fetch_playlist_with_retry`
(`segment_downloader.py:484-523`) has a retry *loop* but no retry *policy*. It retries
only a transport-level failure — with `continue` and no delay at `:504-505` — and a
403/410 that a forced re-extraction can answer. Every other status returns `None` on the
first response. The status is never recorded.

**Evidence (this run):** a stubbed session driven once per status; request count and
return value per status, quoted in the Validation Note.

**Recommendation (as reported):** give the manifest layer the same policy table the
media-part layers use — 429/500/502/503/504 (and 408/425) through `_compute_backoff_delay`
+ `_wait_with_shutdown` — notify the shared pause coordinator the way `:189-196` does for
parts, log the status on every non-200 outcome, pass the coordinator into
`_fetch_playlist_with_retry`, keep 403/410 on the refresh path, and add a delay to the
`continue` at `:504-505`.

---

### NET-003: `--quality worst` downloads the best stream, and the selected stream address is never given to the child at all

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived by driving `_build_ytdlp_cli_command` once per
>   `QualityEnum` member and reading the `-f` argument out of the returned argv. The
>   inversion reproduces exactly: 240 → `best[height<=240]`, 360 → `best[height<=360]`,
>   480 → `best[height<=480]`, 720 → `best[height<=720]`, 1080 → `best[height<=1080]`,
>   1440 → `best[height<=1440]`, 2160 → `best[height<=2160]`, best → `best`,
>   **worst → `best`**. The mechanism is
>   `ytdlp_downloader.py:256-258` (`f"best[height<={quality_str}]" if quality_str and
>   quality_str.isdigit() else "best"`) fed by `:606` (`quality.replace("p","")`), and
>   `QualityEnum.WORST` is the string `"worst"`, which is not a digit. The
>   address-is-never-passed claim is confirmed by signature: `_download_with_ytdlp`
>   (`ytdlp_downloader.py:564-574`) has no `m3u8_url` parameter, and `:623` appends the
>   page URL — `cmd.append(video_url)` — as the child's positional argument. The selected
>   address computed at `downloader.py:476` and threaded through `perform_download` is
>   used only by the ffmpeg method and by the segment fallback.
>   **One correction to the report's evidence, which narrows a secondary claim.** "For
>   numeric qualities the app's exact selection is likewise re-derived by the child's own
>   ranking against a `<=` filter" is a correct description but is not a defect in the
>   direction the report implies: `best[height<=N]` is a superset filter and yt-dlp picks
>   the highest format within it, which is what `QualitySelector` picks when an exact-N
>   stream exists. The genuine divergence is that the app is **stricter** — it raises
>   `QualityNotAvailableError` when no exact label matches — so a numeric request can be
>   silently downgraded by the child where the app would have refused. That is a real
>   substitution, but a different one from the `worst` inversion, which is the finding.
> - **Severity re-derived from this run's own evidence: HIGH — confirmed.** A user who
>   asks for the worst quality receives the best one the origin offers, and nothing in
>   the log distinguishes the request from the delivery: the only quality record on the
>   path is the request echoed into `starting_ytdlp_download` (`:599-604`).
> - **See also:** `NET-015` (the ladder's other handoff asymmetry);
>   `NET-008` / `NET-005` (how the address that *is* used gets chosen).

| Field | Value |
|-------|-------|
| **ID** | NET-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** the ladder selects a stream with `QualitySelector.select`
and passes its URL as `m3u8_url`, but that URL never reaches the child. The child is
given the page URL and a format selector derived from the *request string*, so
`QualityEnum.WORST` becomes the literal selector `best`.

**Evidence (this run):** `_build_ytdlp_cli_command` invoked once per `QualityEnum`
member; the resulting `-f` argument quoted in the Validation Note.

**Recommendation (as reported):** pass the selected `m3u8_url` into `_download_with_ytdlp`
and give it to the child as the positional argument; if the child must re-select, derive
the selector from the *selected* stream's height rather than the request string, and
special-case `worst`; log the selected address and the delivered format.

---

### NET-004: A refreshed signed address is used for the manifest only — every media part is still requested from the stale host, with the fresh cookie

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from `src/vkdownloader/services/segment_downloader.py`.
>   `_fetch_playlist_with_retry`'s return annotation is `str | None` — it returns the
>   playlist **text only**. The refreshed address lives in the local `current_url`
>   (`:494`, assigned at `:518`) and is never returned: the function's only successful
>   `return` is `return playlist_text` at `:509`. The caller builds the download policy
>   with the *parameter* at `:835` (`m3u8_url=m3u8_url`), and
>   `_download_segment_concurrent` resolves every relative part against
>   `policy.m3u8_url` (`:683-687`). Meanwhile `_handle_token_refresh` rewrites the shared
>   dict in place — `headers["Cookie"] = new_cookies` (`:479`) — and that same dict is
>   the one carried into `DownloadPolicy.headers` and attached to every part request. The
>   report's core claim, a fresh credential sent to a stale host, is confirmed by reading
>   the two sites against each other; no scripted origin was needed to establish it.
>   **One correction, which narrows the security framing.** "The new cookie is also
>   disclosed to the old host on every part request" is true, but the old host is the
>   host the process was already addressing with the *old* cookie, so this is a
>   credential-forwarding to a host already in the trust path rather than a new
>   disclosure. The functional consequence is the stronger one and is unchanged: every
>   part is requested with the expired signature.
> - **Severity re-derived from this run's own evidence: HIGH — confirmed.** The recovery
>   path exists, is entered on 403/410, and produces a base address that is then discarded
>   — a browser extraction is spent to obtain an address the bytes are never fetched
>   from. Whether a real VK origin then 403s every part is not asserted here (no origin
>   was contacted); the structural fact is what is established.
> - **See also:** `NET-005` (which stream of the refreshed set is chosen — the other half
>   of the same refresh path, retained separately, not merged); `VAL-002` (this finding
>   changes the return type of a function three other findings also edit).

| Field | Value |
|-------|-------|
| **ID** | NET-004 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** the manifest refresh produces a replacement address and
uses it for the manifest request only. The session's download policy is still built from
the original argument, so every media part resolves against the old base — while the
cookie, rewritten in place, is the refreshed one.

**Evidence (this run):** the return annotation of `_fetch_playlist_with_retry`, the two
`return` statements in it, the `DownloadPolicy` construction site, the
`urljoin(policy.m3u8_url, …)` resolution site, and the in-place header rewrite — all read
and quoted in the Validation Note.

**Recommendation (as reported):** have `_fetch_playlist_with_retry` return the address it
actually succeeded with alongside the playlist text and pass that into
`DownloadPolicy.m3u8_url`; write the refreshed cookie only after the base is switched.

---

### NET-005: The manifest-refresh path substitutes the first stream for the selected quality, with no record of the substitution

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from `_refresh_token_and_retry`
>   (`src/vkdownloader/services/segment_downloader.py:426-446`). Its last statement is
>   `return str(streams[0].url), new_cookies or ""` — element zero, unconditionally, with
>   no quality argument in scope and no branch on the caller's selection. The extraction
>   it calls is `extract_streams_with_cookies(video_url, force_browser=True)`, which with
>   `force_browser=True` bypasses the `CookieSource` check at `extractor.py:167` and
>   always takes the browser path — so the report's claim that the production replacement
>   is always the `quality="best", height=None` record from `extractor.py:297-305` is
>   confirmed by reading the two sites together. The two sibling helpers named in the
>   report do branch and do log: `_attempt_segment_resume`
>   (`ytdlp_downloader.py:503-521`) and `_resolve_cookies` (`:756-774`) each test
>   `quality_enum == QualityEnum.BEST` and emit `fresh_token_obtained_for_resume` or
>   `browser_streams_selected` with the quality fields.
>   **Correction to the report's evidence method.** Its R5 table varies the *stubbed*
>   replacement stream's label per selection and observes that the label is never read.
>   That is a valid observation of the stub, but it demonstrates the code fact only; the
>   production consequence does not depend on the stub. The code fact — element zero,
>   unconditionally — is what this run re-derived, and it is sufficient on its own.
> - **Severity re-derived from this run's own evidence: HIGH — confirmed.** The
>   substitution is unconditional, so it applies to every quality, not only to numeric
>   ones: for `best` it is harmless (the ladder would have chosen a best stream anyway),
>   and for every numeric quality it replaces the requested stream with the browser's
>   first captured address. The only record on the path is
>   `logger.info("token_expired_fetching_new")` (`:515`), which carries no address, no
>   label and no selected value.
> - **See also:** `NET-004` (which *base* the parts resolve against — the other half of
>   the same refresh path); `NET-008` (why the browser's first captured address is
>   whatever it is); `VAL-002`.

| Field | Value |
|-------|-------|
| **ID** | NET-005 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** the manifest refresh returns the first stream the forced
re-extraction produced, whatever the caller selected, and records nothing about it —
while the two sibling refresh helpers in the same codebase branch on the selection and
log both the requested and the selected value.

**Evidence (this run):** the helper's return statement, the `force_browser` bypass at
`extractor.py:167`, the record it builds at `:297-305`, and the two sibling helpers'
branches — read and quoted above.

**Recommendation (as reported):** reuse the existing selection logic — parse the
caller's quality, run `QualitySelector` over the refreshed streams when it is `BEST`, and
apply the same explicit "preselected URL retained" branch the other two helpers use when
it is numeric; log the selected and the delivered label in one record. The carve-out to
phase `08` for the rendering of a non-selectable label in an error's alternatives is
accepted.

---

### NET-006: Two of the four terms of the composed HTTP timeout are dead at the configured floor — and one is dead at every value in range

> **Validation Note:**
> - **Action:** validated · **Severity re-derived from this run's own evidence:
>   HIGH → MEDIUM.**
> - **Detail:** Re-derived by composing the `aiohttp.ClientTimeout` exactly as the three
>   call sites do — `downloader_throttle.py:200-205`,
>   `segment_downloader.py:224-229`, `segment_downloader.py:495-500` — and reading every
>   term at the floor, default and ceiling permitted by `config.py:61-66`
>   (`ge=30, le=3600, default=300`). Results: `download_timeout=30` → `total=30,
>   connect=7, sock_connect=30, sock_read=60`; `300` → `total=300, connect=30,
>   sock_connect=30, sock_read=60`; `3600` → `total=3600, connect=30, sock_connect=30,
>   sock_read=60`. The structural claim is confirmed: at the floor `sock_read` (60)
>   **exceeds** the `total` that contains it, so it can never fire; at every value
>   `sock_connect` is ≥ the `connect` term, which already bounds pool acquisition and, for
>   a new connection, supersedes it, so `sock_connect` is redundant. All three sites are
>   byte-identical, confirmed by reading each.
>   **Two corrections to the report's evidence, both of which lower the consequence.**
>   (1) `sock_connect` is *redundant*, not unreachable: at the default and the ceiling
>   `connect == sock_connect == 30`, so both timers bound the same interval and neither
>   strictly shadows the other. "Dead at every value in range" overstates it; "adds
>   nothing that `connect` does not already bound" is exact.
>   (2) The material correction: "`sock_read` still pinned at 60 s: a long,
>   silently-truncating download on a slow CDN is killed at 60 s of read inactivity while
>   the setting reads 3600" is **wrong**. `sock_read` is an inactivity ceiling, not a
>   duration ceiling — it fires only after 60 s with no data on the socket. A slow but
>   steady transfer is not killed by it, and a long transfer is not truncated by it. The
>   real consequence is the one already stated for the floor: an operator who *shortens*
>   the setting cannot obtain a read budget longer than the whole-request budget, because
>   the container fires first.
> - **Why the severity moves.** With the consequence corrected, what remains is two
>   literals in a composed budget that duplicate, or exceed, the term containing them.
>   That is a real deviation from the setting's declared purpose, and it is worth fixing,
>   but no incorrect result, no data loss and no security boundary follows from it. HIGH
>   was carried by the truncation claim, and that claim does not survive. MEDIUM is the
>   strongest severity the observed consequence supports.
> - **See also:** `NET-007` (the same setting, a different reuse); `NET-013` (derived vs
>   literal terms, stated as a reach property rather than as a deadline property).

| Field | Value |
|-------|-------|
| **ID** | NET-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** every aiohttp request builds a four-term deadline from one
configured value: `total` = the setting, `connect` = `min(30, setting // 4)`,
`sock_connect` = 30, `sock_read` = 60. At the configured floor the read term exceeds the
budget that contains it; at every value the connect term is redundant.

**Evidence (this run):** the composed `ClientTimeout` read back at 30 / 300 / 3600, and
the three identical construction sites — quoted in the Validation Note.

**Recommendation (as reported, with the priority inverted to match the corrected
consequence):** remove `sock_connect`, which adds nothing once `connect` is set; make
`sock_read` a function of the setting (`min(60, download_timeout)` if it is meant to be
inside the budget, or the setting itself if a per-read ceiling is intended) rather than a
literal; if a hard 60 s read ceiling is deliberate it needs its own bounded setting;
collapse the three identical copies into one helper so the floor, default and ceiling are
checkable in one place.

---

### NET-007: One configured HTTP request timeout is reused unchanged as the local concat's budget, while the two stages that actually transfer bytes have no budget at all

> **Validation Note:**
> - **Action:** validated · **Severity re-derived from this run's own evidence:
>   HIGH → MEDIUM.**
> - **Detail:** The first half reproduces exactly. `config.py:61-66` declares
>   `download_timeout` as "HTTP client timeout in seconds for individual segment requests
>   and playlist fetches". `segment_downloader.py:614-616` hands that same value to
>   `_merge_segments_batched`, which passes it to `_await_ffmpeg_with_timeout` **per
>   subprocess** at `ffmpeg_utils.py:304` (batch stage) and `:351` (final stage), each an
>   `asyncio.wait_for(process.communicate(), timeout=download_timeout)`. The worst case
>   for 250 segments at the default is therefore 3 × 300 s + 1 × 300 s = 1200 s of budget
>   for a purely local `concat` of files already on disk. The literal count is confirmed:
>   `DownloadPolicy.download_timeout: int = 300` (`segment_downloader.py:66`), five
>   function defaults at `:146, :217, :282, :314, :370`, against
>   `downloader_throttle.py:180`'s correctly derived
>   `download_timeout: int = _DEFAULT_DOWNLOAD_TIMEOUT`.
>   **The second half is already-correct-by-design and its recommendation is withdrawn.**
>   "The two stages that do transfer bytes impose no budget at all" is true of
>   `downloader.py:360-371` and `ytdlp_downloader.py:672-682`, which both await a bare
>   `process.wait()`. It is not an oversight: `ytdlp_downloader.py:580-582` states the
>   decision — "yt-dlp has its own `--socket-timeout`, `-R`, `--fragment-retries`, and
>   `-N` for network robustness — no application-level download timeout is imposed,
>   avoiding premature kill of legitimate long downloads." Wrapping those `process.wait()`
>   calls in `asyncio.wait_for` would re-introduce exactly the premature kill that comment
>   names, and would make a legitimate long download fail. That half of the recommendation
>   is rejected; the finding stands on the first half alone.
>   **The consequence the report states is the weaker one; a stronger one it does not.**
>   The report argues that *raising* the setting inflates the merge budget. That is
>   permissive — a larger ceiling on a local operation wastes time but produces no wrong
>   result. The consequential direction is the opposite: an operator who *lowers*
>   `download_timeout` to 30 to shorten network stalls also caps each of the ⌈N/100⌉ + 1
>   merge stages at 30 s, which on a slow volume can abort a merge that would otherwise
>   have succeeded — and per `NET-001` that abort destroys the input segments. The
>   consequence is therefore a coupling to `NET-001`, not a standalone severity driver.
> - **Why the severity moves.** A mis-scoped ceiling is a real spec deviation against the
>   setting's own declared description, and the coupling to `NET-001` gives it teeth. But
>   as a standalone finding its blast radius is wasted time in one direction and a
>   lower-probability merge abort in the other — not data loss in its own right, and not a
>   wrong result. MEDIUM is the strongest severity the observed consequence supports.
> - **See also:** `NET-006` (the same setting, reused differently); `NET-001` (the loss
>   this one can trigger); `NET-013` (the same "one value, two meanings" property stated
>   as a reach table — the two findings overlap in framing and are **not** merged, because
>   this one is about *which stage consumes the value* and `NET-013` is about *which
>   transport receives it*).

| Field | Value |
|-------|-------|
| **ID** | NET-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** a setting declared as a per-HTTP-request timeout is applied
unchanged, per subprocess, as the budget for a local file concat; and the two stages that
do transfer bytes are deliberately unbounded, by a decision the code documents.

**Evidence (this run):** the setting's declared description at `config.py:61-66`, the
hand-off at `segment_downloader.py:614-616`, the two `asyncio.wait_for` sites in
`ffmpeg_utils.py`, the six literal `300` defaults, and the design comment at
`ytdlp_downloader.py:580-582` — all read and quoted above.

**Recommendation (narrowed to the half that survives):** give the merge stages their own
budget, derived from the number of stages and the measured segment size or from a separate
bounded setting, and pass it once rather than per subprocess; replace the six literal
`= 300` defaults with the value derived from the settings model, as
`downloader_throttle.py:19` already does. **Not recommended:** adding `wait_for` around
the two transfer stages' `process.wait()` — see the Validation Note.

---

### NET-008: The intercepted address is an unconstrained "first captured wins", and the quality label attached to it is not a member of the declared enumeration

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from `src/vkdownloader/infrastructure/network_monitor.py` and
>   `src/vkdownloader/services/extractor.py`. The capture predicate is
>   `if ".m3u8" in url.lower() or self.M3U8_PATTERN.search(url)` (`:62`) with
>   `M3U8_PATTERN = re.compile(r"(?:https?://)?[^\s\"'<>]+\.m3u8(?:\?[^\s\"'<>]*)?")`
>   (`:21`) — no host constraint, no quality constraint, no preference for a media
>   playlist over a manifest — followed by a dedup on exact string (`:64-65`) and
>   append-in-arrival-order. The selection surface then takes element zero
>   unconditionally: `stream = Stream(url=monitor.m3u8_urls[0], format=StreamFormat.HLS,
>   quality="best", width=None, height=None)` (`extractor.py:297-305`). The label claim is
>   confirmed by enumerating the declared members:
>   `['240','360','480','720','1080','1440','2160','best','worst']` — **no `unknown`**.
>   The second label in the report, produced for a record with no height by
>   `extractor.py:63` (`quality=f"{height}p" if height else "unknown"`), is likewise not
>   a member, so `QualityEnum("unknown")` raises — confirmed. `list_available_qualities`
>   returns those labels unchanged (`quality.py:95-116`) and `downloader.py:685` logs
>   `available[:8]` containing them.
>   **One correction, which narrows the consequence.** "…and it is then handed to ffmpeg
>   and to the segment downloader together with the session cookie
>   (`downloader.py:270-297`, `segment_downloader.py:900-905`)" holds only when cookies
>   are in play: `segment_downloader.py:904-905` sets the `Cookie` header only when
>   `request.cookies` is non-empty, and the browser surface is not entered at all when
>   `cookie_source == CookieSource.NONE` (the declared default, `config.py:115-118`) except
>   under a forced refresh. The selection defect itself is unconditional and is the
>   finding; the credential-disclosure framing is conditional.
> - **Severity re-derived from this run's own evidence: HIGH — confirmed.** The winning
>   address is chosen by arrival order with no constraint of any kind, and the address that
>   wins is the one handed to both transfer stages. A third-party host whose URL ends in
>   `.m3u8` and is fetched first becomes the delivered source for the whole download.
> - **See also:** `NET-016` (the normaliser that can invent a host before any host filter
>   could run); `NET-005` (the refresh path takes the same element zero);
>   phase `08` for the rendering of a non-selectable label in operator output — the
>   report's carve-out is accepted, not double-filed.

| Field | Value |
|-------|-------|
| **ID** | NET-008 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/infrastructure/network_monitor.py`, `src/vkdownloader/services/quality.py` |
| **Classification** | mandatory |

**Description (re-derived):** captured addresses are appended in arrival order with no
host, quality or playlist-type constraint, and the extraction surface takes element zero
unconditionally; the labels it attaches are not members of the declared quality
enumeration, so they cannot be re-requested.

**Evidence (this run):** the capture predicate and pattern, the dedup, the element-zero
selection, the enumerated `QualityEnum` members, the label produced for a heightless
record, and the enumeration error on re-request — all read or executed, quoted above.

**Recommendation (as reported):** filter captured addresses by host against the expected
CDN suffix, prefer a media playlist over a manifest, record the host and label chosen in
the log; add `"unknown"` as a `QualityEnum` member or map it in `_find_quality_match` so
the label the enumeration produces is one the enumeration accepts; deduplicate the
alternatives list.

---

### NET-009: The shared per-origin pause is consulted at a strict subset of the sites that could consult it, and is keyed narrower than the resource it protects

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived by an index-scoped search of `src/` for every call site of
>   `pause` and `wait_if_paused`. The list is exactly three, and matches the report's:
>   `segment_downloader.py:196` — `await backoff_coordinator.pause(video_url, 10.0)`, the
>   only **set**; `segment_downloader.py:267` — `wait_if_paused(video_url)`, the only
>   **consult** inside the segment layer; `ytdlp_downloader.py:401` — the yt-dlp retry
>   loop. The three sites the report names as unable to consult it are confirmed by
>   signature: `_fetch_playlist_with_retry` (`segment_downloader.py:484-492`) has no
>   coordinator parameter; `_download_segment_sequential` (`:139-147`) has none either, and
>   `_download_segment:389-398` routes to it whenever `max_concurrent_downloads == 1`;
>   `extractor.py:184-258` runs the in-process library on a worker thread with no pause
>   object in scope at all. The key is the **page** URL — `pause(video_url, 10.0)`, where
>   `video_url` is what the user supplied — while the pressure is on the CDN host serving
>   every item, and `10.0` is a literal set for every retryable status alike
>   (`_is_retryable_status` at `:184-186` is `status in RETRYABLE_STATUS_CODES`, i.e.
>   429/500/502/503/504 — confirmed at `downloader_throttle.py:22`).
>   **One correction, which narrows the consequence.** "A 429 storm from the CDN is met
>   with unthrottled retries" overstates the sequential-strategy case. That strategy *does*
>   delay on the response path: `downloader_throttle.py:234-247` computes a backoff and
>   awaits `_wait_with_shutdown` for every retryable status. What it lacks is the
>   **shared** pause, so `N` videos in a batch each delay independently against one origin
>   instead of one of them pausing all of them. "Delayed but not shared" is the exact
>   statement; "unthrottled" is not.
> - **Severity re-derived from this run's own evidence: MEDIUM — confirmed.** The defect is
>   a mechanism that exists for a stated purpose and is reachable from a strict subset of
>   the sites that need it, with a key that does not name the resource under pressure. The
>   corrected consequence is a lost coordination, not an absent throttle, and the affected
>   setting (`max_concurrent_downloads == 1`, documented as the anti-detection mode at
>   `config.py:96-97`) is a deliberate mode rather than the default.
> - **See also:** `NET-002` and `NET-010` (the manifest layer's two faces);
>   `VAL-002` (all three prescribe edits in one function).

| Field | Value |
|-------|-------|
| **ID** | NET-009 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description (re-derived):** the process's only per-origin pause is set from one site
and consulted from two, while three sites that make origin requests — the manifest layer,
the sequential media-part strategy, and the in-process extraction — cannot reach it. Its
key is the page URL, not the origin, and its duration is a literal.

**Evidence (this run):** the three-call-site search result, the four signatures, and the
retryable-status set — quoted in the Validation Note.

**Recommendation (as reported):** give the manifest layer and the sequential strategy the
coordinator parameter the parallel strategy has, pass it through `DownloadPolicy`, consult
the pause before the in-process extraction's first request, key the pause on the CDN host
rather than the page URL, and derive the 10 s duration from a bounded setting.

---

### NET-010: A connection-level failure on a retrying path is retried with zero measured delay, and the two media-part strategies disagree on whether to retry it at all

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from `src/vkdownloader/services/segment_downloader.py` and
>   `src/vkdownloader/services/downloader_throttle.py` with a stubbed session, measuring
>   request count and wall-clock spacing. Every row reproduces. **Parallel strategy**
>   (`_download_segment_parallel`): a connection-level exception → 3 requests, spacing
>   `[0.0, 0.0]`, no pause set; a 200 with an empty body → 3 requests, spacing
>   `[0.0, 0.0]`; a 429 with `Retry-After: 2` → 3 requests, spacing `[10.0, 10.0]`.
>   **Sequential strategy** (`_retry_429_with_backoff`): a connection-level exception →
>   **1 request**, terminal on the first attempt, because `:260-267` catches
>   `(aiohttp.ClientError, TimeoutError)` and `return None`; a 429 with `Retry-After: 2` →
>   3 requests and **three** `segment_retry_429` records, i.e. a third wait after the
>   final attempt, against only two observable inter-request gaps; a 408 → 1 request, as
>   408 is not in `RETRYABLE_STATUS_CODES` (`{429, 500, 502, 503, 504}`), so it fails fast
>   on both strategies — the report's Matrix 2 lists 408 for the parallel layer only, and
>   this run observed the same fail-fast on the sequential one.
>   The asymmetry the report describes is therefore real in both directions and the
>   no-delay claim holds exactly: `[0.0, 0.0]` is measured, not inferred.
>   **One scoping correction.** The report's first bullet — the manifest layer's
>   `continue` at `:504-505` with no delay — is a strict subset of `NET-002`, which files
>   the whole manifest-layer retry policy including that exact line. It is **not
>   re-filed here**; this finding is retained for the two media-part strategies and for
>   the sleep-after-the-final-attempt asymmetry, which `NET-002` does not touch.
> - **Severity re-derived from this run's own evidence: MEDIUM — confirmed.** The same
>   transient failure produces three requests inside one millisecond on two layers, and one
>   request and a failed download on the third. The cost of the wasted wait after the
>   final attempt is bounded by one `Retry-After` interval and is a cost, not a wrong
>   result; the no-delay retry loop is the part that expresses the opposite of the
>   etiquette the machinery exists for.
> - **See also:** `NET-002` (absorbed manifest-layer bullet); `NET-009` (the pause these
>   retries fail to notify); `NET-018` (the delay computation both strategies call);
>   `VAL-002`.

| Field | Value |
|-------|-------|
| **ID** | NET-010 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory |

**Description (re-derived):** a connection-level failure is retried instantly on the
parallel media-part strategy, is not retried at all on the sequential one, and on both the
sequential strategy sleeps a full `Retry-After` interval after its final attempt.

**Evidence (this run):** six stubbed-session runs across the two strategies — request
count and measured inter-request spacing quoted in the Validation Note.

**Recommendation (as reported, with the manifest-layer clause dropped as absorbed into
`NET-002`):** route the transport-level failure through the same policy as a response on
both media-part layers — compute a delay from the attempt index, apply it via
`_wait_with_shutdown`, and notify the shared pause the way
`_notify_backoff_for_retryable_status` does; apply `_should_continue_on_retry` (or its
equivalent) in `_retry_429_with_backoff` so the final attempt does not sleep; make the
sequential strategy retry transport failures to the same `max_retries` budget as the
parallel one.

---

### NET-011: The response-size guard measures after reading — on the declared-length-absent path the whole body is materialised before the cap is applied

> **Validation Note:**
> - **Action:** validated · **Severity re-derived from this run's own evidence:
>   MEDIUM → LOW.**
> - **Detail:** The mechanism is confirmed by reading `src/vkdownloader/infrastructure/
>   network_monitor.py:69-105`. The declared-length pre-read is exact: `:74-83` computes
>   `int(content_length)` and skips when `size_bytes >= self.MAX_JSON_BODY_BYTES`
>   (1,000,000, `:23`), so the guard fires **at** the cap and not one byte below. A
>   `ValueError` on the malformed header falls through `except ValueError: pass` (`:84-85`)
>   to the unbounded path. On that path the code calls `await response.body()` at `:90` —
>   an all-or-nothing materialisation — and only then compares `len(body)` to the cap at
>   `:99-105`. The cap therefore bounds parsing work, not memory, on exactly the two paths
>   the report names (header absent, header unparseable). The m3u8 branch (`:62-66`) reads
>   no body and is unaffected, as stated.
>   **Two corrections.** (1) "The comment at `:87-88` states the opposite" is **not**
>   right. The comment reads "Enforce a byte cap even when Content-Length is absent" — and
>   a byte cap *is* enforced in that case. What is not enforced is a *memory* bound. The
>   comment is accurate about what it claims; the code does not do what the surrounding
>   guard's intent (`:72`, "avoid memory issues") suggests. (2) **The recommendation is
>   withdrawn as written.** "Skip the branch when it is absent or unparseable" would
>   disable m3u8 discovery for every chunked or streamed JSON response, which is a common
>   and entirely legitimate shape — a functional regression traded for a memory bound. The
>   Playwright `Response` API exposes `body()` as an all-or-nothing call and no streaming
>   reader, so a true memory bound is not expressible here. The honest options are to keep
>   the cap and correct the comment to state that it bounds parsing rather than memory, or
>   to move the guard to a surface that can bound the read. **The comment fix is the part
>   worth taking.**
> - **Why the severity moves.** With the framing corrected and the aggressive fix
>   withdrawn, what remains is a documented-vs-actual gap of small operational weight: a
>   large JSON body from the video page is buffered in the driver process before the cap
>   is consulted. No incorrect result, no data loss, no security boundary. LOW is the
>   strongest severity the observed consequence supports.
> - **See also:** `NET-016` (the same module's address normaliser — the two findings share
>   a file but neither cause; retained separately, not merged).

| Field | Value |
|-------|-------|
| **ID** | NET-011 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | mandatory |

**Description (re-derived):** the JSON-parsing branch caps the body *after* reading it, so
on the paths where the declared length is absent or unparseable the cap bounds parsing
work rather than memory.

**Evidence (this run):** the pre-read guard, the `ValueError` fall-through, the
all-or-nothing `body()` call, and the post-read comparison — all read and quoted above.

**Recommendation (corrected from the report's):** correct the comment at `:87-88` to state
that the cap bounds parsing rather than memory, which is what the code does. **Not
recommended as reported:** skipping the branch when `Content-Length` is absent or
unparseable — see the Validation Note; it would disable discovery for chunked responses.

---

### NET-012: Acceptance admits a foreign origin that merely contains the pattern, and a negative identifier component; the derived identifier then reaches consumers that assume the canonical form

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived by driving the acceptance predicate and the identifier
>   derivation over a fixed input table. Every row of the report's R9 table reproduces,
>   including the two that establish the boundary — the near misses
>   `https://vkvideo.ru/video_123_456`, `https://vkvideo.ru/videos-123_456`,
>   `https://vkvideo.ru/video-1O3_456` and the empty string are all **rejected**, while
>   these are **accepted**: a foreign origin whose path embeds the pattern
>   (`https://evil.example/video-123_456`), a foreign origin whose *query value* embeds it
>   (`https://evil.example/watch?next=https%3A%2F%2Fvkvideo.ru%2Fvideo-123_456`), the
>   bare pattern with no scheme or origin (`video-123_456`), a negative owner component
>   (`https://vkvideo.ru/video--123_456` → `owner_id = -123` → `video_id_full =
>   "-123_456"`), and the canonical form with a trailing path
>   (`https://vkvideo.ru/video-1_2/extra`). The predicate is
>   `VIDEO_ID_PATTERN = re.compile(r"video-(-?\d+)_(\d+)")` with
>   `bool(VIDEO_ID_PATTERN.search(url))` (`extractor.py:25`, `:37`) — an unanchored
>   search over the whole reference, with `?` admitting the leading `-`. The gate is not
>   confined to the single-download path: `cli.py:249` applies it to every line of the
>   user-supplied batch list. The consumer divergence is confirmed and measured: the four
>   raw-string slicers — `downloader.py:530`, `ytdlp_downloader.py:608`,
>   `segment_downloader.py:602` and `:706`, all `url.split("_")[-1]` — yield `456` for
>   each accepted foreign-origin input and `2/extra` for the trailing-path input, while
>   the parser yields `1_2` and `123_456` respectively.
>   **One correction, which changes the type of half the finding.** The report classes the
>   acceptance half as a specification deviation, but the code matches its own declared
>   contract: `is_valid_video_url`'s docstring (`:35`) says "True if the URL **contains** a
>   valid VK video identifier". The behaviour is the contract; the contract is weak. That
>   half is therefore a hardening recommendation, not a deviation. The consumer half — the
>   parser deriving the identifier correctly and four sites then re-deriving a different one
>   from the raw string — is a genuine correctness defect, and the finding keeps its
>   `SPEC-DEVIATION` label on that half alone.
> - **Severity re-derived from this run's own evidence: MEDIUM — confirmed.** An accepted
>   foreign-origin URL is counted valid, passed to `page.goto(url)` (`extractor.py:273`) on
>   the browser path and to the third-party downloader on the library path, so the gate the
>   batch list relies on is a substring test rather than an origin test; and the identifier
>   that identifies the video in the progress display is not the one the parser produced.
> - **See also:** `NET-008` (the address hand-off that follows the accepted URL);
>   `VAL-002` — none; this finding's recommendation touches `cli.py:249` and
>   `extractor.py:25-107`, which no other accepted finding edits.

| Field | Value |
|-------|-------|
| **ID** | NET-012 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description (re-derived):** acceptance is an unanchored substring search over the whole
reference, admitting foreign origins, a bare pattern, a trailing path and a negative owner
component; the identifier the parser derives is then re-derived differently by four
consumers that slice the raw string.

**Evidence (this run):** the fourteen-row accept/reject and derived-identifier table, plus
the consumer list and the values each consumer yields for the accepted non-canonical
inputs — all quoted in the Validation Note.

**Recommendation (as reported):** anchor acceptance to the origin and to the path after
`urlparse`, require an expected host, reject a negative owner component at acceptance,
and derive the per-item identifier once in the parser and pass it to the four consumers
instead of re-slicing the raw URL.

---

### NET-013: Request-fidelity and verification policies reach a strict subset of the transports; the two surfaces of the same third-party downloader present different identities

> **Validation Note:**
> - **Action:** reclassified · **Severity re-derived from this run's own evidence:
>   MEDIUM → LOW · Classification corrected `recommended` → `advisory`.** The `Type`
>   label is unchanged: `BEST-PRACTICE` is the correct label for what survives.
> - **Detail, part 1 — confirmed.** The transport inventory reproduces from the source:
>   T1 `aiohttp.ClientSession` (`segment_downloader.py:797`), T2 the third-party
>   downloader as an in-process library on a worker thread (`extractor.py:211`, `:243`),
>   T3 the same downloader as a child process (`ytdlp_downloader.py:631`), T4 ffmpeg as a
>   child process transferring a live stream (`downloader.py:305`), T5 ffmpeg doing a local
>   concat (`ffmpeg_utils.py:297`, `:344`), T6 Chromium via Playwright
>   (`browser.py:40`). The T2 identity gap is confirmed by reading the option object at
>   `extractor.py:193-205` — it carries `quiet`, `no_warnings`, `extract_flat`,
>   `nocheckcertificate`, `socket_timeout`, `retries`, `fragment_retries`, `throttled_rate`
>   and **no** `user_agent` and **no** `http_headers` key — against the T3 argv built at
>   `ytdlp_downloader.py:284-287`, which carries `--user-agent` and `--referer`. The
>   verification-posture claim is confirmed: four flag sites
>   (`extractor.py:197`, `ytdlp_downloader.py:298-299`, `segment_downloader.py:539-542`,
>   `downloader.py:298-300`) and two warning sites
>   (`segment_downloader.py:542`, `ytdlp_downloader.py:611-612`) — so two of the four
>   disable verification with no warning in their own module. T6's posture is undeclared:
>   `browser.py:103-108` calls `new_context(viewport=…, user_agent=…, locale=…,
>   timezone_id=…)` and never passes `ignore_https_errors`.
> - **Detail, part 2 — two sub-claims rejected as already-correct-by-design.**
>   (a) *"`throttled_rate` — the setting whose declared purpose is rate limiting — governs
>   the two surfaces that are not the ones carrying most of the traffic."* The setting's
>   declared description (`config.py:99-104`) scopes it to yt-dlp: "If **yt-dlp's**
>   download rate falls below this threshold, yt-dlp aborts the download". The two
>   surfaces that reach it are exactly the two yt-dlp surfaces. Its reach is the declared
>   contract, not a gap, and the recommendation "say so in the setting's description"
>   asks for something the description already says.
>   (b) *"Nothing records the product [of the concurrency bounds]."* `config.py:89-98`
>   already records both levels in the setting's own description: the batch semaphore
>   "gates one permit per video (acquired once per video); each video's segment fan-out is
>   bounded separately by a semaphore of the same size owned by the segment layer". That
>   sub-claim is the substance of `NET-014` and is not re-filed here.
> - **Label legality.** The finding carried `Classification: recommended`. The report
>   format (`.ai/audit/templates/audit-findings.md:27` and `:74`) defines exactly
>   `mandatory | advisory`. `recommended` is not one of them; it is the only finding in the
>   report that leaves the enumeration. Corrected to `advisory`, which is the value the
>   surviving content warrants.
> - **One evidence imprecision, recorded.** The reach table's read-site counts understate
>   `download_timeout` (which is read at `extractor.py:201` and `:244`,
>   `segment_downloader.py:496` and `:833`, `downloader_throttle.py:19`,
>   `ytdlp_downloader.py:275`, not three sites). The table's *conclusion* is unaffected:
>   `download_timeout` still reaches none of T4, T5 or T6.
> - **Why the severity moves.** What survives is a request-fidelity asymmetry and an
>   undeclared browser TLS posture, both of them improvements to a defensible
>   arrangement, with no observed security, data-loss or correctness consequence. That is
>   the report format's own definition of `advisory` and the condition for a low severity.
> - **See also:** `NET-006` / `NET-007` (the same derived-vs-literal property on one
>   specific setting); `NET-014` (the concurrency product, which retains the
>   documentation claim this finding loses); `VAL-004` (the role file that omits
>   `RUNTIME-ERROR`, the label 8 of this report's 18 findings actually use).

| Field | Value |
|-------|-------|
| **ID** | NET-013 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | advisory |

**Description (re-derived):** the two surfaces of the same third-party downloader present
different identities to the origin — the in-process extraction surface sends the library's
own default user agent and no referer, the child-process download surface sends the
configured agent and referer — and two of the four sites that can disable certificate
verification do so without warning in their own module.

**Evidence (this run):** the six-transport inventory, the T2 option object read in full,
the T3 argv flags, the four flag sites against the two warning sites, and the
`new_context` call with no `ignore_https_errors` — all read and quoted above.

**Recommendation (narrowed to what survives):** put the configured user agent and referer
into the in-process option object so both surfaces present the same identity, and add a
warning beside the two un-warned `ssl_verify` flag sites. Pass `ignore_https_errors`
explicitly to the browser context so its TLS posture is declared rather than inherited.
**Not recommended:** the `throttled_rate` documentation change (already declared) and the
`max_concurrent_downloads` documentation change (already declared, and retained as
`NET-014`).

---

### NET-014: The effective simultaneous request rate against one origin is the square of the per-item bound, and nothing else caps it

> **Validation Note:**
> - **Action:** validated
> - **Detail:** The bound arithmetic reproduces. Read from the settings model:
>   `max_concurrent_downloads` default 4, `ge=1`, `le=16`; applied as a whole-item gate at
>   `batch_downloader.py:328` (`asyncio.Semaphore(settings.max_concurrent_downloads)`,
>   wrapped by `_TrackedSemaphore` and acquired once per video at `:191-193` and
>   `downloader.py:500-502`), as the per-item segment semaphore at
>   `segment_downloader.py:822`, and as the child's `-N` at
>   `ytdlp_downloader.py:280-281`. The same setting is therefore applied at two levels and
>   its product is 4 × 4 = 16 at the default and 16 × 16 = 256 at the ceiling. The report's
>   seam is respected: the `TCPConnector(limit=10)` literal at
>   `segment_downloader.py:537`/`:543` is named as phase `04`'s and is not double-filed
>   here; `CON-009` in turn names the request *rate* as phase `03`'s. That mutual carve-out
>   is correct and is what makes the one disagreement a conflict rather than a duplicate.
>   **Two corrections, one of which changes the consequence materially.** (1) "Nothing
>   records the product" is **wrong**: `config.py:89-98` records both levels and the
>   relationship between them in the setting's own description (quoted in `NET-013`'s
>   Validation Note). The product is not undocumented; it is unbounded. (2) "At the
>   default the same product is 16, which is already more than the connection ceiling of
>   10 — so the connector is the binding constraint the setting was meant to be" is
>   **wrong**, and this is the claim `VAL-001` files as a cross-phase conflict.
>   `_create_connector` has exactly one call site, `segment_downloader.py:795`, inside
>   `_run_download_session`, which runs once per video, and each call is paired with its
>   own `aiohttp.ClientSession(connector=connector)` at `:797`. There is **no process-wide
>   pool**: each video carries its own connector with its own `limit=10`. The aggregate
>   connection ceiling is therefore 4 × 10 = 40 at the default and 16 × 10 = 160 at the
>   declared ceiling, exactly as `CON-009` states. The correction strengthens the finding's
>   actual concern — nothing bounds the aggregate — while removing the mechanism the
>   report offered for it.
> - **Severity re-derived from this run's own evidence: MEDIUM — confirmed.** The defect
>   survives both corrections: one setting, documented for whole videos, is also the
>   per-item request fan-out, so the process's aggregate simultaneous request count is
>   quadratic in a value the operator raises to download *videos* in parallel, and the only
>   other ceiling in the chain is a per-unit literal. No incorrect result and no data loss
>   follows at the default; the ceiling is where it bites, and the ceiling is a legal
>   configuration.
> - **See also:** `NET-013` (the documentation claim this finding keeps);
>   `CON-009` in phase `04` (the literal, and the conflict filed as `VAL-001`);
>   `CON-003` in phase `04` (task materialisation — the same "no third bound" concern from
>   the work-count side; complementary, not duplicated).

| Field | Value |
|-------|-------|
| **ID** | NET-014 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** `max_concurrent_downloads` is declared for whole videos and
applied both as the whole-item gate and as the per-item segment fan-out, so the effective
simultaneous request count against one origin is the square of the setting, with no
process-wide bound above it.

**Evidence (this run):** the three application sites of the setting, the single
connector-construction site and its single session construction site, and the declared
bounds read from the model — quoted in the Validation Note.

**Recommendation (as reported, with the connector sentence kept as a seam note):** decide
which of the two levels the setting governs and stop using it for both; give the child and
the segment layer their own separately bounded settings, or gate the batch on a different
value; bound the per-video concurrent-request count with a setting rather than the
`limit=10` literal, so the aggregate is expressible and checkable. The hard-coded ceiling
itself remains phase `04`'s.

---

### NET-015: The ladder's handoffs are asymmetric, and the fallback predicate inspects one of the two names a partial can take

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived by reading both handoffs and the predicate in
>   `src/vkdownloader/services/ytdlp_downloader.py` and
>   `src/vkdownloader/services/downloader.py`. The predicate is
>   `validated_output = validate_output_path(output_file, warning=False)` followed by
>   `if not validated_output.exists() or validated_output.stat().st_size == 0: return None`
>   (`:415-417`) — one path, one name, `.part` never examined. The residue cleanup is the
>   same single name: `validated_output.unlink(missing_ok=True)` (`:444`) with its `OSError`
>   handler at `:446`. The handoff asymmetry is confirmed: `_attempt_segment_resume`
>   removes the predecessor's partial before handing the path on — `output_file.unlink()`
>   (`:531`) with the comment "Remove partial file to start clean segment download" —
>   while `perform_download`'s ffmpeg branch (`downloader.py:550-567`) goes from
>   `download_with_ffmpeg` returning `None` straight into `download_hls_with_resume` with
>   the same `output_file` and **no** unlink anywhere in the block, so the truncated and
>   partially-written file the ffmpeg stage left is still sitting at the path the merge
>   stage is about to write.
>   **The report's `UNVERIFIED` marking is confirmed and correctly held.** Which of the two
>   names the child leaves on failure is internal to the third-party tool; the code-level
>   fact this run establishes is the one the report states — the predicate and the cleanup
>   cover exactly one of the two names — and the runtime consequence is correctly left
>   unmarked. No claim in this artifact upgrades it.
>   **One correction to the consequence.** "On a later run of the same URL,
>   `ytdlp_downloader.py:416` reads that corrupt file as 'a partial exists' and skips the
>   yt-dlp path altogether" is wrong about *which* path is skipped. The predicate guards
>   the branch into `_attempt_segment_resume` (`:420-432`) inside the retry loop, so a
>   non-empty corrupt file skips the **segment-resume fallback** on that iteration;
>   `_download_with_ytdlp` itself is re-invoked unconditionally at `:368` on the next
>   iteration. Across separate runs the same holds. The finding stands on the asymmetry
>   and on the one-name predicate.
> - **Severity re-derived from this run's own evidence: MEDIUM — confirmed.** A corrupt,
>   non-zero-length file occupies the operator's chosen output path, indistinguishable from
>   a completed download; and the advertised retry-with-resume fallback is gated on a
>   detail this repository neither controls nor checks. Both are correctness defects in the
>   ladder's own contract, and the second is the feature the ladder advertises.
> - **See also:** `NET-003` (the ladder's other asymmetry); `NET-001` (a merge that fails
>   after an ffmpeg handoff lands on the same path).

| Field | Value |
|-------|-------|
| **ID** | NET-015 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |

**Description (re-derived):** two handoffs pass a failed stage's output path to the next
stage; one removes the partial first and one does not; and the predicate that decides
whether the resume fallback runs at all inspects a single filename, so it cannot see a
partial written under the other name.

**Evidence (this run):** the predicate, the cleanup, the `.unlink()` in one handoff and
its absence in the other, and the `UNVERIFIED` marking held where the report held it —
quoted in the Validation Note.

**Recommendation (as reported):** probe both `output_file` and `output_file.part` in the
predicate and clean both, so the fallback does not depend on the child's internal naming;
make the two handoffs agree, removing the failed stage's partial before handing its path
on.

---

### NET-016: The intercepted-address normaliser promotes a relative path to a host, carries a plaintext address forward in plaintext, and contains an unreachable branch

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived by driving `_normalize_url` over the address forms a page can
>   deliver. Every row of the report's R4(a) table reproduces: absolute `https` unchanged;
>   absolute `http` unchanged; scheme-relative `//cdn.example/a/stream.m3u8` →
>   `https://cdn.example/a/stream.m3u8`; root-relative `/a/stream.m3u8` →
>   `https://a/stream.m3u8`; bare host `cdn.example/a/stream.m3u8` →
>   `https://cdn.example/a/stream.m3u8`; bare relative path `a/stream.m3u8` →
>   `https://a/stream.m3u8`; bare filename `stream.m3u8` → `https://stream.m3u8`;
>   whitespace-padded absolute stripped. The JSON-payload row reproduces too: a value of
>   `720/stream.m3u8` normalises to `https://720/stream.m3u8`, i.e. a host named `720`,
>   which `_extract_urls_from_json` (`:132-133`) then appends as a discovered address.
>   The unreachable branch is confirmed by the control flow, not by counting: `:47` is
>   `if url.startswith("/")`, and a string starting with `//` necessarily starts with `/`,
>   so `:49-50` (`if url.startswith("//")`) can never be reached — the scheme-relative
>   case is already handled by the ternary's else-arm at `:48`.
>   **One correction, which narrows the practical consequence.** The bare-promotion branch
>   is only reachable from the JSON path, not from the response path:
>   `_intercept_response` normalises `response.url` (`:63`), which Playwright always
>   supplies as an absolute address. The consequence is therefore confined to a JSON
>   payload whose `hls` value is a relative path — a real shape, but a narrower one than
>   "any address the page produces". The plaintext-carry-forward branch is reachable from
>   both paths and is a property of the `http://` guard at `:44-45` regardless.
> - **Severity re-derived from this run's own evidence: LOW — confirmed.** A normaliser
>   that can invent a host, and a dead branch inside it, are correctness and hygiene
>   defects at a level this report's LOW band is for. The plaintext-carry-forward has a
>   security flavour, but it requires the page to serve an `http://` media address, which
>   is not the shape a modern VK page uses, and the finding is filed as `RUNTIME-ERROR`
>   rather than as a security boundary — which is the correct label for what is observable
>   here.
> - **See also:** `NET-008` (the selection that consumes these addresses — a host filter
>   there would drop the invented `720` host anyway, so the two fixes do not conflict);
>   `NET-011` (the other `network_monitor.py` finding; different cause, not merged).

| Field | Value |
|-------|-------|
| **ID** | NET-016 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | mandatory |

**Description (re-derived):** `_normalize_url` is a fall-through chain that promotes a
bare relative path to a host, returns an `http://` address in plaintext, and carries a
branch no input can reach.

**Evidence (this run):** the nine address forms driven through the helper, the JSON-payload
row, and the control-flow argument for the unreachable branch — all quoted in the
Validation Note.

**Recommendation (as reported):** promote only forms that actually name a host; resolve a
root-relative address against the page's own origin rather than treating its first segment
as a hostname; drop candidates that do not resolve to an absolute `https://` address;
delete the unreachable branch at `:49-50`.

---

### NET-017: Format classification matches one literal anywhere in the address, a record with no codec key is treated as video, and the ranker cannot tell a placeholder height from an absent one

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived by driving a fixed eight-record table through `_build_streams`
>   and then the ranker. The audio filter is `if f.get("vcodec") == "none": continue`
>   (`extractor.py:51`) — it excludes the literal and nothing else, so a record that
>   **omits** the key is not audio by that test and survives, confirmed. The classifier is
>   `StreamFormat.HLS if ".m3u8" in format_url else StreamFormat.MP4` (`:62`) — a
>   substring test over the whole reference — and both misclassifications reproduce: a
>   progressive address whose **query** carries the literal
>   (`https://c/v.mp4?src=https://x/a.m3u8&t=1`) is classified `hls`, and a progressive
>   address in a **directory** named with the literal (`https://c/v.m3u8/720/v.mp4`) is
>   likewise classified `hls`. The label is `quality=f"{height}p" if height else
>   "unknown"` (`:63`), so `height=0` produces `"unknown"` — covering `0` as well as
>   `None`. The ranker claim is confirmed and is the sharpest part of the finding: with a
>   two-element set `{height=0, height=None}`, `QualitySelector.select` returns the
>   `height=0` record for **both** `BEST` and `WORST` — the placeholder outranks the
>   absent value in the same way in each direction, because `max(streams, key=lambda s:
>   (s.height is not None, …))` (`quality.py:52`) and
>   `min(streams, key=lambda s: (s.height is None, …))` (`:80`) are inverses of each other
>   and both rank `(True, 0)` above `(False, 0)`. "The ranker cannot tell a placeholder
>   height from an absent one" is exactly right.
> - **One correction, which narrows one consequence.** "An audio-only record that omits
>   `vcodec` is offered and selectable as a video stream" — the record is offered and
>   selectable, yes, but whether it *is* audio is not knowable from the absence of the
>   key. The precise statement is the one the finding's own table shows: the filter cannot
>   distinguish "no codec key" from "video", so any record that omits the key is offered as
>   a video stream. The defect is in the filter's expressiveness, not in a mislabelled
>   record.
> - **Severity re-derived from this run's own evidence: LOW — confirmed.** A misrouted
>   progressive stream and a ranker that cannot choose between two uninformative records
>   are correctness defects with a bounded blast radius: the first produces a failed
>   transfer of one quality, the second a deterministic but arbitrary choice among records
>   that carry no resolution information. Neither loses data and neither breaches a
>   boundary.
> - **See also:** `NET-008` and `NET-005` (both consume the `Stream` record this finding
>   mis-labels); `NET-003` (the ranker's `WORST` branch is the one inverted by the child
>   format selector — different defect, same record).

| Field | Value |
|-------|-------|
| **ID** | NET-017 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/quality.py` |
| **Classification** | mandatory |

**Description (re-derived):** three enumeration predicates read format metadata by
inspection rather than by structure — a codec key tested for one literal, a format
classified by a substring anywhere in the reference, and a height treated as present when
it is zero — and the ranker cannot distinguish a placeholder height from an absent one, so
`best` and `worst` select the same record from a set that carries no resolution
information.

**Evidence (this run):** the eight-record survival/classification/label table, the two
misclassification cases, and the ranker's two answers on the `{0, None}` set — quoted in
the Validation Note.

**Recommendation (as reported):** classify on the parsed path's suffix rather than a
substring over the whole reference, and exclude a record that is neither video-bearing nor
explicitly audio-only; treat `height <= 0` as absent in the label and in the ranker key.

---

### NET-018: `_parse_retry_after` rejects three of the five date forms the specification permits, accepts a negative delay, and the ceiling is applied before the server's value

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived by driving `_parse_retry_after` over the header forms the
>   specification permits. Every row of the report's R2a table reproduces exactly: integer
>   `120` → 120.0; non-integer `2.5` → 2.5; exponent `1e1` → 10.0; IMF-fixdate → ~59.6;
>   **`+0000` offset → None**; **obsolete RFC 850 → None**; **obsolete `asctime()` → None**;
>   lower-case IMF-fixdate → **260,548,251.6 s ≈ 8.26 years**; a past date → None (correct
>   per specification, and the code does it deliberately with `if delta > 0`);
>   `-5` → **-5.0**; `soon` → None; `"  30  "` → 30.0; absent → None. The lower-case row is
>   worth naming precisely: `datetime.strptime` matches `%a`/`%b`/`%p` case-insensitively,
>   so the code *does* accept a lower-case IMF-fixdate — and then computes 8.26 years from
>   it, which is the finding. The ceiling ordering reproduces: with `Retry-After: 600` the
>   computed delay is `[600.0, 600.0, 600.0, 600.0, 600.0, 600.0]` at attempts 0–5, while
>   the local term alone is capped — the maximum over attempts 0–40 with no header is
>   29.63, i.e. the `min(delay, 30.0)` at `downloader_throttle.py:332` binds locally from
>   attempt 5 upward, and the `max(delay, retry_after_seconds)` at `:336` is applied
>   **outside** it and is never clamped. That is the ordering defect, confirmed.
> - **The correctly-designed part is left alone.** "A past date is silently ignored
>   (correct per specification)" — confirmed, and not a defect; the code states the rule
>   with `if delta > 0` and it is right.
> - **Severity re-derived from this run's own evidence: LOW — confirmed.** The extreme
>   consequence (8.26 years) needs an origin that sends a lower-case date a decade out.
>   The realistic consequence is a legitimate `Retry-After: 600` putting the process to
>   sleep for ten minutes on a request whose own budget is 30–300 s, with the shutdown
>   event as the only escape. That is a real availability cost and a real spec deviation,
>   but bounded, operator-interruptible, and requiring a misbehaving or unusual origin.
> - **See also:** `NET-010` (the retry loops that call this helper — a defect here changes
>   what those loops wait); the report's own boundary note naming phase `09` for the
>   comment/`max()` wording mismatch at `downloader_throttle.py:334`, which this run
>   confirms exists and does not re-file.

| Field | Value |
|-------|-------|
| **ID** | NET-018 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory |

**Description (re-derived):** the server-supplied delay parser accepts one date form of
the three the specification permits, plus a bare float that may be negative; and the local
ceiling is applied to the local term only, so the server's value — however large — is
never clamped.

**Evidence (this run):** the thirteen-row header-form table, the compute-then-clamp path at
attempt indices 0–5 with `Retry-After: 600`, and the maximum of the local term alone over
attempts 0–40 — quoted in the Validation Note.

**Recommendation (as reported):** parse all three HTTP-date forms and reject a
non-positive parsed value; clamp *after* taking the maximum with the server's value, so
the ceiling bounds the wait the process actually performs; and decide explicitly whether
the ceiling is per-request or per-video.

---

## Validation Findings

> Defects in the audit inputs themselves — a conflict, a merge, an ordering constraint, a
> pipeline-document defect. No `VAL-` finding is a product defect; every product defect
> belongs to the phase that owns its subject and is recorded above as a decision.

### VAL-001: Two phases state incompatible facts about the same connection ceiling

| Field | Value |
|-------|-------|
| **ID** | VAL-001 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.ai/audit/03-network-resilience/findings.md`, `.ai/audit/04-concurrency-cancellation/findings.md` |
| **Classification** | mandatory |

**Description:** `NET-014` (phase 03) asserts that at the declared default the connector
"is the binding constraint the setting was meant to be" because the concurrency product
(4 × 4 = 16) exceeds `TCPConnector(limit=10)` — a process-wide ceiling of 10.
`CON-009` (phase 04) asserts, for the same default and the same literal, "4 units × 10 =
40 concurrent TCP connections". Both cannot hold. The evidence supports `CON-009`:
`_create_connector` has exactly one call site (`segment_downloader.py:795`), inside
`_run_download_session`, which runs once per video, and each call is paired with its own
`aiohttp.ClientSession(connector=connector)` at `:797`. There is no process-wide pool, so
the aggregate ceiling is per-unit and the phase 03 figure is wrong.

**Evidence:** the two findings' text, quoted above in `NET-014`'s and Checkpoint 2's
records; the single connector-construction site and the single session-construction site,
counted in `src/`.

**Consequence:** a fixer acting on `NET-014` as written would bound the per-video request
fan-out "with a setting rather than the `limit=10` literal" on the belief that the literal
already bounds the process — and would leave 16 independent 10-connection pools in flight.
The number that appears in the fix's rationale would be the wrong one.

**Recommendation:** correct `NET-014`'s consequence to state that the literal is
**per download**, that the aggregate is 10 × `max_concurrent_downloads`, and that the
process-wide bound does not exist. Cross-reference `CON-009` as the owner of the literal
and retain the seam both findings already declare.

---

### VAL-002: Four accepted findings prescribe edits inside one 40-line function, two of them on the same two lines

| Field | Value |
|-------|-------|
| **ID** | VAL-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `_fetch_playlist_with_retry` (`segment_downloader.py:484-523`) is the
target of four accepted recommendations, from four different directions and on overlapping
lines:

| Finding | Prescribed change | Lines |
|---|---|---|
| `NET-004` | change the **return type** to carry the address the manifest came from | `:509`, plus the caller at `:798-806` |
| `NET-002` | rewrite the status branch, add a coordinator, add a delay | `:502-523`, incl. `:504-505` and `:512-513` |
| `NET-009` | add a `backoff_coordinator` parameter to the signature | `:484-492` |
| `NET-010` | route the transport-level failure through the response policy | `:504-505` |

**Evidence:** the four findings' recommendation blocks, quoted in this artifact; the
function's line range read from the source.

**Consequence:** there is no order in which these four can be applied independently that
does not put at least one edit on a line another has already moved. `NET-002` and `NET-010`
name the same `continue` at `:504-505`; `NET-004` changes the shape of the `return` that
`NET-002`'s rewritten status branch produces. Applying `NET-004` first invalidates
`NET-002`'s stated insertion point; applying `NET-002` first invalidates `NET-004`'s
description of what the function returns. A fixer following the findings in ID order will
produce a merge conflict, and the resolution chosen under time pressure will be arbitrary.

**Recommendation:** land the four as **one** change to
`_fetch_playlist_with_retry` — signature, return value, status branch, transport-failure
branch and the two call sites together — rather than as four. If they must be separated,
`NET-004` goes first (it owns the signature and the return contract); the other three then
share a rewritten loop body and are not separable from one another either.

---

### VAL-003: The validation stage's write path and its check path name different files, so every run fails its own gate for an artifact that is on disk

| Field | Value |
|-------|-------|
| **ID** | VAL-003 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/audit-multi-phase.md` |
| **Classification** | mandatory |

**Description:** step 2.4 writes the validator's artifact to
`.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md`
(`audit-multi-phase.md:94`). Step 2.5 checks
`.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated.md`
(`audit-multi-phase.md:105`) — a different filename. The two artifacts already on disk,
`01-entry-architecture-validated-findings.md` and `02-config-validated-findings.md`, match
the **write** path.

**Evidence:** both lines quoted above in the pipeline-document map; the two files present
in `.ai/audit/99-validation/`.

**Consequence:** the check can never pass. Every phase that reaches step 2.5 takes the
retry once, fails again, and escalates to the user with a structured failure report naming
a missing output that is present under a different name. The pipeline therefore cannot
complete a phase normally, and the escalation is indistinguishable from a genuine
validator failure.

**Recommendation:** correct the **check** at `audit-multi-phase.md:105` to
`…-validated-findings.md`. The write path is the form the pipeline has always produced and
is correct; the check is the defective side. (This artifact was written to the
`-validated-findings.md` form, as the orchestrator's write instruction names it.)

---

### VAL-004: The role that executes this phase cannot legally write the label 8 of this report's 18 findings use, and the report format names an executor the pipeline cannot launch

| Field | Value |
|-------|-------|
| **ID** | VAL-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/agents/validator.md`, `.ai/audit/templates/audit-findings.md` |
| **Classification** | mandatory |

**Description:** two documents of the pipeline disagree about what may be written and by
whom.

1. The report format defines four type labels — `SPEC-DEVIATION | BEST-PRACTICE |
   DOC-UPDATE | RUNTIME-ERROR` (`.ai/audit/templates/audit-findings.md:68`). The role file
   for the agent that executes this phase lists **three** of them, in both places it
   enumerates them (`.kilo/agents/validator.md:243-245` and `:356-358`), omitting
   `RUNTIME-ERROR`. Eight of this report's eighteen findings carry `RUNTIME-ERROR` — the
   report's own tally is 8 `RUNTIME-ERROR`, 9 `SPEC-DEVIATION`, 1 `BEST-PRACTICE` — and the
   format's own guide says that label is for "anything observed failing", which is the
   majority of what this phase audits and includes its only irreversible-loss finding. The
   agent is instructed to reject a label its own file does not list.
2. The format's frontmatter and header both name the executor `audit-executor`
   (`:4`, `:10`). The role roster is `analyst, auditor, docs-specialist, implementor,
   planner, researcher, tech-lead, test-engineer, validator` — there is no
   `audit-executor`. The launch site names `auditor` (`audit-multi-phase.md:75`).

**Evidence:** the two label lists and the two executor names, quoted above; the role
directory listing.

**Consequence:** a legal report is illegal to the agent that writes it, and the format
that carries the vocabulary names a role the pipeline cannot launch. A validator reading
its own role file would reclassify or drop every `RUNTIME-ERROR` finding — including
`NET-001`, the only irreversible-loss finding in the catalogue. The template's declared
executor is unverifiable from the roster.

**Recommendation:** the format is the authority for the vocabularies; the role file is the
defective side. Add `RUNTIME-ERROR` to both lists in `.kilo/agents/validator.md` and
reconcile the format's `audit-executor` with the launched `auditor` — either the frontmatter
or the launch site is wrong, and the format is the one this phase treats as authoritative.

---

### VAL-005: The command reads a project-instructions file as mandatory base context that the repository does not contain, and reports nothing about the miss

| Field | Value |
|-------|-------|
| **ID** | VAL-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/audit-multi-phase.md` |
| **Classification** | mandatory |

**Description:** step 1, "Gather Base Layer Context", instructs the orchestrator to "Read
`AGENTS.md` for project guidelines" (`audit-multi-phase.md:43`) and folds the result into
`{BASE_CONTEXT}`, which is passed verbatim to every executor and every validator. A
recursive search of the repository — root, source tree, docs, and the worktree — returns
**no** `AGENTS.md` at any path. The command has no branch for a missing file: it proceeds
with `{BASE_CONTEXT}` assembled from the other two sources and says nothing.

**Evidence:** the instruction at `audit-multi-phase.md:43`; the recursive filename search
returning zero paths, re-run during this validation.

**Consequence:** the project's own rules — English-only, production code is king, strict
separation of concerns, single responsibility, StrEnum for all constants, Pydantic, no
`print()`, small focused modules, and the Clean Architecture layering in
`.ai/context/python-code-standards.md` — are absent from the context every auditor and
validator receives, silently. Those rules are the basis on which a finding is typed
`SPEC-DEVIATION` against a declared rule, and this phase found three such findings
(`NET-007`, `NET-009`, `NET-014`) whose severity turns on exactly that. The rules actually
live in `.kilo/rules/project.md`, `.kilo/rules/commands.md` and
`.ai/context/python-code-standards.md`; the command reads the verification commands from
`.ai/context/commands.md` correctly and only the project-instructions file is wrong.

**Recommendation:** read the rules that exist — `.kilo/rules/project.md` and
`.ai/context/python-code-standards.md` — and make the step fail loudly, or state the
substitution, when a named context file is absent. A silent half-context is the failure
mode; the path being wrong is the smaller half.

---

### VAL-006: The report format has no slot for a per-finding decision, which every validation artifact must carry

| Field | Value |
|-------|-------|
| **ID** | VAL-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.ai/audit/templates/audit-findings.md` |
| **Classification** | mandatory |

**Description:** the format's finding block runs from the `### {ID}:` heading straight into
a fixed field table (nine mandatory fields, `audit-findings.md:22-27` and `:62-74`), then
into Description, Evidence and Recommendation. **No field carries a validation decision** —
not `id`, `title`, `type`, `severity`, `description`, `evidence`, `affected_modules`,
`recommendation` or `classification`. There is nowhere to record which of the four
decisions a validation run took, nor a rationale, nor a cross-reference.

**Evidence:** the finding block and the mandatory-field table, read in full; the two
existing validation artifacts, both of which state the same deviation in their own headers
(this artifact's header, and `02-config-validated-findings.md:8-14`).

**Consequence:** the decision record — the entire reason a validation store exists, and
the evidence that stops the next run re-deriving a rejected claim — has no home in the
format. Every validation artifact must therefore deviate, and each one states the
deviation independently. A reader who takes the format as authoritative will look for a
decision in the field table and not find one, and may conclude the artifact validated
everything.

**Recommendation:** add a tenth field to the format's mandatory list — `decision`, with
values `validated | reclassified | merged | rejected` — and place it between the heading
and the field table, where the `Validation Note` block currently sits. Until the format
carries it, the deviation stays and the two prior artifacts and this one remain
self-describing.

---

### VAL-007: The orchestrator instructs that rejected findings be cleaned from the artifact; this phase's own contract forbids deleting them

| Field | Value |
|-------|-------|
| **ID** | VAL-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/audit-multi-phase.md`, `.kilo/commands/audit/phases/99-audit-validate.md` |
| **Classification** | mandatory |

**Description:** two pipeline documents give opposite instructions about the same content.
`audit-multi-phase.md:133` states, under its retry rules, "Rejected findings cleaned from
file before merge". `99-audit-validate.md` states the opposite three times — §6 subject 3
("an instruction that strips rejected content from the artifact before it is merged
destroys the evidence the next run needs"), §11 ("**Never delete it** — the claim and the
reason are what stop the next run re-deriving it") and the "retained Rejected and Merged
rows" paragraph. The role file agrees with the preserving side:
`.kilo/agents/validator.md:362` describes rejected findings as "Rejected findings with
evidence-based rationale", not as content to remove.

**Evidence:** the two statements, quoted above with their lines; the role file's section.

**Consequence, and the side this phase took:** the **preserving side governs** this
artifact's output, per §6 subject 3. Every rejected claim and its reason would be retained
in full. As it happens this run rejected no finding outright, so nothing is at risk in this
artifact — but the contradiction is live for any run that does reject one, and a later run
following the orchestrator's rule would delete the record that would otherwise have decided
the same claim a second time.

**Recommendation:** delete the line at `audit-multi-phase.md:133`, or restate it as
"rejected findings are retained with their rejection reason, per the validation phase's
`Validation Note` contract". Where the two documents disagree, the retaining instruction
is correct: a decision record that a downstream merge may delete is not a record.

---

## Baselines — re-run during this validation

The state the decisions above were composed against. Re-run here because a validation that
adopts a baseline it has not checked cannot tell a stale finding from a live one.

```
$ uv run pytest -q -rs
486 passed, 4 skipped in 24.28s                              EXIT=0
$ uv run ruff check src tests
All checks passed!                                           EXIT=0
$ uv run ruff format --check src tests
52 files already formatted                                   EXIT=0
$ uv run mypy src
Success: no issues found in 30 source files                  EXIT=0
```

All four match the source report's R10 table. The static-tools-clean claim therefore holds
against the current tree, and every finding above is a behavioural or specification gap
rather than a type, lint or formatting violation.

**One citation in the source report's R10 section does not hold, and is corrected here.**
The report attributes all four skips to a single site, `tests/test_cookie_permissions.py:57`.
**That file does not exist in the repository.** The four skips are at
`tests/test_config.py:337`, `tests/test_config.py:353`,
`tests/test_hls_downloader.py:533` and `tests/test_hls_downloader.py:678` — three files,
four sites, all carrying the same D-11 Windows owner-only-confinement message. The
report's substantive conclusion ("all 4 skips are one platform gate, not four independent
subjects") is **correct**; only its citation is stale, and no finding depends on it.

**R10b's coverage declaration re-tested and confirmed.** A search of `tests/` (22 Python
files, worktree directories excluded) returns **0** matches for `aiohttp` and **0** for
`ClientTimeout | TCPConnector | ssl. | CERT_NONE | check_hostname`. The report's central
coverage claim — that the 486 passes include no assertion on the aiohttp layers, the merge
stage, the ladder handoff, the timeout composition or the per-surface option sets — is
confirmed. Every finding in this artifact that touches those paths was established by
re-derivation, not by the suite, and no fix to any of them would be caught by it. The
report's suggestion that a test for the merge stage's segment-deletion ordering is the first
cheap step is accepted: it is the only CRITICAL in the catalogue and the suite cannot see
it.

**Documented skips carried forward unchanged.** The report's six skips (SKIP-01 … SKIP-06)
were not re-derived here, because each names a boundary this run also cannot cross — child
process enforcement of a transport or verification policy it was handed, the child's
internal failure residue name, cookie lifetime and retention, the connection ceiling owned
by phase `04`, and the absence of a real network, a real origin and a real browser. One
consequence is restated because it is load-bearing: **no finding in this artifact asserts
what a real VK origin does.** Every claim about a live server's behaviour is marked
structural or left unasserted, exactly as the report marked it.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 15 | NET-001, NET-002, NET-003, NET-004, NET-005, NET-008, NET-009, NET-010, NET-012, NET-014, NET-015, NET-016, NET-017, NET-018 — plus NET-006, NET-007 and NET-011, validated with severity corrected (see the table below) |
| Reclassified | 1 | NET-013 |
| Merged | 0 | — |
| Rejected | 0 | — |
| VAL- (cross-phase / rollout) | 7 | VAL-001 … VAL-007 |

**Tally reconciliation.** 15 + 1 + 0 + 0 = **18**, which equals the number of findings in
the source report and the number of `Validation Note` blocks above. Every decided finding
carries exactly one decision record; none carries a severity change made by its decision.
The seven `VAL-` severities were composed in this artifact, from the evidence quoted in
each, and inherit nothing from the source report.

**Severity re-derived in this run.** Four corrections, all downward, none made by a
decision:

| ID | Was | Now | Why |
|----|-----|-----|-----|
| NET-006 | HIGH | MEDIUM | its stated consequence was a silent truncation that does not occur — `sock_read` is an inactivity ceiling, not a duration ceiling |
| NET-007 | HIGH | MEDIUM | half the finding is a documented design decision; what remains is a mis-scoped ceiling coupled to `NET-001` |
| NET-011 | MEDIUM | LOW | the comment it says is wrong is accurate, and the fix it recommends would break discovery for chunked responses |
| NET-013 | MEDIUM | LOW | two of its four sub-claims are already-correct-by-design; what survives is advisory with no observed consequence |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | **0 rejected.** No finding in the source report met a stated rejection ground: none was stale, none duplicated another, none was already implemented, none was architecture-breaking or overly complex, and none was against the project's direction. All 18 survive at least as decisions. |

**Sub-claims rejected inside surviving findings — retained, because these are the reasons
a later run must not re-derive them.** A rejected *sub-claim* is not a rejected finding and
has no ID, so it appears here rather than in the table above.

| Finding | Sub-claim rejected | Reason it is already correct by design |
|---------|-------------------|------------------------------------------|
| `NET-007` | "The two stages that actually transfer bytes impose **no** budget at all" — and the recommendation to add `asyncio.wait_for` around their `process.wait()` | `ytdlp_downloader.py:580-582` states the decision: the child carries its own `--socket-timeout`, `-R`, `--fragment-retries` and `-N`, and "no application-level download timeout is imposed, avoiding premature kill of legitimate long downloads". Adding a whole-operation budget re-introduces exactly that premature kill. The finding survives on its first half; this half re-litigates a stated design choice and must not be re-derived. |
| `NET-013` | "`throttled_rate` … governs the two surfaces that are not the ones carrying most of the traffic" | `config.py:99-104` scopes the setting to yt-dlp in its own description: "If **yt-dlp's** download rate falls below this threshold, yt-dlp aborts the download". The two surfaces that reach it are exactly the two yt-dlp surfaces. The recommendation "say so in the setting's description" asks for something the description already says. |
| `NET-013` | "Nothing records the product" (of the concurrency bounds) | `config.py:89-98` records both levels in the setting's own description: the batch semaphore "gates one permit per video (acquired once per video); each video's segment fan-out is bounded separately by a semaphore of the same size owned by the segment layer". The product is unbounded, not undocumented. The unbounded-ness is retained under `NET-014`. |
| `NET-011` | "The comment at `:87-88` states the opposite" | The comment reads "Enforce a byte cap even when Content-Length is absent", and a byte cap *is* enforced there. What is not enforced is a memory bound. The comment is accurate about its own claim; the finding's framing was not, and the corrective is a comment edit, not a behavioural change. |

**Recommendations withdrawn as unsafe to apply as written** — retained for the same reason.
`NET-007`: add `wait_for` around the two transfer stages (above).
`NET-011`: skip the JSON branch when `Content-Length` is absent or unparseable — this would
disable m3u8 discovery for every chunked or streamed JSON response, a functional
regression traded for a memory bound that the Playwright `Response` API cannot express
anyway. `NET-013`: change the `throttled_rate` description (already declared).

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| — | — | **0 merged.** No two findings share a root cause once named, so no ID absorbs another and no content moved. |

**The closest candidate, tested and not merged — retained so a later run does not merge it
on the strength of the overlap alone.** `NET-002` (the manifest layer has no retry policy)
and `NET-010` (a transport-level failure is retried with zero delay) overlap on exactly one
bullet: the manifest layer's `continue` at `segment_downloader.py:504-505` with no delay,
which `NET-002` names in its own recommendation. They are **not** merged, because
`NET-010`'s other two bullets are the two media-part strategies, which `NET-002` does not
touch — a merge would have to delete content belonging to no other finding. Both are
retained, `NET-002` absorbs the overlapping bullet by scope, and both Validation Notes say
so. The same test was applied to `NET-004`/`NET-005` (two halves of one refresh path, both
retained), `NET-011`/`NET-016` (one file, two causes, both retained), `NET-006`/`NET-007`
(three copies of one setting, different defects, both retained) and `NET-013`/`NET-014`
(a reach table and a product, overlapping framing, both retained).

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| NET-013 | BEST-PRACTICE | BEST-PRACTICE *(unchanged)*; `Classification` `recommended` → `advisory`; `Severity` MEDIUM → LOW | The **type** needed no change and none was made — a reclassification is not a severity change, and the two are recorded separately here for that reason. What changed is the *classification* field: the report format defines `mandatory \| advisory` (`audit-findings.md:27`, `:74`) and `recommended` is not a member — the only finding of 18 that leaves the enumeration. Corrected to `advisory`, the value the surviving content warrants. The severity follows from that correction, independently: what survives is a request-fidelity asymmetry and an undeclared browser TLS posture, with no observed security, data-loss or correctness consequence. |

**Label legality of every other finding, checked.** All 18 `Type` labels are members of the
format's enumeration. Seventeen `Classification` labels are `mandatory`, one is the
corrected `advisory`, and no other finding uses a value the format does not define. All
four `Severity` labels are members. No finding is typed `DOC-UPDATE`, so that section of
the format has no rows here and none is manufactured.

**No finding calls a component dead**, so the dead-code reconciliation block had no subject
to run on; none is filed, and none was reclassified as missing integration.

**Pre-answered sections:** the source report correctly omits the format's `## Summary`,
`## Mandatory Fixes`, `## Advisory Recommendations` and `## Doc Updates Needed` sections and
its `## Template Field Reference`. This artifact omits them too. The format supplies them
pre-answered with zero counts and placeholder text, and a section every phase must delete
is a defect of the format rather than of any one report.

---

## Fix Order

Derived from the decisions above, not inherited. Only the constraints that are real are
stated; a fixer following this order cannot create a conflict.

1. **`NET-001` alone, first.** It is the only irreversible loss in the catalogue, and
   `NET-007`'s mis-scoped merge budget can *trigger* it — an operator who lowers
   `download_timeout` shortens every merge stage. Nothing else in the report destroys data.
2. **`VAL-003` before the next audit run.** The pipeline cannot complete a phase until the
   check path names the file the write path produces.
3. **The `_fetch_playlist_with_retry` group as one change** — `NET-004`, then `NET-002`,
   `NET-009` and `NET-010` together. See `VAL-002`; these four cannot be separated.
4. **`NET-003` with `NET-015`** — the ladder's two handoff defects, one module boundary, no
   shared lines, but one coherent change to "what the next stage is handed".
5. **The refresh-path selection pair** — `NET-005` with `NET-008`, since both decide which
   captured address is used, and `NET-016` alongside them: a host filter in `NET-008` would
   otherwise have to special-case the host `NET-016`'s normaliser invents.
6. **The rest, in any order** — `NET-006`, `NET-007`, `NET-011`, `NET-012`, `NET-013`,
   `NET-014`, `NET-017`, `NET-018`. No two of them share an insertion point.

**The one thing not to do:** do not add a whole-operation budget to the two transfer
stages. It is the most repeated recommendation in the report's consequence text and it
would re-introduce the premature kill that `ytdlp_downloader.py:580-582` was written to
prevent.

---

*End of validation artifact. The source report `.ai/audit/03-network-resilience/findings.md`
was read only and is unmodified. No product code was changed by this phase.*
