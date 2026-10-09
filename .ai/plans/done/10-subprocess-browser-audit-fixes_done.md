# Plan 10 — Phase 05 Audit Fixes: Subprocess and Browser

**Source artifact (read-only, authoritative for *what* must change):**
`.ai/audit/99-validation/05-subprocess-browser-validated-findings.md` (1754 lines).
**Code context (read-only, authoritative for *where* it changes):** `tmp/code_context_phase05.md`
(1602 lines, produced by the Auditor against the live tree).
**Source report (read-only):** `.ai/audit/05-subprocess-browser/findings.md`.
**Precedent matched:** `.ai/plans/08-concurrency-cancellation-audit-fixes.md` (11 blocks),
`.ai/plans/09-concurrency-cancellation-audit-fixes-completion.md` (4 blocks).
**Tree state this plan was composed against:** branch `main`, `HEAD = 4bf9efb`
(`chore (agent) plan multiagent skip plan phase`), **working tree clean under `src/`, `tests/` and
`pyproject.toml`**. The dirty state is entirely under `.ai/` — eight tracked **deletions** in
`.ai/plans/`, one modified `.ai/problems/PROBLEM.md`, and five untracked entries
(`.ai/plans/05`-`08`, `tmp/`). `tmp/` is **not gitignored**. See §2.5.
**Coverage:** 12 product findings `TRN-001` … `TRN-012` + `BRW-001` + `BRW-003` + 2 audit-input
findings (`phase05/VAL-501`, `phase05/VAL-502`), in **15 blocks**. **One block (`B3`) was deleted as
moot** and its id is retired, not reused (§1.3 `S1a`). One further defect (**the console-encoding gap**)
is carried by `B16`; it had no finding id because no phase filed it, and `D7` adopts it here.

> **ZERO GATES REMAIN.** Every block is executable without a further decision. Seven decisions are now
> binding — `D1`–`D5` from the Product Owner, `D6`–`D7` from the Tech Lead — and they are recorded with
> the owner's verbatim words, the date, the blocks each changed and the findings each mooted in **§9**.
> Read §9 before §3.
>
> - **`D1`** — single-user desktop deployment. Command-line token exposure is **moot**; the user can
>   already see their own process list. Retires the `SEC-004` exposure argument as a *reason to prefer
>   indirection*.
> - **`D2`** — `--method ffmpeg` is **DELETED, not repaired**. *"No you can delete it for now. If it
>   will be needed we will add it in future."* Inverts `B10`.
> - **`D3`** — the stall bound is real and configurable: `download_stall_timeout`, default `300.0`,
>   bounds mirroring `download_timeout`. An **inactivity** bound, so `NET-007` stands and its docstring
>   sentence needs amendment, not reversal.
> - **`D4`** — stealth extraction is a hard requirement. **SUPERSEDED BY `D5`.**
> - **`D5`** *(NEW, binding)* — stealth is an **opt-in setting, default OFF**: `stealth_enabled: bool =
>   False`. The owner: *"я бы хотел, чтобы скачивающий сам решал нужен stealth или нет. Т.е. это должно
>   быть configurable по умолчанию отключено."* — *"I would like the downloader itself to decide whether
>   stealth is needed. That is, it should be configurable, disabled by default."* **Stealth was
>   previously always on; defaulting the flag to `False` removes stealth from every existing user's
>   default run.** `BRW-003` and `B15` are re-scoped by this.
> - **`D6`** *(Tech Lead, closes `Q4`)* — `TRN-008` / `B13`: **option (B), better degradation.** One
>   actionable warning, the probe's answer USED at its single call site, the `failed_to_refresh_token`
>   mislabelling stopped, and **no exit-code change**.
> - **`D7`** *(Tech Lead, closes `Q6`)* — the console-encoding defect is **adopted here**, option (A).
>   `B16` is ungated.

> **REVISION 2 — the Product Owner has answered.** Four decisions are now binding and have changed
> this plan's shape. They were taken on **2026-10-03** and are recorded verbatim, with the blocks they
> changed and the findings they mooted, in **§9**. Read §9 before §3.
>
> - **`D1`** — single-user desktop deployment. Command-line token exposure is **moot**; the user can
>   already see their own process list. This retires the entire `SEC-004` exposure argument as a
>   *reason to prefer indirection*.
> - **`D2`** — `--method ffmpeg` is **DELETED, not repaired**. The owner's words: *"No you can delete
>   it for now. If it will be needed we will add it in future."* This **inverts `B10`**: it is now the
>   removal of the transport, not its repair.
> - **`D3`** — the stall bound is real and configurable: a new `download_stall_timeout` setting,
>   default `300.0`, bounds mirroring `download_timeout`. It is an **inactivity** bound, so
>   `NET-007`'s documented decision **stands** and the docstring sentence does **not** need reversing.
> - **`D4`** — stealth extraction is a **hard requirement**: *"bypassing detection is required for the
>   tool to work, we need this as downloading from the system with high bot protection."* This
>   **escalates `BRW-003`** from a warning to a hard failure.
>
> Two product questions remain open and are stated as such in §9: **Q4** (`TRN-008`'s remedy shape,
> materially narrowed) and **Q6** (the console-encoding gap's ownership). **Q5** (`TRN-009`'s
> ownership) is **closed** by the decision already taken: this plan takes the **unowned merge sinks**;
> phase 06 keeps the yt-dlp terminal echo and the path-matching capability.

> **Identifier convention — binding on every block, every block report, every task id and every
> commit message of this plan.**
> `VAL-` is a **colliding prefix**. Every per-phase validation run mints `VAL-001…` independently and
> the numbers name different subjects: `VAL-001`…`VAL-006` (phase 02), `VAL-001`…`VAL-007`
> (phase 03), `VAL-101`…`VAL-112` (phase 01), `VAL-401`…`VAL-410` (phase 04). `VAL-501` in
> particular appears in phase 07's validation store as a *pipeline-document range*, not as phase
> 05's cross-phase conflict. **This plan's two audit-input findings are written
> `phase05/VAL-501` and `phase05/VAL-502` everywhere** — in a block heading, a block report, a task
> id and a commit message. An unqualified `VAL-501` is a **defect** and must be rejected at review.
> `TRN-` and `BRW-` are unique to phase 05 across the whole store and are **NOT** qualified.

> **Nothing in this plan is anchored by line number.** Every target is a semantic anchor — a file, a
> module, a class, a function, a method, a guard expression, a return statement, a parameter, a
> module-level name. The validated artifact's `file:line` references are stale for every moved file
> (measured drift: `+1`…`+2` in `services/downloader.py`, `+30` in `services/ffmpeg_utils.py`,
> `+1`…`+32` in `services/ytdlp_downloader.py`, `+1`…`+20` in `infrastructure/browser.py`) and the
> tree can move again. **Re-anchor semantically at execution time.**

> **Four decisions were asked for and four were given (`D1`–`D4`, 2026-10-03); this plan now records
> them as taken.** `TRN-001`'s transport shape is settled by **`D2`** (delete, not repair);
> `TRN-007`'s stall bound by **`D3`** (default 300.0s, configurable, an **inactivity** bound, so
> `NET-007` stands and its docstring sentence needs amendment rather than reversal); `TRN-003`'s
> boundary scope by **`D1`** plus the standing Tech Lead decision (minimum platform keyword, Windows
> residual documented); and `BRW-003`'s remedy by **`D4`** (**escalated** to a hard failure, verified
> before a browser launches). **`TRN-009`'s ownership (`Q5`) is closed** by the split already decided:
> this plan takes the two **unowned merge sinks**, phase 06 keeps the yt-dlp terminal echo and the
> path-matching capability. **Two questions remain open and are stated as such in §9:** **`Q4`**
> (`TRN-008`'s remedy shape, materially narrowed by `D2`, with a recommendation) and **`Q6`** (the
> console-encoding gap, owned by no finding). **`B13` and `B16` must not be scheduled before their
> answers.**

---

## §1 Scope

### §1.1 How this block set was derived

The block set is **not** the artifact's finding order. It is that order re-derived against five
things the artifact could not see.

1. **The tree moved by seven commits and nothing was pre-fixed.** Everything plans 05–09 landed on
   the three phase-05 modules, and the code context establishes that `download_with_ffmpeg`'s body
   is **byte-identical** to the tree the artifact was composed against. All fourteen accepted
   findings are therefore open or partially open, and **no block in this plan is "already fixed"**.
   The derivation is therefore mostly about **grouping and splitting**, not about triage.
2. **One anchor function was rewritten by an already-landed plan.** `iter_process_lines` was
   rewritten by `f6ed0cf` (plan 08's `B1`), which added a watcher task, a `fire()` exactly-once
   helper and a `finally` that awaits the watcher. `TRN-004`'s defect survives inside the rewrite, but
   its remedy has a **second** concern the artifact could not name. That is a distinct interaction,
   not a duplicate — see `C3`.
3. **`BRW-001` is `PARTIALLY FIXED` and its two halves now diverge.** Phase 01's `ENT-001`/`ENT-002`
   landed, so the artifact's premise "logging is not configured on this path" is **false**. The
   `from None` half is unconditional; the `UnicodeEncodeError` half is conditional on a strict
   stream and does not fire on the log-file sink at all. And the encoding facet is **owned by no
   finding in any phase**. That forces a split (§1.3 `S4`) and a conditional block (`B16`).
4. **Four findings had an unresolved PRODUCT decision at their core**, not a technical one. Three of
   them are now answered by `D1`–`D4` (§9): `TRN-001`'s transport shape (`D2`), `TRN-007`'s stall
   bound (`D3`) and `TRN-003`'s boundary scope (`D1` plus the standing Tech Lead decision).
   **`TRN-008`'s remedy shape (`Q4`) remains open**, and it is materially narrower now that three of
   its four arms are re-derived in §1.8.
5. **Three currently-green test groups interact with defective behaviour or with an invariant a
   remedy would break**, and several more tests named by the code context **do not exist under the
   names it gives them**. Under project rule 2 a pinned test is edited *in the same change* as the
   fix. The inventory is re-derived against the live tree in §2.6 and corrected in §1.7.

**Grouping rule applied throughout:** two findings share a block only when they share a **semantic
anchor** *and* the grouping reduces conflict, review surface, or risk. Conversely **one finding may be
split across blocks** when its halves live in different modules, carry different failure modes, have
different ordering gates, or need different verification shapes. Every split and every grouping is
justified in §1.3 and repeated at the block heading.

### §1.2 IN — every still-open item

**Every row below is stated as it stands after `D1`–`D4`.** Four rows are materially different from
Revision 1 and are marked.

| Block | Findings | One-line goal | Why here | Plan that would otherwise carry it |
|---|---|---|---|---|
| **B1** | `TRN-002` **re-scoped** | Make the yt-dlp transport's cookie-file destroy incapable of replacing the download's own outcome | **Re-scoped by `D2`.** The argfile — the finding's original subject — is deleted with the transport, and with it the orphan half. A **residue survives** at `_download_with_ytdlp`'s `finally:` (§1.3 `S1b`). Now one site, one module, one line. | — (this plan) |
| **B2** | `TRN-004` | Make one oversized child line incapable of killing the reader | `iter_process_lines` **survives `D2`** — it is the yt-dlp drain's only reader. Unchanged in substance; its regression net shrinks (§1.3 `S1c`). | — (this plan) |
| ~~**B3**~~ | ~~`TRN-005`~~ | ~~Stop reading at the muxer's end-of-stream marker~~ | **DELETED — MOOT.** `read_progress` and its `progress=end` marker are deleted with the transport, and the **merge** transport never emits `-progress` at all (`_build_ffmpeg_concat_command` passes no `-progress`). Nothing that can reach this defect survives. §1.3 `S1a`. | — (nothing; it is disposed of) |
| **B4** | `TRN-006` **sink half only** | Make a reader failure **visible** instead of swallowed | **Re-scoped by `D2`.** The parse half (`_PROGRESS_KEY_HANDLERS` and the unguarded conversions) dies with `read_progress`. The **sink** half survives and is now *more* load-bearing: `_await_first_and_cancel_others` is the observer for the **only** reader left. One module, one half. | — (this plan) |
| **B5** | `TRN-012` | Read `cancel_subprocess`'s documented return contract correctly at its **two** surviving sites | `D2` deletes the four `download_with_ffmpeg` sites; the two in `_download_with_ytdlp` survive, and the "already gone ⇒ clean" misreading survives with them. | — (this plan) |
| **B6** | `TRN-011` | Stop accumulating a child's entire transcript, including the transcript nobody asked for | **Unaffected by `D2`.** Its subject is the yt-dlp transcript, which `D2` does not touch. | — (this plan) |
| **B7** | `TRN-009` *(claim half, 2 of 3 sites)* | Stop the sanitizer's docstring and the yt-dlp `SEC-002` comment claiming a capability its regex cannot deliver | **Re-scoped by `D2`.** One of the two source comments dies with `download_with_ffmpeg`. The function's **own docstring** and the yt-dlp comment survive — the docstring is shared and the yt-dlp transport is the one that remains. | — (this plan) |
| **B8** | `BRW-001` *(half a)* | Carry the launch failure's actionable cause into the `ExtractionError` | The **unconditional** half. One `except` arm in one method. Decidable from the artifact's own correction (`from None` sets `__suppress_context__`, not `__context__`). **Unaffected by `D2`.** | — (this plan) |
| **B9** | `phase05/VAL-501` + `phase05/VAL-502` | Record that both chains are **resolved by deletion**, and that phase 06's `SEC-004` is now describing a transport that no longer exists | **Re-scoped by `D2`.** `phase05/VAL-502` chain 2 is answered; chain 1 evaporates with the argfile; `phase05/VAL-501` becomes *more* clearly stale. §1.3 `S1e`. | — (this plan) |
| **B10** | `TRN-001` + `TRN-010` **inverted** | **DELETE** the ffmpeg download transport and everything that exists only to serve it | **Inverted by `D2`.** No longer "make it work" — remove it. `TRN-010`'s asymmetry is moot with one transport left. §1.3 `S1d`. | — (this plan) |
| **B11** | `TRN-007` | Bound the stall at the transport's one surviving re-wait, as an **inactivity** bound | **Decided by `D3`.** No longer `AWAITING DECISION`. `D2` deletes one of the two re-wait sites, so the finding survives at **one** site. `NET-007` stands and is not reversed. | — (this plan) |
| **B12** | `TRN-003` | Establish a process boundary at the asyncio spawn sites: the minimum platform keyword, with the Windows residual documented | **Decided.** The standing Tech Lead decision is option (B) — `start_new_session=True` on POSIX, `CREATE_NEW_PROCESS_GROUP` on Windows — rejecting a Job Object as overengineering against rule 5. `D1` is the reason the residual is acceptable. §1.3 `S1f`. | — (this plan) |
| **B13** | — | — | **YES** | **YES** | MEDIUM | *Planner:* **retained after `D6`.** The remedy shape is fixed (option B), but three call sites change and there is a real fork: **whether the cache gains an invalidation path or is left write-once**, and where the single warning is emitted so arm (b), arm (c) and arm (d) all reconcile with it. *Validator:* arm (b) is **untested today** and is now the sharpest arm, and `D6`'s "no exit-code change" instruction is exactly the kind a well-meaning Implementor over-applies — the Validator must confirm no branch raises and no exit code moves. |
| **B14** | `TRN-009` *(capability half)* | Apply the redaction transform at the **two untransformed merge sinks** | **Shrunk by the `Q5` decision.** This plan takes the **unowned merge sinks** (`batch_merge_failed`, `final_merge_failed`); phase 06 keeps the yt-dlp echo and the path-matching capability. **No longer gated** — ownership is decided. Two lines, two tests. | phase 06 `SEC-005`/`SEC-006` — **closed, split by sink** |
| **B15** | — | — | **YES** | **YES** | HIGH | **Planner — retained, and the reason changed.** `D4`'s block had a determined remedy and no Planner; `D5` gives it back one, because the block now decides **where the flag is read at two consumption points**, **where exactly the conditional check sits**, and **what the field description must say** — four coupled statements across two modules and eleven documentation sites, which is not mechanical. *Validator:* **mandatory and the gate is the ordering proof** — a check that sits after `async_playwright().start()` satisfies every other assertion while achieving nothing. Plus `S1i`: it must confirm `B8`'s four anchors are untouched. |
| **B16** | — | — | **YES** | **YES** | LOW-MEDIUM, unowned | *Planner:* **retained.** `D7` settles adoption, but not construction — whether the encoding-safe value is set on the handler or supplied at construction is a small real fork, and the report must state why `PYTHONIOENCODING` and `sys.stderr.reconfigure` were rejected. *Validator:* the block still has **no finding behind it**, so its job is to confirm the adoption is the Tech Lead's decision and that no per-callsite `try` was written instead. `D7`'s fourth rationale is **not borne out by the code** and the Validator must not let it into the commit body as fact. |

**Reconciliation.** 12 `TRN-` + 2 `BRW-` = **14 product findings**, in **13 product blocks** after
`B3`'s deletion; `TRN-009` is carried by two blocks (`B7` + `B14`) and `TRN-001` + `TRN-010` by one
(`B10`). Adding `B9` for the 2 audit-input findings gives **14 unconditional blocks**, plus `B16` for
the unowned gap = **15 blocks**. **Zero accepted findings unassigned, and zero findings left in the
plan whose subject no longer exists.**

### §1.3 Every split and every grouping, with its reason

The `D1`–`D4` cascade re-derived the grouping. Rows `S1a`–`S1g` are **new in Revision 2** and record
what the decisions changed; the surviving rows are Revision 1's, carried forward.

| # | Decision | Reason |
|---|---|---|
| **S1a** *(new)* | **`B3` / `TRN-005` — BLOCK DELETED as moot** | `TRN-005` is the `if value == "end": break` inside `read_progress`, which abandons the child at its final progress block. **The merge transport never emits `-progress` at all** — `_build_ffmpeg_concat_command` builds `["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", <list>, "-c", "copy", <out>]` and reads it with `process.communicate()` under `_await_ffmpeg_with_timeout`. The muxer's progress stream is produced **only** by `download_with_ffmpeg`. `D2` deletes that method, so `read_progress` goes with it and **no reachable code can produce the defect**. The finding is disposed of, not deferred. Its id is **retired, not reused**: `B3` is a gap in the sequence on purpose, so that Revision 1's cross-references stay readable. |
| **S1b** *(new)* | **`TRN-002` / `B1` — RE-SCOPED from the argfile to the yt-dlp cookie file** | `TRN-002` had two halves. **(i) The destroy sits outside the child-termination guarantee, so a failed destroy orphans the child** — this half's *only* instance is `_temp_argfile`'s `finally:`, and `D2` deletes it. **Moot.** (ii) *A failed destroy replaces the download's own outcome* — this half **survives**, at `_download_with_ytdlp`'s `finally:`, which carries the identical `cookie_file.unlink(missing_ok=True)` pattern. Established by reading the surviving `finally:` in full: the child is always reaped (normal and error paths both pass `await process.wait()`) or cancelled (the `except asyncio.CancelledError` arm) **before** the cookie unlink runs, so a failure here cannot orphan a child — but it **can** turn a clean `None` into a raised `OSError`. The residue is real, is a **different statement in a different module**, and is a one-line fix. **The block survives, at one-tenth of its original scope, and no longer carries `phase05/VAL-502` chain 1.** |
| **S1c** *(new)* | **`TRN-004` / `B2` — SURVIVES, regression net shrinks** | `iter_process_lines` has exactly two surviving consumers after `D2`: `_monitor_progress` and `_drain_output` in `_download_with_ytdlp`. The oversized-line hazard is fully live on the yt-dlp child. But the six drain tests `B2` names as its regression net included three that `D2` **deletes** (`test_error_handling_ffmpeg_failure`, `test_error_handling_ffmpeg_failure_sanitizes_url_in_error`, `test_download_with_ffmpeg_with_progress_callback`, `test_perform_download_ffmpeg_progress_adapter_sends_unknown_total`). The net reduces to the **yt-dlp** drain tests (`test_ytdlp_stdout_progress_written_to_console`, `test_ytdlp_echo_false_suppresses_stderr_while_callback_fires`, `test_ytdlp_echo_false_progress_emits_debug_log`) plus the exact-once invariant on `TestIterProcessLines`. Re-listed at the block. |
| **S1d** *(new)* | **`TRN-001` + `TRN-010` / `B10` — INVERTED, not split** | `D2` removes the transport, so `B10`'s content is a **deletion**, and `TRN-010` remains grouped with it: its asymmetry is moot with one transport left, and its residue (the yt-dlp transport still passes `--cookies <path>` and the media URL in argv while `sanitize_text_for_log` cannot match a path) is **phase 06's `SEC-006`**, which `D1` makes moot for this deployment. A deletion is one review surface; splitting it across blocks would produce several commits that each leave the tree broken. **One block, one commit, one revert.** |
| **S1e** *(new)* | **`phase05/VAL-501` + `phase05/VAL-502` / `B9` — RE-SCOPED from "record an open conflict" to "record that both chains are closed"** | `phase05/VAL-502` chain 2 (the transport-shape decision) is **answered** by `D2`. Chain 1 (the `TRN-001` <-> `TRN-002` coupling) **evaporates**: the coupling existed because fixing one made the other worse, and there is nothing left to couple. `phase05/VAL-501` becomes **more** stale, not less — phase 06's `SEC-004` asserts a concealment that never existed **and** now describes a transport that no longer exists at all. The block's substance is the correction, not the conflict. `.ai/audit/**` remains read-only, so the recording lands in this plan and in commit bodies. |
| **S1f** *(new)* | **`TRN-003` / `B12` — DECIDED, scope unchanged** | The standing Tech Lead decision is option (B): the minimum platform keyword per spawn, plus honest documentation of the Windows residual. `D1` changes the **cost/benefit**, not the remedy: a surviving orphan now holds a file open on the user's own desktop rather than on a shared host, so the residual a Job Object would have closed is no longer worth its abstraction cost against rule 5. Recorded, not re-opened. |
| **S1g** *(revised by `D5`)* | **`BRW-003` / `B15` — RE-SCOPED from "always hard-fail" to "gate, then hard-fail only when explicitly enabled"** | `D4` read `BRW-003` as a silent asset and made the absence an unconditional hard failure. `D5` supersedes that: stealth becomes an **opt-in setting, default off**. The two halves of `BRW-003` now behave differently. **With stealth off, the asset is not consulted at all** — nothing reads `self._stealth_path` — so "the asset's absence is silent" has no subject and **the finding's original form dissolves**. **With stealth explicitly enabled, absence is a hard failure**, because the user asked for stealth and cannot have it; extraction will fail downstream anyway, so failing fast at the cheapest point is strictly better than a confusing late failure. `D4`'s placement analysis, exception choice and message convention all survive — only the *condition* changes from "always" to "when enabled". |
| **S1h** *(new, `D5`)* | **The stealth posture splits into a gated set and an ungated set, verified against the code** | The posture is **four** components, not one, and they do not belong together. **GATED:** `--disable-blink-features=AutomationControlled` (`__aenter__`'s launch args) and `add_init_script(path=self._stealth_path)` (`create_stealth_page`) — both are anti-detection measures whose only purpose is to defeat automated-browser fingerprinting. **NOT GATED:** the context identity triple `viewport` / `user_agent` / `locale` / `timezone_id`. Established against the code: `settings.user_agent` is consumed by **four** call sites — the browser context, the segment downloader's HTTP `User-Agent` header, yt-dlp's `--user-agent`, and the ffmpeg transport's `-headers` value (the last deleted by `B10`) — so it is **ordinary request identity**, not a stealth setting, and gating it at the `Settings` level would break the other three consumers. `viewport` is a hard-coded literal, not a setting at all. `locale` and `timezone` are consumed **only** by the browser context, so gating them would be *technically* safe — but their field descriptions say "for browser stealth configuration" and **those descriptions are corrected rather than acted on**: a Russian locale and a Moscow timezone are what a real user's browser looks like, so applying them is **correctness, not evasion**, and suppressing them would make extraction *less* likely to succeed for a user in that region for no gain. §3's `B15` carries the reasoning. |
| **S1i** *(new, `D5`)* | **`B8` and `B15` stay TWO blocks, and `B8` lands first** | Both land in `BrowserManager.__aenter__`, so merging is tempting. **Not merged, because their verification shapes differ.** `B8` is an *information* fix — it re-scopes one pinned test and adds three cases about what the raised message contains and that the Playwright banner stays suppressed; its anchors are the `except Exception:` arm and the raise statement. `B15` is a *posture* fix — it adds a `Settings` field, gates two components, adds a conditional pre-driver check, and adds an ordering proof that the driver is never reached; its anchors are the launch args, `create_stealth_page`, `__aenter__`'s entry, `Settings`, and eight documentation sites. No test of one satisfies the other. **Order: `B8` first** — it is unconditional and independent, while `B15` changes the *default* behaviour for every existing user (`D5`); landing the information fix first means a revert of the posture change leaves `B8` standing. |
| **S1** | **`TRN-002` split off from `TRN-001`** *(superseded by `S1b`)* | **Was:** different ordering gates — `TRN-002` live today, `TRN-001` gated on a decision. **Now:** moot. The split is retained only because the two subjects no longer exist; `B1` survives for a different reason (`S1b`) and `B10` for a different reason (`S1d`). |
| **S2** | **`TRN-010` grouped with `TRN-001`** | `TRN-010` has no independent fix, and `D2` makes it moot outright: the asymmetry it names is an asymmetry *between two transports*. Its residue is recorded as a cross-reference to phase 06's `SEC-006`, not as a block. |
| **S3** | **`TRN-009` split into a claim half and a capability half** | **Still correct, and now sharpened.** The claim half (`B7`) and the capability half (`B14`) have different owners, different modules and different verification. `D2` shrinks both — the claim half from three sites to two, the capability half from three sinks to **two merge sinks** — but the split still holds, because the two halves are still independently landable. |
| **S4** | **`BRW-001` split: half (a) unconditional, the encoding half conditional** | **Unchanged.** `D1`–`D4` do not touch `browser.py`'s launch-failure arm or the console sink. `B8` and `B16` both stand as written. |
| **S5** | **`TRN-004`, `TRN-005`, `TRN-006`, `TRN-007` kept as four blocks, not merged** | **Partly superseded.** `TRN-005` is moot (`S1a`). Of the remaining three: `TRN-004` and `TRN-006`'s sink half are the **same reader** and remain separate because one prevents the failure and one reports it; `TRN-007` is a different question with a now-decided answer. The four-way split is retained minus the deleted member. |
| **S6** | **`TRN-006`'s parse half and its sink half kept in one block** | **Superseded by `D2`.** The parse half dies with `read_progress`. `B4` survives with **one** half, so the two-module justification no longer applies — the block is now one module, and the argument for it is stronger: the surviving sink is the observer for the only reader left. |
| **S7** | **`TRN-005` and `TRN-007` kept in different blocks** | **Superseded.** `TRN-005` is deleted; `TRN-007` survives at one site, decided by `D3`. The reasoning about policy-vs-mechanism is no longer needed. |
| **S8** | **`phase05/VAL-501` + `phase05/VAL-502` grouped into `B9`** | **Unchanged.** Both still write the same single document. |
| **S9** | **`TRN-011` and `TRN-012` kept separate although both sit in `ytdlp_downloader.py`** | **Strengthened.** After `D2`, **both subjects live entirely in `ytdlp_downloader.py`** — `TRN-012`'s two surviving call sites and `TRN-011`'s buffer. They are still different statements with different failure modes and different verification, but the module overlap is now total, so the conflict matrix entry (`C16`) is a same-file pairing rather than a cross-module one. |

### §1.8 What `D2` mooted — finding by finding, with the code reason

**A finding quietly left in the plan after its subject is removed is a defect in the plan.** Each of the
fourteen is stated here, in code terms, as **mooted**, **disposed**, **re-scoped** or **untouched**.

| Finding | Verdict | The code reason |
|---|---|---|
| **`TRN-001`** | **DISPOSED by `D2`** | Its subject is the `@argfile` invocation and the `--method ffmpeg` transport. Both are deleted. `D2` **is** the answer to this finding; it is not left open and not carried forward. |
| **`TRN-002`** | **RE-SCOPED (half moot)** | The orphan half's only instance (`_temp_argfile`'s `finally:`) is deleted. The "failed destroy replaces the outcome" half survives at `_download_with_ytdlp`'s `finally:` — same `missing_ok=True` pattern, different module. See `S1b`. |
| **`TRN-003`** | **UNTOUCHED** | `D2` removes one of four spawn sites; the yt-dlp child — the one that can spawn descendants — is untouched. Decided by `S1f`. |
| **`TRN-004`** | **UNTOUCHED** | `iter_process_lines` survives for the two yt-dlp drain sites. Fully live. |
| **`TRN-005`** | **FULLY MOOT** | `read_progress` is deleted, and the merge transport never emits `-progress`. Nothing can reach the defect. **`B3` deleted.** See `S1a`. |
| **`TRN-006`** | **HALF MOOT** | The parse half (`_PROGRESS_KEY_HANDLERS`, `ProgressParser`, `FfmpegProgress`) is deleted. The sink half (`_await_first_and_cancel_others`) survives and is the observer for the only reader left. **`B4` survives, one module, one half.** |
| **`TRN-007`** | **UNTOUCHED, site count halved** | Two re-wait sites; `download_with_ffmpeg`'s is deleted, `_download_with_ytdlp`'s survives. Decided by `D3`. |
| **`TRN-008`** | **PARTLY MOOT** | Arm (a) — the ffmpeg download path's `except OSError` — is deleted. Arms (b) merge, (c) yt-dlp, (d) resume survive. `check_ffmpeg_available` **stays live**: the single bare call in `perform_download` still guards a download that can reach `_merge_segments_batched` -> `_merge_batch_segments`/`_perform_final_merge`, which still need the muxer. |
| **`TRN-009`** (claim) | **PARTLY MOOT** | Three sites; the `download_with_ffmpeg` `SEC-002:` comment is deleted. `sanitize_text_for_log`'s own docstring and the yt-dlp `SEC-002:` comment survive. **`B7` survives, two sites.** |
| **`TRN-009`** (capability) | **SCOPED** | Three sinks. `D2` deletes none of them (they are all in the merge and yt-dlp paths). The `Q5` decision assigns this plan the **two unowned merge sinks**; phase 06 keeps the yt-dlp echo and the path-matching capability. **`B14` survives, two lines.** |
| **`TRN-010`** | **MOOT** | It is an asymmetry **between two transports**. One transport remains, so there is no asymmetry. The residue — yt-dlp still passes `--cookies <path>` and the media URL in argv, and `sanitize_text_for_log` still cannot match a path — is **phase 06's `SEC-006`**, and `D1` makes the exposure moot for a single-user desktop. **Cross-reference recorded; no block.** |
| **`TRN-011`** | **UNTOUCHED** | Its subject is the yt-dlp transcript buffer, which `D2` does not touch. |
| **`TRN-012`** | **UNTOUCHED, site count reduced** | Six `cancel_subprocess` call sites; the four in `download_with_ffmpeg` are deleted. The two in `_download_with_ytdlp` survive with the same misreading. The "three records per stop" composition is specific to the deleted method; the surviving composition is weaker (the reader's `_on_shutdown` plus the `CancelledError` arm) but real. |
| **`BRW-001`** | **UNTOUCHED** | `infrastructure/browser.py`. No dependency on the transport. |
| **`BRW-003`** | **RE-SCOPED by `D5`** | Two halves now diverge again. *The original half* — the asset's absence is silent at every log level — **dissolves when stealth is off**, because nothing consults the asset. *The residual* — when stealth is **explicitly enabled**, absence must be a hard failure — is what `B15` carries, with `D4`'s placement analysis intact and only the condition changed. Same anchors, different remedy. §1.3 `S1h`. |

**A sixth, unplanned observation, recorded because it is not any phase-05 finding.**
`docs/99-reference/cli-reference-clean.md` is **not** a second page and **not** an exact duplicate: it is
the **same document with every non-ASCII character mojibake'd** — the em dash appears as `вЂ”`, the
cp1251 misreading of UTF-8 `E2 80 94`. It is 283 lines against the original's 284 and the hashes
differ. Exactly one file links to it (`docs/99-reference/error-handling-logging-research-2025-2026.md`).
There is no `mkdocs.yml` in this repository, so there is no navigation to reconcile. **This is a
pre-existing documentation-hygiene defect owned by no phase; it is recorded here and deliberately NOT
fixed by this plan.** `B10` still edits its `--method` rows, because leaving a page that advertises a
deleted CLI option would be worse than leaving its encoding broken.

### §1.4 OUT — and where each item went

| Item | Disposition | Where it went, and why |
|---|---|---|
| **`TRN-010`** (the *asymmetry* between two transports) | **OUT — moot by `D2`** | An asymmetry **between two transports** cannot survive the deletion of one. The residue is recorded as a cross-reference to phase 06's `SEC-006` — the yt-dlp transport still passes `--cookies <path>` and the media URL in argv, and `sanitize_text_for_log` still cannot match a path — and `D1` makes the exposure moot for a single-user desktop, where the user can already read their own process list. **No block.** |
| **`TRN-005`** (the muxer's `progress=end` break) | **OUT — moot by `D2`** | `read_progress` is deleted with the transport, and the **merge** transport never emits `-progress` at all — `_build_ffmpeg_concat_command` builds no `-progress` argument and reads the child with `process.communicate()`. Nothing reachable can produce the defect. **`B3` deleted**; its id is retired, not reused. §1.8. |
| **`TRN-006`'s parse half** (the unguarded numeric conversions) | **OUT — moot by `D2`** | `_PROGRESS_KEY_HANDLERS`, `ProgressParser` and `FfmpegProgress` are deleted with `read_progress`. Only the **sink half** survives, in `B4`. |
| **`phase05/VAL-502` chain 1** (the `TRN-001` <-> `TRN-002` coupling) | **OUT — evaporates by `D2`** | The coupling existed because fixing one member made the other worse. There is nothing left to couple. `B1` no longer carries it. |
| **`docs/99-reference/cli-reference-clean.md`'s mojibake** | **OUT — recorded, not fixed** | The file is the same document as `cli-reference.md` with every non-ASCII character mis-decoded (`вЂ”` for an em dash). It is linked from exactly one research document and there is no `mkdocs.yml`, so there is no navigation to reconcile. **No phase-05 finding owns this**, it is a documentation-hygiene defect, and this plan does not expand into it. `B10` still edits its `--method` rows, because leaving a page advertising a deleted CLI option is worse than leaving its encoding broken. §1.8. |
| **`TRN-013`** (merge batch size is a literal where configured values sit beside it) | **OUT — rejected upstream** | The validator rejected it on *low value at this scale*: `download_timeout` already bounds each batch's merge, `_check_merge_space` already accounts for the space independently of `batch_size`, and the finding's own rationale ("avoid command line limits") is stale because the path writes a concat file list and passes six arguments. **This plan does not resurrect it.** No block may add a configuration knob for `batch_size`, and no block may treat the `TRN-013` reasoning as a precedent for adding knobs elsewhere. `B6`'s buffer cap is the one place a new constant is proposed and it is justified by a **measured** consequence (108.6 MiB of growth for 50 MiB of child output), which is exactly what `TRN-013` lacked. **The merge transport this concerns survives `D2` unchanged**, so the rejection still stands on its own terms. |
| **Any change to `pyproject.toml`'s dependencies** | **OUT — none becomes unused** | Established by reading the dependency block: `playwright` (the stealth layer, now a **hard requirement** under `D4`), `aiohttp` (the segment downloader), `yt-dlp` (the surviving transport), and `pydantic`/`pydantic-settings`/`typer`/`rich`/`structlog`/`python-dotenv` all keep their consumers. The ffmpeg **download** path used no dependency the **merge** path does not. **`B10` edits no dependency.** The `artifacts = ["src/vkdownloader/stealth.min.js"]` declaration **stays** and becomes *more* load-bearing under `D4`: it is what makes a missing asset mean a broken build or a partial deployment rather than a bad install. |
| **`BRW-002`** (the context created on every acquire is bound to no release) | **OUT — rejected upstream** | The measurement reproduces but the consequence is unreachable: the only call site sits inside `async with BrowserManager(...)`, and `__aexit__` closes the browser, which closes every context it owns. **No block may add a release path for the context.** `B8` and `B15` touch `browser.py` and must leave `create_stealth_page`'s context handling exactly as it is. |
| **Any severity reclassification** | **OUT — prohibited** | All fourteen severities are retained as the artifact re-derived them, including `TRN-001`'s escalation to CRITICAL. A role file lacking a vocabulary is not grounds to reclassify an observed failure. **Binding on every block.** |
| **`TRN-001`'s raw reproduction counts** (`25/25`, `3/3`, the four controls A–D) | **OUT — not endorsed** | The validator declined to endorse the report's counts and recorded its own. No block report may cite `25/25`. The conclusion does not depend on the count. |
| **`BRW-001`'s "permanent leak" consequence** | **OUT — withdrawn upstream, in phase 04** | `__aexit__` does call `playwright.stop()` in a `finally`. **Binding on `B8`, `B15`, `B16`.** |
| **`TRN-006`'s "`N/A` is unhandled" framing** | **OUT — moot by `D2`, and corrected anyway** | Two independent reasons. Every entry of `_PROGRESS_KEY_HANDLERS` carries the `v != "N/A"` guard, so the framing was already wrong. And `D2` deletes `_PROGRESS_KEY_HANDLERS` entirely, so there is nothing left for the framing to describe. `B4` no longer extends the guard; the guard goes with the table. |
| **`TRN-003`'s named failure scenario** (the muxer yt-dlp started to merge the streams) | **OUT — corrected by the validator** | The vector passes `--hls-prefer-native`, which steers yt-dlp to its own HLS downloader; the flag is accepted by the installed `yt-dlp 2026.07.04`. The **structural** defect and the reproduction are unaffected — and `D2` strengthens that point, because the yt-dlp child is now the *only* transport, so a boundary gap there has no sibling transport to hide behind. **`B12`'s commit body states the conditional form, not the unconditional one.** |
| **`TRN-003`'s named failure scenario** (the muxer yt-dlp started to merge the streams) | **OUT — corrected by the validator** | The vector passes `--hls-prefer-native`, which steers yt-dlp to its own HLS downloader; the flag is accepted by the installed `yt-dlp 2026.07.04`. The **structural** defect and the reproduction are unaffected. **`B12`'s commit body states the conditional form, not the unconditional one.** |
| **`BRW-001`'s "`from None` sets `__cause__` and `__context__` to `None`"** | **OUT — corrected by the validator** | It sets `__cause__` and `__suppress_context__`; `__context__` is populated. **`B8` therefore carries the cause into the message text; it does not attempt to clear a `__context__` that is already there.** |
| **`pyproject.toml`'s wheel-artefact declaration** as an anchor | **OUT — no edit, but it is now load-bearing** | `B10` touches no packaging. `B15` **verifies** the declaration and the asset's presence and edits neither — but under `D4` that verification is the difference between "a broken build" and "a silently mis-detecting extraction", so the block must *assert the declaration names the asset* rather than merely note it. |
| **`docs/STRUCT.md`'s omission of `ytdlp_downloader.py`** | **OUT — phase 09 by R-E** | Recorded upstream as a cross-reference and not filed. Not this plan's subject. |
| **Any change to `.ai/audit/**`** | **OUT — read-only for this engagement** | See §1.5 and `B9`. **No block may edit a validated artifact or a source report, including its own.** |
| **`BRW-002`'s API asymmetry** (a method that creates a resource it cannot release) | **OUT — recorded, not a finding** | Deliberately so recorded by the validator. A reader must not implement a fix for it. |

### §1.5 Deferred — explicitly not in this plan

| Deferred item | Owner / trigger |
|---|---|
| **The console-encoding defect** — `config.setup_logging` gives the console sink a bare `logging.StreamHandler()` with no `errors=` handling, so a structlog record carrying non-encodable characters raises `UnicodeEncodeError` out of `logging.StreamHandler.emit`. **No finding in any phase owns it**: phase 01's `ENT-001`/`ENT-002` are sink-*routing* findings and deferred encoding to phase 08; phase 08 never filed it; a corpus search for `cp1251` finds it only as *evidence* inside `ENT-001`, `ENT-002` and `OUT-002`. | **The Product Owner's answer to §9 Q6.** Carried as `B16`, which is **CONDITIONAL** and must not be scheduled without that answer. `BRW-001`'s `logger.error(..., exc_info=True)` arm is the mechanism that exposes it; `B8` records the exposure and does not fix it. |
| **`phase05/VAL-501`'s correction of phase 06's `SEC-004`** | **Phase 06, and now more clearly stale.** `D2` removes the transport entirely, so phase 06's `SEC-004` does not merely assert a concealment that never worked — it asserts it **about a transport that no longer exists**. Its R5(d) `MET (argfile)` cells and its subject line are doubly wrong. The targets are under `.ai/audit/**`, which is **read-only** for this engagement, so `B9` **records** the correction in this plan and in commit bodies and does **not** perform it. **Trigger:** a documentation pass explicitly authorised to edit `.ai/audit/*/findings.md` must (a) replace both `MET (argfile)` cells, (b) rewrite the subject line so it does not name a deleted transport, and (c) record `D1` as the reason the exposure argument no longer distinguishes the transports. |
| **`TRN-009`'s capability half — the parts phase 06 keeps** | **Phase 06**, per the `Q5` decision recorded in §9: the yt-dlp terminal echo (`_echo_ytdlp_line`) and the path-matching capability in `_URL_REGEX`. `B14` takes only the **two unowned merge sinks** (`batch_merge_failed`, `final_merge_failed`), which appear in **neither** phase's set. This is **no longer an open ownership question** — the split is decided and `B14` is unconditional. |
| **`TRN-008`'s remedy shape** | **The Product Owner's answer to §9 Q4 — still open, and narrower.** `D2` deletes arm (a), so the question is no longer "hard failure or better degradation for a download substitution" but "does a missing muxer during the **merge** step hard-fail or degrade, given that the merge is already the tail of a failed download". §3 `B13` re-derives the three surviving arms and gives a recommendation; the decision is still the owner's because it moves a documented exit code. |
| **`phase05/VAL-502` chain 2** — the transport-shape decision | **CLOSED by `D2`.** Recorded in §9 with the owner's words. No longer a gate. |
| **`NET-007`'s withdrawn whole-operation budget** | **Phase 03, permanently withdrawn — and `D3` preserves it.** `D3` chose an **inactivity** bound, not a whole-operation budget, so the withdrawn decision stands and `_download_with_ytdlp`'s "no application-level download timeout is imposed" sentence needs **no** reversal. `B11` rewrites that sentence only to name the new setting and its inactivity semantics. |
| **The signal-handler skip table's rows** (`add_signal_handler` unreachable on Windows; the ladder's grace branch) | **Not findings.** Recorded upstream as skips. No block may implement them as defects. |
| **Test coverage for symbols with zero references** | **Phase 10 (`test-coverage`).** Blocks here add tests **for the finding they carry**, not for coverage's sake. |
| **Any change to `.kilo/rules/project.md`** | **Flagged, not fixed** — §5.6's rule-12 divergence. |

### §1.6 The `mypy` situation — stated once, so no block writes an impossible gate

`uv run mypy src` is **clean** (31 files). `uv run mypy src tests` reports **79 errors in 8 files**,
including `tests/test_config.py`'s `_build_settings(max_retries=…)` calls failing against
`SupportsGe`/`SupportsLe`.

**Therefore, binding on every block:** a block that touches **only `src/`** may write
"`uv run mypy src` is clean" as an acceptance criterion. A block that touches **`tests/`** **may not**
write "mypy clean" — the suite-wide `mypy src tests` invocation is **red before and after** and
carries no signal. Such a block writes instead: "`uv run mypy src` is clean **and** `uv run mypy src
tests` reports **the same 79 errors in the same 8 files**, with no error in any file the block
edited." A block that *reduces* the 79 is welcome and must be called out; a block that *adds* one is
a defect.

### §1.7 Corrections the Planner entered against the code context and the artifact

Six. Each was measured on the live tree at `HEAD = 4bf9efb` with a clean `src/`, and none changes a
decision — each corrects a target or a count. **Every block report cites these, not the superseded
form.**

1. **`TRN-008` arm (c) is misidentified in both the code context and the artifact.** The code
   context and the artifact's `TRN-008` both describe a `ModuleNotFoundError` arm in
   `_download_with_ytdlp` logging `download_failed`. **No such arm exists.** The live tree has
   `except FileNotFoundError:` logging **`ytdlp_not_found`**, and a missing *module* surfaces as the
   child's non-zero exit, reaching the `download_failed` record through the ordinary
   `returncode != 0` arm. `B13` must enumerate the four arms by their real statements.
2. **The documentation site that asserts the argv is *only* `['ffmpeg', '@<argfile>']` is at
   `docs/01-tools/api-reference.md`**, not `docs/99-reference/api-reference.md`. `B10` must edit the
   live path.
3. **The documentation site count is seven, not six.** `docs/99-reference/cli-reference-clean.md` is
   a **second copy** of the CLI reference and it also carries the `--method` option table and the
   worked `--method ffmpeg` example. `B10`'s documentation obligation therefore has **seven** files,
   one of which is a duplicate that will drift if only the first is edited.
4. **Three test class names in the code context's test-pinning inventory do not exist.** There is no
   `TestDownloadWithFFmpeg` (the cases live in **`TestHLSDownloaderDownload`**), no `TestFormatArgfile`
   (the `test_format_argfile_*` cases live **inside `TestTempArgfile`**), and no
   `TestCheckFFmpegAvailable` (it is **`TestFfmpegAvailabilityCheck`**).
5. **Two tests the code context lists as pins do not exist at all**:
   `test_download_with_ffmpeg_failure` and `test_download_with_ffmpeg_file_not_found`. The
   returncode-≠-0 fallback arm is pinned by
   **`TestHLSDownloaderDownload::test_error_handling_ffmpeg_failure`** (and its sanitising twin), and
   the `FileNotFoundError` arm has **no test**. **`TRN-008`'s arm (a) is unpinned, not pinned** —
   `B13` adds coverage rather than re-scoping it.
6. **`TRN-005` was a hazard-amplifier for `B2` in Revision 1, and `D2` removed the amplifier.** Revision 1
   argued that because `B3` made `read_progress` consume to EOF instead of breaking at the marker, more
   lines were read for longer, which made the oversized-line hazard `B2` fixes more reachable — an
   argument for `B2` before `B3`, recorded as edge `E3` and conflict `C3`. **Both of those are retired:
   `B3` is deleted**, so `iter_process_lines` keeps exactly its two yt-dlp consumers and the exposure is
   unchanged from what `B2` was scoped against. `B2` needs no reordering, and `E3` is gone from §4.1.

---
## §2 Baseline

### §2.1 The verification commands — re-run by the Planner against the live tree

```
$ uv run pytest tests -q
772 passed, 4 skipped, 1 warning in 30.30s                              EXIT=0

$ uv run ruff check src
All checks passed!                                                       EXIT=0

$ uv run ruff format --check src
31 files already formatted                                                EXIT=0

$ uv run mypy src
Success: no issues found in 31 source files                              EXIT=0

$ uv run mypy src tests
Found 79 errors in 8 files (checked 54 source files)                    EXIT=1
```

Re-run by the Planner against `HEAD = 4bf9efb` with `src/`, `tests/` and `pyproject.toml` **clean**.
**Not copied from the code context**, though it agrees with it. Three statements from the validated
artifact are now stale and are recorded once here:

- The artifact recorded `498 passed, 4 skipped`. The suite has grown to **772** through plans 05-09.
- The artifact's `mypy` line was "clean over five paths". It is clean over **`src`** only — §1.6.
- Bare `uv run mypy` is **not a valid invocation** here: `[tool.mypy]` declares no `files` or
  `packages`, so mypy has no default target. The documented form in `.ai/context/commands.md` is
  `uv run mypy <path>`.

**Expected skip count is 4, and all four are one Windows gate**: `os.chmod` on Windows toggles only
the read-only attribute, so the measured mode is `0o666` rather than the requested `0o600`. **No block
may change that count** — neither to hide a failure nor to "tidy" it. It is a `D-11` subject.

**The one warning is pre-existing and unrelated to any phase-05 anchor.** Do not fix it in a
subprocess block.

### §2.2 Binding project rules — every block

`.kilo/rules/project.md` (15 rules) is the binding set. **`AGENTS.md` does not exist** in this
repository at any depth — the environment context names it, but a recursive search returns nothing.
**No block may plan against it.**

| Rule | What it binds in this plan |
|---|---|
| **1. English only** | Comments, log event names, docstrings, error text, test docstrings. |
| **2. Production code is king** | Makes §2.6 load-bearing. **Five** test groups pin defective behaviour or assert an invariant a remedy would break; each travels with its fix **in the same change**. A block that cannot make a pinned test pass by fixing the code has misread its finding. |
| **3 / 4. Separation of concerns, single responsibility** | The subprocess helpers live in `services/ffmpeg_utils.py`; the transports in `services/downloader.py` and `services/ytdlp_downloader.py`. `B4` deliberately spans two modules because its two halves are one defect; `B16` deliberately lives in `config.py` rather than in `browser.py`. Neither may be used to justify growing `downloader.py` (690 lines) or `ytdlp_downloader.py` (815 lines). |
| **5. Avoid overengineering** | **The rule `B12` collides with head-on.** `TRN-003`'s remedy ranges from one keyword per platform to a Windows job object. The finding's HIGH severity and this rule pull opposite ways, which is why `B12` is `AWAITING DECISION` rather than assigned a remedy. It also constrains `B2`, `B4`, `B6`, `B11`, `B13` — every one of which has a one-line shape available and a framework shape rejected. |
| **6. Composition over inheritance** | No subclassing of the exception or process types. `B8`'s remedy composes a message; `B4`'s sink outcome must not become a class hierarchy. |
| **7. Follow existing patterns** | `logger = get_logger(__name__)` then `logger.<event>(key=value)`; dense decision-carrying provenance comments (`SEC-*`, `INT-*`, `D-11`, `STR-008`, `CON-*`). Any behaviour change **must** update the comment that justifies the old behaviour — several of those comments are exactly what is wrong (§5.2). |
| **8. Meaningful, consistent naming** | `TRN-012`'s remedy makes three spurious `ffmpeg_cancel_not_clean` / `yt_dlp_cancel_not_clean` records meaningful; if any block renames them it must do so in the same change and update **both** families, since sibling events in the same module use the unseparated `ytdlp_` form. Neither spelling appears in `tests/` or `docs/`, so both are internal-only and free to change. |
| **9. Type safety** | `mypy` is on for `src`. `Any` is prohibited. `_await_first_and_cancel_others` is typed `*tasks: asyncio.Task[Any]` — inside the very function `B4` must touch. `B4`'s change must not *add* `Any`, and if it removes one that is a bonus, not a requirement. `create_stealth_page` carries a `# type: ignore[union-attr]`; `B15` must not need to widen it. |
| **10. `StrEnum` for all constants** | Any new named value must be a `StrEnum` member or a frozen dataclass — **never a bare literal, never a dict**. Applies to `B2`'s chosen bound, `B4`'s outcome, `B11`'s bound, `B13`'s remedy mode. See §1.4: `TRN-013` was rejected for exactly this class of addition. |
| **11. Pydantic** | A new `Settings` field would be a `Field(default=..., ge=..., le=..., description=...)` appearing in **three** places (field description, `.env.example`, `docs/11-guides/configuration.md`), and `model_config`'s `extra="forbid"` makes that a correctness requirement. **No block in this plan adds a `Settings` field.** The Polars half of the rule is unfollowable — Polars is not a dependency — and is read as the Pydantic half only. |
| **12. No `print()`** | **Read the trap: the rule's text prescribes `logging.getLogger(__name__)` and the codebase universally uses `structlog`.** §5.6. |
| **13. Migrations for schema changes** | Not applicable — no database, no ORM, no migrations directory. Recorded so no block looks for one. |
| **14. Documentation stays current** | **Load-bearing and under-appreciated here.** `TRN-001` leaves **seven** documentation sites asserting a non-working mechanism (§1.7 item 3); `TRN-009` leaves a false claim in a docstring; `TRN-010`'s concealment rationale is void; `_temp_argfile`'s docstring and `download_with_ffmpeg`'s INT-001 note both describe the `@file` mechanism as working; `check_ffmpeg_available`'s hint text predicts an outcome its own code does not deliver. |
| **15. Small modules and functions** | Prefer a new small module to growing the three large ones. **Constrained by §2.3's packaging gate** — in practice: stay inside the existing module that owns the anchor. |

### §2.3 Repository constraints every block must respect

- **Layering is one-directional and acyclic**: `cli -> services -> infrastructure`;
  `services -> models | utils | config | exceptions`; `models` and `utils` depend on nothing. Two
  specific constraints bind this plan:
  1. **`services/ffmpeg_utils.py` is a leaf.** It imports **only** `..exceptions` and
     `..utils.formatting`. **`B2`, `B4`, `B5`, `B6` and `B11` must NOT add an import to it** —
     in particular no `url_sanitizer`, no `downloader_throttle`, no `downloader`. (**`B14` is the one
     knowing exception**, §5.2 item 3.) The stop state already arrives at `iter_process_lines` and
     `read_progress` **as a parameter**; that is deliberate and stays.
  2. **`services/downloader.py` is a backward-compatibility re-export facade** with a symbol-ownership
     comment and an explicit `__all__`. **Every fix goes in the owning module**: `iter_process_lines`,
     `read_progress`, `check_ffmpeg_available`, `cancel_subprocess`, the merge helpers ->
     `ffmpeg_utils.py`; `_temp_argfile`, `_format_argfile`, `HLSDownloader` ->
     `services/downloader.py`; `_download_with_ytdlp`, `_echo_ytdlp_line`,
     `_await_first_and_cancel_others`, `_build_ytdlp_cli_command` -> `services/ytdlp_downloader.py`;
     `sanitize_text_for_log` -> `utils/url_sanitizer.py`; `BrowserManager`, `create_stealth_page` ->
     `infrastructure/browser.py`; logging sinks -> `config.py`. **Editing a re-export line in
     `downloader.py` is never the fix** — except where `B10` must add a name that `tests/` imports
     from that module, which is then a facade obligation, recorded at the block.
- **`tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` is a hard gate**, asserted twice (exact entry
  set and exact entry count) and it covers **`tests/`** as well as `src/`. **Decision, stated once:
  no block in this plan adds a `src/` or `tests/` file.** New tests go into the **existing** test
  file that already owns the module under test (§2.6). `B12`'s boundary is the one block with a
  plausible reason to want a new module; rule 5 and this gate both push against it, and if its
  Planner concludes a new module is unavoidable the frozenset is edited **in the same change** with
  the reason recorded.
- **`tests/conftest.py` carries an autouse fixture, `isolate_settings_source`**, which chdirs to
  `tmp_path` and deletes every `VKDOWNLOADER_*` for each test. Any new test that reads `.env` or the
  environment must work inside it. The `test_settings` fixture carries **`max_retries=1`**.
- **Any new test that needs a set or unset stop state must use the project's own token idiom** — `set`
  a fresh `asyncio.Event` into `_shutdown_event_ctx` and `reset(token)` afterwards. The event is a
  `contextvars.ContextVar` whose value is **never reset** once created, so a leaked loop-bound `Event`
  poisons every later test in the session. **Binding on `B2`, `B4`, `B5`, `B6`, `B11`.**
- **There is no `aiohttp` session fixture, no ffmpeg-subprocess fixture and no fake clock.** No
  verification step in this plan may require network access. Every new test builds its own stand-in —
  a real `asyncio.StreamReader` fed by `feed_data`, or an `AsyncMock` process.
- **Windows runtime facts, binding on `B1`, `B2`, `B12`, `B16`:**
  - The loop is `ProactorEventLoop`. `loop.add_signal_handler` raises `NotImplementedError` (measured
    upstream), so `signal_handlers.py`'s `signal.signal` fallback is the branch that runs.
  - **`missing_ok=True` suppresses only `FileNotFoundError`.** A `PermissionError` — an antivirus
    scanner or indexer holding the temp file — propagates. This is `B1`'s whole subject.
  - `os.chmod` toggles only the read-only attribute, so `0o600` is a POSIX-only effect (`D-11`).
    `B1` must not "fix" the chmod and must not delete the `SEC-001`/`SEC-003` comment that requests it.
  - **A Ctrl-C in a console window also delivers `CTRL_C_EVENT` to child processes by default.** No
    block may assume the child survives an interrupt.
- **Exit codes are documented**: `130` = interrupted, `1` = failure, `2` = usage error. **`B11` must
  not turn a legitimate long download into `1` without the Product Owner's explicit decision**, and
  `B13`'s hard-failure option would make a missing muxer produce a different exit code than today's
  traceback-then-`1` — that is part of what §9 Q4 asks.

### §2.4 Documentation sites that assert the `@file` mechanism works — `B10`'s obligation

Seven files, measured. `B10` owns all seven **only if** option (A) or (C) is chosen; option (B) owns
the five that advertise a removed CLI option, and must still correct the two that describe the
mechanism itself.

| Site | What it asserts |
|---|---|
| `README.md` | The `--method ffmpeg` worked example. |
| `docs/99-reference/cli-reference.md` | The `--method` option row ("yt-dlp, ffmpeg, or auto") and the worked `--method ffmpeg` example. |
| `docs/99-reference/cli-reference-clean.md` | **The same two, in a duplicate of the above.** Editing only `cli-reference.md` leaves the copy lying. |
| `docs/01-tools/api-reference.md` | That the argv is **only** `['ffmpeg', '@<argfile>']`. |
| `docs/01-tools/quality-selection.md` | The transport table and two `--method ffmpeg` worked examples. |
| `docs/01-tools/vkdownloader-overview.md` | "**Secret-safe ffmpeg argument passing**: ... are passed to ffmpeg via a temporary argument file (`ffmpeg @argfile`) instead of command-line arguments. This prevents session tokens and CDN URL signatures from leaking into process listings ... The tokens are absent from process listings on both platforms". This is the strongest single claim in the corpus, and it is false today. |
| `docs/11-guides/vkdownloader-limitations.md` | The same claim plus the `--method ffmpeg` workaround row. |

Plus **two in-code comments that assert the same thing**: `_temp_argfile`'s docstring ("The caller
invokes `ffmpeg @<path>` so that sensitive values ... never appear in the process command-line
arguments") and `download_with_ffmpeg`'s INT-001/SEC-001 comment block. Those are **in `B10`'s
scope** regardless of option, because they are the code's own justification for the mechanism.

### §2.5 The landing rule — binding on every block

The tree is **clean under `src/`, `tests/` and `pyproject.toml`**. The dirty state is entirely under
`.ai/`: eight tracked **deletions** in `.ai/plans/`, one modified `.ai/problems/PROBLEM.md`, and five
untracked entries (`.ai/plans/05`-`08` and `tmp/`). `tmp/` is **not gitignored** — `git check-ignore`
returns no match and `.gitignore` lists no `tmp/` entry.

> 1. **A block's commit contains only its own work item.** Stage by **explicit semantic path**.
>    Never `git add -A`, never `git add .`, never `git commit -a`. Before committing, the block report
>    shows `git diff --cached --stat` and confirms every staged path belongs to the block.
> 2. **`.ai/audit/**` is read-only for this engagement.** No block may edit a validated artifact or a
>    source report — **including phase 05's own**. `.ai/plans/**` is *not* read-only, but **this plan
>    file is the only `.ai/plans/**` file any block may write.** `B9` writes exactly one new file
>    under `.ai/decisions/` (currently an empty directory).
> 3. **`tmp/` stays local and is never committed.** It is untracked and not ignored, so it will appear
>    in `git status`; that is pre-existing and **no block may `git add` it, delete it, or add it to
>    `.gitignore`.**
> 4. **The eight `.ai/plans/` deletions and the modified `.ai/problems/PROBLEM.md` are pre-existing.**
>    They must not be absorbed into a phase-05 commit and must not be restored by one.
> 5. **Exit codes and the documented `130`** must survive every block.

### §2.6 Test layout and the corrected test-pinning inventory

| Module under test | Test file (existing) | Class / area |
|---|---|---|
| `services/ffmpeg_utils.py` | `tests/test_ffmpeg_utils.py` + the reader area of `tests/test_hls_downloader.py` | `TestCancelSubprocess` in `test_ffmpeg_utils.py`; **`TestIterProcessLines`, `TestReadProgress`, `TestProgressParser`, `TestFfmpegProgress` are all in `test_hls_downloader.py`**, not in `test_ffmpeg_utils.py` |
| `services/downloader.py` | `tests/test_hls_downloader.py` | **`TestHLSDownloaderDownload`**, `TestTempArgfile` (which also holds the `test_format_argfile_*` cases), `TestFfmpegCookiePassing`, `TestFfmpegAvailabilityCheck`, `TestYtdlpCliCommand` |
| `services/ytdlp_downloader.py` | `tests/test_hls_downloader.py` | `TestEchoYtdlpLine`, `TestYtDlpSubprocessShutdown`, `TestAttemptSegmentResumeQuality` |
| `services/ytdlp_downloader.py` (output accumulation) | `tests/test_hls_downloader.py` | `TestEchoYtdlpLine` is the closest owner; `B6` adds its own class in the same file |
| `utils/url_sanitizer.py` | `tests/test_url_sanitizer.py` | `TestStripAuthParams`, `TestSanitizeTextForLog` |
| `infrastructure/browser.py` | `tests/test_browser_infrastructure.py` | `TestBrowserManager` — and **`create_stealth_page` has no test at all** |

**Project rule 2 inventory — corrected against the live tree** (§1.7 items 4 and 5 record the
corrections to the code context's version):

> **`D2` note, so a reader does not treat the deletions as gaps.** `B10` removes the
> `HLSDownloader` / `TestTempArgfile` / `TestFfmpegCookiePassing` / `TestReadProgress` /
> `TestProgressParser` / `TestFfmpegProgress` surface **in the same commit as the code it tests**, and
> with it the `B1`, `B3` and `B10` rows that depended on those classes. `D-12 cases 5/6/7` go with the
> `FFMPEG` dispatch arm; `D-12 case 10` **survives** and becomes the only thing keeping
> `perform_download`'s `case _:` arm honest. `TestFfmpegAvailabilityCheck` **survives** — the merge path
> still needs the muxer. **Two obligations are replaced rather than dropped:** `B1`'s ordering assertion
> relocates to a new cookie-cleanup case, and `B2`'s drain-test net narrows to the yt-dlp trio.

| Block | Test | What it pins | Disposition |
|---|---|---|---|
| **B10** | `tests/test_hls_downloader.py::TestHLSDownloaderDownload::test_download_with_ffmpeg_uses_argfile_syntax` | **Confirmed pin.** Asserts `len(captured_args) == 2` and `captured_args[1].startswith("@")`, and asserts the signed token is absent from argv — **it pins the non-functional invocation by name**. It passes because it checks the *invocation shape*, not whether the muxer understands it. | **Re-scoped, not deleted, not weakened.** Must assert the **new** contract. |
| **B10** | `::TestHLSDownloaderDownload::test_error_handling_ffmpeg_failure` and `::test_error_handling_ffmpeg_failure_sanitizes_url_in_error` | The `returncode != 0 -> None -> fallback` arm **every** `--method ffmpeg` invocation lands in. | **Must stay green unchanged.** They pin the fallback arm, which is correct behaviour and is not what `B10` removes. |
| **B10** | `::TestTempArgfile::test_temp_argfile_creates_and_cleans_up` and `::test_temp_argfile_permissions_are_0600` | The file is removed at context-manager exit; the `os.chmod(path, 0o600)` call. | **The cleanup test is `B1`'s to re-scope** (§3 `B1`); the permissions test is `B1`'s to **extend** with the new ordering assertion. |
| **B10** | `::TestFfmpegCookiePassing::test_download_with_ffmpeg_uses_cookies_protocol_option` | The argfile **content** carries `cookies=file:` and `-headers` — pins the *concealment mechanism*, not the invocation. | **Option-dependent.** Under option (A) there is no argfile, so this test is re-scoped; under (C) it stays green. The block's report must say which. |
| **B10** | `::TestTempArgfile::test_format_argfile_quotes_args_with_spaces`, `::test_format_argfile_preserves_urls`, `::test_format_argfile_simple_args` | `shlex.quote` per line and URL preservation — pins the response-file *format*, which option (A) orphans. | **Option-dependent.** Under (A) `_format_argfile` is deleted and all three go with it; under (B) likewise; under (C) they stay green. |
| **B1** | `::TestTempArgfile::test_temp_argfile_creates_and_cleans_up` | The file is removed at context-manager exit — **the ordering that is the `TRN-002` defect.** | **Re-scoped in the same change.** It must additionally assert that the file still exists while the child is running and is gone only after the termination guarantee has run. |
| **B3** | `::TestReadProgress::test_read_progress_stops_on_end` | Supplies `[b"frame=100\n", b"progress=end\n", b"frame=200\n"]` with the comment `# This should not be read`, then asserts `len(results) == 1` — **pins the `break` that abandons the child.** | **Re-scoped in the same change**, to assert the tail is consumed and reaches the collector. |
| **B4** | `::TestReadProgress::test_read_progress_handles_na_values` | The `N/A` sentinel path through `_PROGRESS_KEY_HANDLERS` — pins the guard that **is** present. | **Must stay green unchanged.** `B4` extends the guard; it does not replace it. |
| **B4** | `::TestReadProgress::test_read_progress_yields_progress`, `::test_read_progress_parses_all_fields`, `::test_read_progress_resets_on_continue` | The well-formed parse paths. | **Must stay green unchanged.** |
| **B2** | `::TestIterProcessLines::*` | The generator's line yield and the shutdown callback. **No test exercises a line at or above the 64 KiB reader limit**, so `TRN-004` has neither a pin nor coverage. | Add coverage. No pin to re-scope. All existing cases must stay green **unchanged** — the `fired`/`fire()` exactly-once invariant is a live constraint on `B2`'s remedy. |
| **B5** | `tests/test_ffmpeg_utils.py::TestCancelSubprocess::test_terminate_on_success`, `::test_kill_on_timeout` | Assert `result is True` on the graceful and force arms. | **Must stay green unchanged.** They pin the *correct* arms. |
| **B5** | `::TestCancelSubprocess::test_returns_false_on_process_lookup_error` | Makes `process.wait()` raise `ProcessLookupError`, then asserts **`result is False`** — pins the "already gone" contract the six call sites misread. | **Must stay green unchanged.** `B5` does not change `cancel_subprocess`; it changes the call sites. |
| **B5** | `::TestCancelSubprocess::test_backward_compatible_alias` | `cancel_ffmpeg_process is cancel_subprocess` — pins the alias `B11`'s bounded helper depends on. | **Must stay green unchanged.** |
| **B13** | — | — | **YES** | **YES** | MEDIUM | *Planner:* **retained after `D6`.** The remedy shape is fixed (option B), but three call sites change and there is a real fork: **whether the cache gains an invalidation path or is left write-once**, and where the single warning is emitted so arm (b), arm (c) and arm (d) all reconcile with it. *Validator:* arm (b) is **untested today** and is now the sharpest arm, and `D6`'s "no exit-code change" instruction is exactly the kind a well-meaning Implementor over-applies — the Validator must confirm no branch raises and no exit code moves. |
| **B13** | — | — | **YES** | **YES** | MEDIUM | *Planner:* **retained after `D6`.** The remedy shape is fixed (option B), but three call sites change and there is a real fork: **whether the cache gains an invalidation path or is left write-once**, and where the single warning is emitted so arm (b), arm (c) and arm (d) all reconcile with it. *Validator:* arm (b) is **untested today** and is now the sharpest arm, and `D6`'s "no exit-code change" instruction is exactly the kind a well-meaning Implementor over-applies — the Validator must confirm no branch raises and no exit code moves. |
| **B13** | — | — | **YES** | **YES** | MEDIUM | *Planner:* **retained after `D6`.** The remedy shape is fixed (option B), but three call sites change and there is a real fork: **whether the cache gains an invalidation path or is left write-once**, and where the single warning is emitted so arm (b), arm (c) and arm (d) all reconcile with it. *Validator:* arm (b) is **untested today** and is now the sharpest arm, and `D6`'s "no exit-code change" instruction is exactly the kind a well-meaning Implementor over-applies — the Validator must confirm no branch raises and no exit code moves. |
| **B6** | `::TestEchoYtdlpLine::test_ytdlp_echo_false_*` (4 tests) | Assert that with `echo=False` **nothing is written to stderr**. They pass, and they are the reason `TRN-011`'s accumulation is invisible from the console. | **Must stay green unchanged.** `B6`'s remedy must not make `echo=False` write anything. |
| **B7** | `tests/test_url_sanitizer.py::TestSanitizeTextForLog::*` (4 tests) | URL redaction in text, multiple URLs, text without URLs, yt-dlp output. **No test passes a filesystem path**, so the false path-redaction claim is unpinned *and* uncovered. | Green unchanged for `B7` (a documentation change). `B14` adds the path-shaped case. |
| **B7** | `::TestStripAuthParams::*` (8 tests) | The URL-only replacer's contract. | **Must stay green unchanged.** |
| **B8** | `tests/test_browser_infrastructure.py::TestBrowserManager::test_browser_manager_launch_failure_raises_extraction_error` | Asserts `pytest.raises(ExtractionError, match="Failed to launch browser for video extraction")` — **pins the message that names neither the binary nor the remedy**, and passes only because pytest's capture gives the record a non-strict stream. | **Re-scoped in the same change.** The `match` must be widened to the new text while still asserting the application's own exception type reaches the caller. |
| **B8**, **B15** | `::TestBrowserManager::test_con005_close_runs_on_stop_path`, `::test_con005_context_exit_stops_playwright_on_browser_close_error`, `::test_con004_con005_val401_cancelled_survives_close_error`, `::test_release_failure_nothing_in_flight_is_suppressed`, `::test_type_error_from_release_escapes`, `::test_hang_guard_close_bounded_by_wait_for` | Plan 08 `B4`'s six tests for `__aexit__`. They do not pin `BRW-001`/`BRW-003` but they **constrain any change to that method**. | **Must stay green unchanged.** |
| **B15** | — | — | **YES** | **YES** | HIGH | **Planner — retained, and the reason changed.** `D4`'s block had a determined remedy and no Planner; `D5` gives it back one, because the block now decides **where the flag is read at two consumption points**, **where exactly the conditional check sits**, and **what the field description must say** — four coupled statements across two modules and eleven documentation sites, which is not mechanical. *Validator:* **mandatory and the gate is the ordering proof** — a check that sits after `async_playwright().start()` satisfies every other assertion while achieving nothing. Plus `S1i`: it must confirm `B8`'s four anchors are untouched. |

The uniform failure mode this creates: an agent under gate pressure **weakens an assertion rather
than fixes the code**. Every block's Validator is briefed on it, and every re-scoped test must assert
the **new** contract, not a weaker one.

### §2.7 Machine facts — re-measured, binding on `B2` and `B10`

| Check | Value | Binds |
|---|---|---|
| Muxer on `PATH` | `C:\ffmpeg\ffmpeg.exe`, `ffmpeg version N-117624-g9eb7e8d2a4-20241023` (7.x-lineage nightlies) | `B10`, `B13` |
| `ffmpeg -h full` search for `@file` or `-/opt` | **no match for either** | `B10` — the whole basis of the option set |
| yt-dlp in the active environment | `2026.07.04` | `B6`, `B12` |
| Python | `3.12.1` | `B2`, `B12` |
| `asyncio.streams._DEFAULT_LIMIT` | `65536` | **`B2` — the bound is the standard library's default and is never set by this codebase** (no spawn site passes `limit=`) |
| `Settings()` on this machine | `download_timeout=300`, `max_concurrent_downloads=4`, `max_retries=3`, `log_file=None`, `log_level=INFO`, `headless=False`, `locale=ru-RU`, `timezone=Europe/Moscow` | `B11`, `B13` |

`B2`'s control experiment, re-run through the product's own `_format_argfile`: with the response
file, `output_created = False` and `Error opening output files: Invalid argument`; with the same
arguments passed directly, `output_created = True`. The **decisive** signal is `output_created`, not
the exit code. `B10`'s option analysis rests on this and must re-run it before it starts.

---

## §3 Execution blocks

**Fifteen blocks** after `D2` deleted `B3` as moot. Each surviving block is **one commit** and
**independently verifiable** against §2.1's commands. `B3`'s id is **retired, not reused** — the gap
in the sequence is deliberate, so Revision 1's cross-references stay readable.

**Read only the block you are handed** — §3 is self-contained per block; §4 is needed only if you are
scheduling.

**Gate status: ZERO GATES REMAIN.** All seven decisions (`D1`–`D7`) are recorded in §9, and every
block is executable without a further decision.

| State | Blocks | Meaning |
|---|---|---|
| **Unconditional — 15 of 15** | `B1`, `B2`, `B4`, `B5`, `B6`, `B7`, `B8`, `B9`, `B10`, `B11`, `B12`, `B13`, `B14`, `B15`, `B16` | No decision gate. **No block is `AWAITING DECISION`; none is `CONDITIONAL`.** |
| **DELETED** | `B3` | Moot by `D2`. §1.3 `S1a`. |

**What `D5` and `D6`/`D7` changed, so no one implements a superseded remedy:**

- **`B15` is re-scoped.** Stealth is now an **opt-in `Settings` field, default OFF**. Two of the four
  stealth components are gated; two are not. The asset check is **conditional on the flag** and, when
  it fires, hard-fails **before the driver starts**. `D4`'s unconditional hard failure is
  **superseded** — read `B15` before implementing it, because the warning branch it forbids is now
  conditional too.
- **`B13` is decided** — `D6`, option (B), better degradation, **no exit-code change**.
- **`B16` is ungated** — `D7`, adopted here.

---

### B1 — Make the yt-dlp transport's cookie-file destruction incapable of replacing the download's outcome

**Findings carried:** `TRN-002` **re-scoped by `D2`** — **MEDIUM** (was HIGH, re-scoped; see below) ·
`BEST-PRACTICE` · **mandatory**.

**Goal.** A failure to remove the yt-dlp transport's temporary cookie file must never turn a completed
download into a raised `OSError`.

**Re-scoped by `D2`. `TRN-002` had two halves and only one of them survives the deletion of the
ffmpeg download transport.**

| Half | Verdict | The code reason |
|---|---|---|
| (i) the destroy sits **outside** the child-termination guarantee, so a failed destroy **orphans the child** | **MOOT** | Its only instance is `_temp_argfile`'s `finally:`, reached before `download_with_ffmpeg`'s inner `try:`. `D2` deletes the method, the helper and the argfile together. Nothing can orphan a child this way any more. |
| (ii) a **failed destroy replaces the download's own outcome** | **SURVIVES** | `_download_with_ytdlp`'s `finally:` carries the identical pattern: `if cookie_file is not None and cookie_file.exists(): cookie_file.unlink(missing_ok=True)`. `missing_ok=True` suppresses **only** `FileNotFoundError`. A `PermissionError` from an indexer or scanner holding the file propagates out of the `finally:` and replaces the method's return value. |

**Established by reading the surviving `finally:` in full, so the residue is bounded honestly.** The
child **cannot** be orphaned here, because on every path the `finally:` runs the child has already
been reaped or cancelled:

- the normal and non-zero-returncode paths both pass `await process.wait()` before returning;
- the shutdown path returns after the race has settled the child;
- `except FileNotFoundError` means no child was ever created;
- `except asyncio.CancelledError` cancels the child, then re-raises, before the `finally:` runs.

So the surviving defect is **narrower and lower-severity than the original**: it cannot leak a
process, it can only mask an outcome. That is why this block's priority drops from HIGH to MEDIUM, and
it is stated here rather than left for a reader to discover.

**`phase05/VAL-502` chain 1 no longer applies to this block.** The coupling between `TRN-001` and
`TRN-002` existed because repairing one made the other worse; `D2` removes `TRN-001`'s subject
entirely, so there is nothing left to couple. See §1.3 `S1b`.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — the `finally:` clause's `if cookie_file is not None and cookie_file.exists(): cookie_file.unlink(missing_ok=True)` | The surviving instance of `TRN-002`. The destroy must not be able to replace the method's return value on any arm. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — `_build_ytdlp_cli_command`'s returned `cookie_file`, which this `finally:` consumes | **Read-only.** The cookie file is still required: it carries the Netscape cookie material for `--cookies`. `D2` does not touch it. |
| `services/ytdlp_downloader.py` | the `finally:`'s existing `logger.debug("cookie_file_cleaned_up", path=str(cookie_file))` | The success record. A failure record must sit beside it at a level a default run shows. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp`'s `except asyncio.CancelledError` arm, which cancels the child and re-raises | **Untouched.** It is what guarantees no child is alive when the `finally:` runs. |
| `services/downloader.py` | `_temp_argfile`, `download_with_ffmpeg`'s cookie-file `finally:` | **DELETED by `B10`.** This block must not reintroduce, mirror, or "share" the argfile logic — the pattern is being removed, not propagated. |

**Tests required**

- **ADD** — the surviving instance: a destroy that raises `OSError` leaves the file behind **and the
  call still returns normally**, on the success path, on the non-zero-returncode path (`None`), and on
  the shutdown path (`None`). Drive it by patching the unlink — **do not hold a real handle**, which
  makes the test machine-dependent.
- **ADD** — the negative case, so the fix cannot pass by deleting the cleanup: the file **is** removed
  when the destroy succeeds, and the `cookie_file_cleaned_up` record is written.
- **ADD** — the ordering assertion that makes the residue honest: on the failed-destroy path the child
  has already been waited or cancelled **before** the `finally:` runs. Assert on the observable
  effect (the process is reaped), not on a private attribute.
- **MUST STAY GREEN UNCHANGED** `::TestYtDlpSubprocessShutdown` and the yt-dlp drain tests named in
  `B2`'s prohibition list.

**Dependencies:** `depends_on: []`. **Ordered after `B10`** (`E2`) — `B10` deletes four
`cancel_subprocess` call sites in the same region of the same layer, and `B5` then re-scopes the two
that remain; sequencing the deletion first keeps `B5`'s diff reviewable against a settled tree.

**Risk class: MEDIUM.** One `finally:` clause, one file. The risk is over-reach: an Implementor who
reads "the cookie file must be removed" and hardens every cleanup in the module would undo `B10`'s
deletion work and invent a new abstraction.

**Prohibitions (binding)**

1. **MUST NOT** mirror the fix into `_temp_argfile` or any other argfile helper. `B10` **deletes**
   them. If the deletion has not landed, this block waits (`E2`) — it does not write code against code
   that is about to disappear.
2. **MUST NOT** add a shared cleanup helper, a context manager, or a new abstraction. There is one
   site after `B10`; one site does not need a helper (rule 5).
3. **MUST NOT** change the `except asyncio.CancelledError` arm or the child's termination ladder.
4. **MUST NOT** swallow the failure silently. It must be recorded, naming the path, at a level a
   default run shows.
5. **MUST NOT** change `cookie_file.exists()`'s guard semantics beyond what the failure handling needs.
6. No new module, no new dependency, no `Settings` field.
7. The `_download_with_ytdlp` "no application-level download timeout" docstring is **byte-identical**
   after this block — `D3` does not reverse it (`B11`'s subject, not this block's).

**Commit shape.** One commit, subject naming the yt-dlp cookie-file destruction, body carrying the
measured before/after (a destroy that raises `OSError`: before -> the method raises instead of
returning; after -> the method returns normally and one warning names the path), an explicit statement
that the **orphan** half is closed by `D2` and this block closes the **outcome** half, and the
priority re-grading with its reason. Cited `TRN-002`.

### B2 — Make one oversized child line incapable of killing the reader

**Findings carried:** `TRN-004` — **HIGH** · `BEST-PRACTICE` · **mandatory**.

**Goal.** A child line at or above the `StreamReader`'s limit must not raise out of the reader and
leave the pipe undrained.

**Why alone, and why `D2` did not moot it.** `iter_process_lines` is the **only** anchor in this plan
that a landed plan rewrote: `f6ed0cf` (plan 08 `B1`) added a watcher task, a `fire()` exactly-once
helper and a `finally:` that awaits the watcher. The defect survives inside the rewrite, untouched: the
`line = await stream.readline()` at the bottom of the `try:` is the same unbounded call, and no spawn
site in `src/` passes `limit=`, so the effective bound is
`asyncio.streams._DEFAULT_LIMIT = 65536`.

**After `D2` this function has exactly two consumers**, both in `ytdlp_downloader.py`:
`_monitor_progress` and `_drain_output`. The third consumer, `read_progress`, is deleted with the
ffmpeg download transport. **The hazard is fully live** — it is the yt-dlp child's stdout that must
survive a long line — and the block's substance is unchanged. What changed is the **regression net**:
four of the six drain tests Revision 1 named are deleted by `D2`, and the surviving net is re-listed
below.

**The consequence is permanent, not slow.** On this platform the reaper's result is returned only
once the returncode is set **and** every pipe has reached EOF. A reader that dies mid-stream leaves
the pipe attached and undrained, so the child's stderr never reaches EOF, so the transport can never
finish, so `await process.wait()` is **structurally incapable of returning** — even after `kill()`.
The parent emits no verdict of any kind.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ffmpeg_utils.py` | `iter_process_lines` — the `line = await stream.readline()` statement inside the `while True:` loop | The read must survive a line at or above the reader's limit. Four candidate shapes are named below and the block's Planner selects one against a measurement. |
| `services/ffmpeg_utils.py` | `iter_process_lines` — the `watch_task` created before the `try:`, and the `finally:` that cancels and awaits it | **Read-only obligation, and a constraint on the remedy.** Whatever shape is chosen must state what happens to `watch_task`: a remedy that raises, or that replaces the read, must still cancel the watcher and await it, and must not leave it pending. |
| `services/ffmpeg_utils.py` | `iter_process_lines` — the `fire()` helper and its `fired` flag | **The exactly-once invariant must survive.** `fire()` is the single place `on_shutdown` is invoked and both the between-lines guard and the watcher call it. A remedy must not add a second invocation site. |
| `services/ffmpeg_utils.py` | `iter_process_lines` — the `if not line: break` EOF branch | EOF must stay distinguishable from a stop. A bounded read must not turn EOF into a stop, nor a stop into EOF. |
| `services/ffmpeg_utils.py` | `iter_process_lines`'s docstring — the termination conditions it lists | Must be made true. After the fix it must also say what happens to a line the reader cannot hold in one piece. |
| `services/downloader.py`, `services/ytdlp_downloader.py` | the `asyncio.create_subprocess_exec` call sites — **three after `D2`**, down from four | **Read-only obligation.** None passes `limit=`. The block must state whether raising the spawn-time limit is part of its remedy or explicitly not, and why. |
| `services/ffmpeg_utils.py` | `read_progress` — its `shutdown_event` parameter, defaulting to a throwaway `asyncio.Event()` | **Unchanged.** Deliberate, because the module is a leaf. |

**Tests required**

- **ADD** — the case that does not exist: a real `asyncio.StreamReader` fed with **one line at or
  above the reader's limit**, then silence. Assert the generator yields the complete line (or the
  block's chosen contract), that it does not raise, and that **no task of ours is left pending**.
  No subprocess, no network.
- **ADD** — the stop-during-an-oversized-read case: the read is blocked on an oversized line, the
  stop is set, and `on_shutdown` must still fire **exactly once** and the generator must end. This
  is the interaction between `B2`'s remedy and `f6ed0cf`'s watcher, and nothing tests it today.
- **ADD** — the `watch_task` cleanup assertion on the oversized-line path specifically.
- **MUST STAY GREEN UNCHANGED** every existing `::TestIterProcessLines` case, including the
  exactly-once assertion on `on_shutdown`, and
  `::TestYtDlpSubprocessShutdown::test_ytdlp_cancelled_on_shutdown_returns_none`.
- **MUST STAY GREEN UNCHANGED** the drain tests a task-wrapped or raced read breaks. **The net after
  `D2` is the yt-dlp trio** — `test_ytdlp_stdout_progress_written_to_console`,
  `test_ytdlp_echo_false_suppresses_stderr_while_callback_fires`,
  `test_ytdlp_echo_false_progress_emits_debug_log` — **plus** the exactly-once assertion inside
  `TestIterProcessLines`. Revision 1 named six; `B10` deletes
  `test_error_handling_ffmpeg_failure`, `test_error_handling_ffmpeg_failure_sanitizes_url_in_error`,
  `test_download_with_ffmpeg_with_progress_callback` and
  `test_perform_download_ffmpeg_progress_adapter_sends_unknown_total` along with the transport that
  exercised them. **This is the regression net and the gate must be the full suite**, not the four
  cases in the class. A reader comparing this block to Revision 1 must not read the shorter list as a
  weaker gate.
- **MUST NOT GROW** the suite's warning count. If it does, the watcher must be created lazily rather
  than eagerly at generator entry, and the report says so.

**Dependencies:** `depends_on: []`. It precedes `B3` (`E3`).

**Risk class: HIGH.** A shared primitive with an already-landed plan's invariants on it, and the
failure mode of a *partial* fix is a drain that returns without draining.

**Prohibitions (binding)**

1. **`ffmpeg_utils.py` gains no import.** It stays a leaf.
2. `read_progress` keeps `shutdown_event` as a **parameter**.
3. `fire()` remains the single invocation site of `on_shutdown`; no second one is added.
4. The `finally:` that cancels and awaits `watch_task` is **preserved**.
5. **The read is not wrapped in a task and not raced.** Measured upstream: doing so costs ~35 us/line
   against ~1.6 us/line and, decisively, breaks six currently-green tests because the extra
   suspension lets `process.wait()` win the caller's `FIRST_COMPLETED` race and cancel the drain
   before it yields a single line.
6. **No new timeout in any transfer stage**, and no new module-level constant unless rule 10's shape
   is honoured (a named `StrEnum` member or a frozen dataclass — a bare literal is prohibited).
7. No `env=`/`cwd=`/`limit=` sweep of the four spawn sites: that is `B12`'s subject and touching it
   here would create a cross-block conflict with no finding behind it.

**Commit shape.** One commit, subject naming the reader's line bound, body carrying the measured
before/after (a line at the limit: before -> generator raises and the drain dies; after -> the
complete line is yielded), an explicit statement of what happened to `watch_task`, and the assertion
that `fire()` remains the only `on_shutdown` invocation site. Cited `TRN-004`.

#### §3.18 Decisions `B2`'s block Planner must make

**How to survive an oversized line.** Four shapes, named with what each costs:

- **(a) Raise the spawn-time `limit=`** on the four spawn sites. *Pro:* smallest diff. *Con:* it does
  **not** fix the defect — it moves the threshold. A line above the new limit still raises. If the new
  limit is large enough to be "practically unreachable", that is an unmeasured assumption, which is
  precisely the class of reasoning `TRN-001` was filed about. **Rejected unless the block can state
  a measured maximum line length for both children.**
- **(b) Catch the overrun inside `iter_process_lines` and treat it as end-of-stream.** *Pro:* smallest
  correct diff; the reader never dies. *Con:* silently truncates the child's output, which is
  `TRN-005`'s defect in a new place, and leaves the rest of the line in the pipe.
- **(c) Read the oversized line in bounded pieces and yield the reassembled line as one item.**
  *Pro:* the caller's contract is unchanged — it still receives whole lines — and nothing is lost.
  *Con:* the reassembly must be interruptible, or it becomes a **new** unbounded wait; and it interacts
  with the watcher's exactly-once invariant.
- **(d) Re-raise as a typed, catchable product error after draining the remainder of the line.** *Pro:*
  the failure is visible; the caller can terminate the child through a path it already owns. *Con:*
  requires a new exception type, which is rule 10's shape question, and the caller changes.

→ **The block's Planner selects, and the block report records the measurement that decided it.**
Binding regardless of the choice: `fire()` stays exactly-once, `watch_task` is still awaited, the
reassembled or discarded path is **not** an unbounded wait, and the EOF-vs-stop distinction survives.

---

### ~~B3 — DELETED: moot by `D2`~~

**This block is deleted. It is not deferred, not merged, and its id is retired rather than reused.**

**Finding:** `TRN-005` — the `if value == "end": break` inside `read_progress`, which stops reading
while the child is still running and truncates the child's output after its final progress block.

**The code reason, established against the live tree.** For the defect to be reachable, a child must
emit ffmpeg's `-progress` stream. Two facts decide it:

1. **Only `download_with_ffmpeg` passes `-progress`.** Its `ffmpeg_args` begin
   `["-y", "-progress", "pipe:2", "-nostats", ...]` and it is that stream `read_progress` parses.
2. **The merge transport never does.** `_build_ffmpeg_concat_command` returns
   `["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", <list>, "-c", "copy", <out>]` — no
   `-progress` argument at all — and `_merge_batch_segments` / `_perform_final_merge` read their
   children with `process.communicate()` under `_await_ffmpeg_with_timeout`, which parses nothing and
   has no progress marker.

`D2` deletes `download_with_ffmpeg`, `HLSDownloader`, `_temp_argfile`, `_format_argfile` and, with
them, `read_progress`, `ProgressParser`, `FfmpegProgress` and `_PROGRESS_KEY_HANDLERS`. The merge
transport — which **stays**, because segment merging still needs the muxer — was never a consumer.
**Therefore no reachable code can produce `TRN-005`'s defect after `D2`, and the finding is disposed
of rather than left open.**

**What a reader must not conclude.** This is not a claim that the defect never existed: it existed and
was measured. It is a claim that the **subject** is removed. `B2` and `B4` survive because their
subjects — `iter_process_lines` and `_await_first_and_cancel_others` — are both still reachable from
`_download_with_ytdlp`. Anyone tempted to reinstate a muxer download transport must be told, in the
commit that does it, that `TRN-005` returns with it and needs re-filing.

**Consequences already absorbed elsewhere in this plan**, so no cross-reference goes stale:

- `B2`'s regression net loses four tests that `D2` deletes; the surviving net is re-listed at `B2`.
- `B4` loses the parse half that shared `read_progress` with this block; it survives on the sink half.
- `§8.4`'s trace records `TRN-005` as **moot by `D2`**, not as pending.
- `§10` records the deletion in the disclosures.

### B4 — Make a reader failure visible instead of swallowed

**Findings carried:** `TRN-006` **sink half only** — **HIGH** · `BEST-PRACTICE` · **mandatory**.
**Re-scoped by `D2`**; the parse half is gone (§1.3 `S1a`, §1.8).

**Goal.** A reader task that fails must be reported, not absorbed.

**What `D2` removed.** `TRN-006` had two halves, and they were inseparable while both existed:

- the **parse half** — `_PROGRESS_KEY_HANDLERS`' unguarded `int()`/`float()` conversions, reached
  through `read_progress` — **is deleted**, because `read_progress`, `ProgressParser`, `FfmpegProgress`
  and the table go with the ffmpeg download transport. The validator's correction that every entry
  already carries a `v != "N/A"` guard is now moot as well: there is no table.
- the **sink half** — `_await_first_and_cancel_others` returns a failed task in `done` without
  retrieving its exception, and **all four call sites discard the return value** — **survives whole.**

**Why the surviving half is now *more* important, not less.** After `D2`,
`_await_first_and_cancel_others` is the observer for the **only reader the product has left**. `B2`
makes that reader survive an oversized line; this block makes its death *visible*. Before the deletion
there were two readers and one sink; now there is one reader and one sink, so this is the single point
at which a yt-dlp drain failure can be detected at all. A silent reader death here leaves the child's
stdout pipe undrained, and an undrained pipe means `await process.wait()` can never return — the same
permanent wedge `B2` addresses, one layer up.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ytdlp_downloader.py` | `_await_first_and_cancel_others` — its `except asyncio.CancelledError: pass` arm and its `return done, pending` | The surviving half of the finding. A task that raised is returned in `done` and its exception is never retrieved, so no record is produced and no exception propagates. |
| `services/ytdlp_downloader.py` | `_await_first_and_cancel_others` — its signature and return annotation, typed `*tasks: asyncio.Task[Any]` | **The block may not add `Any`.** Removing the existing one is a bonus, not a requirement. |
| `services/ytdlp_downloader.py` | `_await_first_and_cancel_others` — its `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)` and the pending-task cancel-and-await loop | **Plan 08's contract, binding.** It must still cancel and await every pending task before returning. This block adds *reporting*, not a change to settlement. |
| `services/downloader.py` | the `await _await_first_and_cancel_others(...)` call sites | **After `D2` there are two, both in `ytdlp_downloader.py`** (`_monitor_progress` and `_drain_output`, each in two branches). `download_with_ffmpeg`'s two call sites are deleted. All surviving sites must be reviewed in the same change. |
| `services/ffmpeg_utils.py` | `_await_ffmpeg_with_timeout`, which drains with `process.communicate()` and is the merge transport's completion path | **Read-only.** It never uses `_await_first_and_cancel_others`; it is not affected and must not be made to. |
| `services/ffmpeg_utils.py` | module-level `_PROGRESS_KEY_HANDLERS`, `ProgressParser`, `FfmpegProgress`, `read_progress` | **DELETED by `B10`.** This block must not reintroduce, extend or reference them. |

**Tests required**

- **ADD** — the sink case, which no test covers today: a reader task that raises produces **one**
  record. Assert on the observable effect (the log record), not on the helper's return tuple.
- **ADD** — the discrimination case: a task that **completes normally** produces **no** record. Without
  it the fix is satisfiable by logging every finished task, which would be noise, not visibility.
- **ADD** — the cancellation case: a pending task that is cancelled and settles does **not** produce a
  record. This is plan 08's settlement contract and this block must not break it.
- **MUST STAY GREEN UNCHANGED** `::TestYtDlpSubprocessShutdown` and the yt-dlp drain trio named in
  `B2`'s criteria.
- **DELETED by `B10`, so they no longer gate this block**: `::TestReadProgress`'s four cases and
  `::TestProgressParser` / `::TestFfmpegProgress`. Revision 1 listed
  `test_read_progress_handles_na_values` as this block's regression net for the guard extension; **that
  obligation is discharged by the deletion**, not weakened by it.

**Dependencies:** `depends_on: []`. Reviewed after `B2` (`E3`) — the pair is prevention-then-reporting
of the same failure, and `B4`'s report must say how many routes remain when both have landed.

**Risk class: HIGH** for a one-module block. It changes what a shared helper does on the failure path,
and the failure path is the path no test currently exercises.

**Prohibitions (binding)**

1. **MUST NOT** touch `_PROGRESS_KEY_HANDLERS`, `ProgressParser`, `FfmpegProgress` or `read_progress`.
   They are deleted. "Extending the `N/A` guard" is not this block any more.
2. **MUST NOT** add an import to `ffmpeg_utils.py`, and **MUST NOT** add one to
   `ytdlp_downloader.py` for the reporting mechanism unless the report justifies it against rule 4.
3. **MUST NOT** change the cancellation-and-settlement contract plan 08 built. If any part of it is
   reversed, the report names the part and the reason.
4. **MUST NOT** make a **normal** completion look like a failure.
5. **MUST NOT** add `Any` to any annotation.
6. **MUST NOT** add a bound to any wait. `NET-007` stands and `D3` preserved it.
7. **MUST NOT** re-raise the failed task's exception out of the helper. That would change a drain into
   a crash, and it is the specific over-correction this block's option analysis names.

**Commit shape.** One commit, subject naming the swallowed reader failure, body carrying the measured
before/after (a reader task that raises: before -> no record and no exception; after -> exactly one
record, with a normally-completing task producing none), an explicit statement that the parse half is
disposed of by `D2`, and the statement that this sink is now the only observer of the only reader left.
Cited `TRN-006`.

#### §3.20 Decisions `B4`'s block Planner must make

**How "visible" is expressed without reversing plan 08.** Two shapes:

- **(a) Retrieve and report each failed task's exception** — the return shape stays exactly as it is,
  the reporting is new. *Pro:* the smallest change; every existing call site keeps working unchanged
  because they all discard the return anyway; plan 08's contract is untouched. *Con:* the report is
  produced by the helper, so the helper must now know the log event name.
- **(b) Surface a completion outcome the callers act on** — a richer return type the call sites must
  branch on. *Pro:* the caller can decide what a reader failure means. *Con:* it changes the return
  contract for two call sites and forces `B2`'s interaction to be re-reviewed; larger diff for the
  same visibility.

→ **Recommended: (a).** The return value is currently discarded by every surviving call site, so (a)
delivers the whole of the finding with no contract change at all, and (b) would create a new coupling
between this helper and two closures for no behavioural gain. If the block's Planner chooses (b), the
report must name what a caller does with the outcome that it does not do today.


### B5 — Read `cancel_subprocess`'s documented return contract correctly at its two surviving sites

**Findings carried:** `TRN-012` — **MEDIUM** · `BEST-PRACTICE` · **mandatory**.

**Goal.** A process that is **already gone** must not be reported as "not clean".

**Why alone.** The validator established that the function is **correct as documented** — "True if
process was cancelled, False if process was already gone" — and that the defect is **entirely in the
call sites**. The remedy is a mechanical guard, with no uncertainty.

**Re-scoped by `D2`: six sites become two.** Revision 1 counted six boolean-reading call sites — four
in `download_with_ffmpeg` (`_monitor_progress`'s and `_drain_stderr`'s `_on_shutdown` closures, the
stop branch after the re-wait, and the `finally:`) and two in `_download_with_ytdlp` (its `_on_shutdown`
and the `except asyncio.CancelledError:` arm). `D2` deletes `download_with_ffmpeg`, so **all four of
its sites go with it.** The two in `ytdlp_downloader.py` survive, and the misreading survives with
them.

**The failure mode is weaker but real, and the weakening is stated rather than assumed.** Revision 1's
"three spurious records per stop" was a property of `download_with_ffmpeg`'s composition: the same
handle received `cancel_subprocess` three times — from the reader's stop branch, from the stop branch
after the re-wait, and from the `finally:`. `_download_with_ytdlp` has **no** such composition: its
`if shutdown_event.is_set():` arm simply returns `None` without calling the ladder. What survives is a
two-call sequence — the reader's `_on_shutdown` terminates the child, and if the caller's task is then
cancelled, the `except asyncio.CancelledError:` arm calls the ladder again on a child that is already
gone and logs `yt_dlp_cancel_not_clean` for it. **One** spurious record, not three.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ffmpeg_utils.py` | `cancel_subprocess` — its `except ProcessLookupError: return False` arm, its return annotation and its `Returns:` docstring | **The contract is correct and must not change.** It may be re-documented to state explicitly that `False` means "already gone, therefore clean", because two readers got it backwards. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — the `if not await cancel_subprocess(process):` guard inside its `_on_shutdown` closure | Must warn only when the child is **genuinely still running** after the ladder. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — the `if not await cancel_subprocess(process):` guard in its `except asyncio.CancelledError:` arm | Same treatment. |
| `services/ffmpeg_utils.py` | `_await_ffmpeg_with_timeout` — its `except (TimeoutError, asyncio.CancelledError): await cancel_ffmpeg_process(process); raise` arm | **The one call site that already ignores the return value correctly.** It is the in-repo precedent, it is unaffected by `D2`, and it must stay exactly as it is. |
| `services/ffmpeg_utils.py` | `cancel_ffmpeg_process`, the backward-compatible alias | **Untouched.** `test_backward_compatible_alias` stays green. |
| `services/downloader.py` | the four `cancel_subprocess` call sites | **DELETED by `B10`.** This block must not reintroduce or mirror them. |

**Tests required**

- **ADD** — the composition case: the reader's `_on_shutdown` terminates the child, then the
  `CancelledError` arm runs; **no** `yt_dlp_cancel_not_clean` record is written for the second call.
  Assert on the log records, not on the return values.
- **ADD** — the negative case, which is **mandatory**: a child that is **still running** after the
  ladder **does** produce the record. Without it the fix is trivially satisfiable by deleting the
  warning, and that must not be a passing outcome.
- **MUST STAY GREEN UNCHANGED** `tests/test_ffmpeg_utils.py::TestCancelSubprocess` in full,
  including `test_returns_false_on_process_lookup_error` (which pins the correct contract),
  `test_terminate_on_success`, `test_kill_on_timeout` and `test_backward_compatible_alias`.

**Dependencies:** `depends_on: [B10]` (`E2`) and ordered after `B1` (`E4`). `B10` deletes four of the
six sites and changes this module's neighbourhood; `B1` hardens the cookie-file `finally:` in the same
function whose `CancelledError` arm this block guards.

**Risk class: MEDIUM.** Two mechanical edits, but the failure mode is a *deleted* warning that no test
distinguishes from a fixed one.

**Prohibitions (binding)**

1. **`cancel_subprocess`'s return contract does not change.** No tri-state, no new exception, no
   renamed return value. The function is correct.
2. **MUST NOT** re-add a guard in `download_with_ffmpeg` or any other deleted site.
3. `_await_ffmpeg_with_timeout`'s arm is **untouched**, and the alias stays an alias.
4. **No warning is deleted** — each is made conditional, and the positive case is mandatory.
5. No change to the termination ladder itself: the `terminate()` -> `wait_for(..., 5.0)` -> `kill()` ->
   `wait()` order, or the keyword-only `timeout: float = 5.0`.
6. If `yt_dlp_cancel_not_clean` is renamed, the whole family goes with it and the unseparated
   `ytdlp_*` siblings in the same module are reconciled in the same change (rule 8). Neither spelling
   appears in `tests/` or `docs/`, so both are internal-only and free to change.

**Commit shape.** One commit, subject naming the termination ladder's return contract, body carrying
the measured before/after (two calls on one handle: before -> the second logs `yt_dlp_cancel_not_clean`;
after -> it does not) and the record count on the stop path, plus an explicit statement that the
four-site composition was deleted with the transport. Cited `TRN-012`.


### B6 — Stop accumulating a child's entire transcript, including the transcript nobody asked for

**Findings carried:** `TRN-011` — **MEDIUM** · `BEST-PRACTICE` · **mandatory**.

**Goal.** The buffer that exists only to build a failure message must be bounded, and in batch mode
it must not grow at all.

**Why alone.** One private buffer in one function, a different failure mode (memory) from every other
block, and a verification shape nothing else here produces (accumulated bytes, not a log record).

**The code context's sharpening, which the block must honour.** At both append sites the ordering is
`_echo_ytdlp_line(decoded, echo=echo)` **then** `output_chunks.append(line)`. `_echo_ytdlp_line`
returns without writing anything when `echo=False` — and the line is stored anyway. So in batch mode
the entire child transcript is accumulated for output that was just deliberately discarded. Measured
growth: **108.6 MiB for 50 MiB of child output**, which multiplies across the batch
(`max_concurrent_downloads` accepts up to 16).

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — the `output_chunks: list[bytes] = []` accumulator | Must be bounded. **No `Settings` field** — see §2.2 rule 11 and the `TRN-013` precedent. The in-repo precedent for this exact need is `ffmpeg_utils.py`'s `error[:200]` / `stderr.decode()[:200]` truncation, i.e. a module-level constant. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — the two `output_chunks.append(line)` sites, inside `_monitor_progress` and `_drain_output` | The two branches must behave identically. If accumulation is skipped when `echo=False`, it must be skipped in **both**. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — the `output_data = b"".join(output_chunks) if output_chunks else b""` statement and its only consumer, the `returncode != 0` arm | The joined buffer is decoded and then transformed, adding two more copies on the failure path. Bounding the accumulator bounds all three. |
| `services/ytdlp_downloader.py` | `_echo_ytdlp_line` — its `if not echo:` early-return branch | **Read-only obligation.** `B6` must not make `echo=False` write anything. Four currently-green tests assert exactly that. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp`'s docstring — the `echo` parameter's description | If the block makes accumulation conditional on `echo`, the docstring must say so. |

**Tests required**

- **ADD** — a child that writes far more than the bound: assert the **accumulated buffer** stays at
  or under the bound and the call still returns normally on the success path. Assert on the buffer's
  size through the observable effect (the failure message's length), not on a private attribute.
- **ADD** — with `echo=False`: assert that a chatty child leaves the buffer empty **and** that
  nothing was written to stderr. This is the case that makes the ordering defect visible.
- **ADD** — the failure path still produces a usable error message containing the child's most
  relevant output. **Which** output that is (the head or the tail) is the block's Planner's decision,
  recorded below.
- **MUST STAY GREEN UNCHANGED** all four `::TestEchoYtdlpLine::test_ytdlp_echo_false_*` cases, and
  `::TestYtDlpSubprocessShutdown`.

**Dependencies:** `depends_on: []`. Shares `_download_with_ytdlp` with `B11` — see `C13`.

**Confirmed unaffected by `D1`–`D4`.** Its entire subject is the yt-dlp transcript buffer, which the
transport deletion does not touch, and the four bounding decisions change nothing about it. `B10`
deletes no statement in `_download_with_ytdlp`'s body; it deletes `download_with_ffmpeg` elsewhere in
the package. Re-verified against the live tree: `output_chunks` and both append sites are inside
`_monitor_progress` and `_drain_output`, and neither symbol is named by anything `B10` removes. **This
block stands exactly as Revision 1 wrote it**, with no re-scoping and no dependency change.

**Risk class: MEDIUM.** A buffer bound is easy to get wrong in the direction of losing the message
that explains a failure.

**Prohibitions (binding)**

1. **No `Settings` field.** No new environment variable, no CLI option, no `.env.example` row, no
   configuration-guide row.
2. `_echo_ytdlp_line` gains **no** parameter and writes **nothing** when `echo=False`.
3. No new module and no new import in `ytdlp_downloader.py` for the bound.
4. The four `echo=False` tests stay green **unchanged** — no edits at all.
5. The bound is not enforced by **dropping** lines silently; if a line is not accumulated the block
   says so in the docstring.
6. No change to `max_concurrent_downloads`, the segment fan-out, or the batch permit — those are
   plan 04's and plan 07's.

**Commit shape.** One commit, subject naming the child's output accumulation, body carrying the
measured before/after (peak growth for a 50 MiB child: before -> 108.6 MiB; after -> the chosen
bound), the chosen bound and where it is declared, and an explicit statement that **no setting was
added**. Cited `TRN-011`.

#### §3.21 Decisions `B6`'s block Planner must make

**Bounded how?** Four shapes:

- **(a) A capped tail** — keep the last N bytes, drop the oldest. *Pro:* a failure's informative part
  is almost always at the end; the join stays O(N). *Con:* needs a bounded-buffer structure (a
  `deque` of lines with a running total, or a `bytearray` trimmed per line), which is the largest of
  the four diffs.
- **(b) A capped head** — keep the first N bytes, drop the rest. *Pro:* trivial (`bytearray` with an
  `if len(...) > N: del ...` trim). *Con:* the message is usually the *tail*; a truncated-from-the-end
  error message loses the reason.
- **(c) Accumulate only on failure** — buffer to a bounded ring while the child runs, and join only
  in the `returncode != 0` arm. This is (a) with the join moved.
- **(d) Do not accumulate at all when `echo=False`.** *Pro:* smallest, and it removes the batch-mode
  amplification entirely. *Con:* batch mode's `download_failed` record loses its `error` field —
  a **diagnostic regression in the exact mode that already cannot see the console output**.

→ **Recommended: (a) or (c).** (d) is a real improvement with a real cost and is the block's Planner's
call, but the report must state the diagnostic regression explicitly if it is chosen. (b) is
rejected: the tail is the informative part.

**What is the bound's number and where does it live?** A module-level private constant in
`services/ytdlp_downloader.py`, sized against the in-repo precedent (`ffmpeg_utils.py` truncates a
merge error to 200 characters) and against the 64 KiB the reader can hold per line. Rule 10 governs
the *shape* if the value ever becomes a named setting — it does not become one.

---

### B7 — Stop the sanitizer's docstring and the yt-dlp comment claiming a capability its regex cannot deliver

**Findings carried:** `TRN-009` *(claim half)* **re-scoped by `D2`: two of three sites** — **MEDIUM** ·
`SPEC-DEVIATION` · **mandatory**.

**Goal.** No artifact in the repository may claim that `sanitize_text_for_log` redacts filesystem
paths. It cannot: the transform is a single `_URL_REGEX.sub` over `https?://[^\s'\"<>]+`, and a path
contains neither prefix, so it can never match, and `_strip_auth_params` — reached only from a match —
can never be reached for one.

**Re-scoped by `D2`: three sites become two.** Revision 1 named three artifacts making the false claim:
the function's **own docstring**, the `# SEC-002:` comment in `_download_with_ytdlp`, and the
`# SEC-002:` comment in `download_with_ffmpeg`. **The third is deleted with the method.** The first two
survive: the docstring is shared and the yt-dlp transport is the one that remains — and the yt-dlp
transport is the one that still writes `--cookies <path>` and the media URL into argv, so **its**
comment is now the one that most needs to stop over-claiming.

**Why this half is unconditional.** A false claim is false today under every resolution. Phase 06 may
eventually add path redaction; until it does, the claim lies. Rule 14 makes correcting it mandatory,
and there is no decision to take.

**Why it stays split from `B14`.** Different modules (`utils/url_sanitizer.py` plus one comment in
`services/ytdlp_downloader.py` against two sinks in `services/ffmpeg_utils.py`), different ownership,
different verification — a docstring's text against a path-shaped input being redacted — and above all a
different **gate**: `B14` is now decided and unconditional, but it applies the transform, while this
block changes no behaviour at all. Merging them would put an unconditional documentation correction
behind an implementation.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `src/vkdownloader/utils/url_sanitizer.py` | `sanitize_text_for_log`'s **own docstring** — the third sentence, which claims the transform prevents "signed CDN tokens **or cookie file paths** ... from leaking into log files" | The **false** claim, and the significant one the artifact did not name: the function documents itself as doing something it cannot do. The first sentence ("Scans `text` for `http(s)://` URLs and replaces each match with only its scheme and host") is **accurate** and must be kept. |
| `src/vkdownloader/utils/url_sanitizer.py` | module-level `_URL_REGEX` | **Unchanged.** This block is documentation. |
| `src/vkdownloader/services/ytdlp_downloader.py` | `_download_with_ytdlp` — the `# SEC-002:` comment above the `error_msg = sanitize_text_for_log(error_msg)` pair | Its claim ("redact any signed CDN URLs **or cookie file paths**") has a true half and a false half. Keep the true half, drop the false one. **This is the only surviving source comment.** |
| `src/vkdownloader/services/downloader.py` | `download_with_ffmpeg`'s `# SEC-002:` comment | **DELETED by `B10`.** |
| `src/vkdownloader/services/ytdlp_downloader.py` | `_echo_ytdlp_line`'s `sys.stderr.write(...)` calls | **Phase 06's, per the `Q5` decision.** Read-only here; `B14` does not touch it either. Recorded so no block mistakes it for either of theirs. |

**Tests required**

- **ADD** — a test that pins the **capability boundary** so the docstring cannot drift back: a
  filesystem path and a bare URL both passed through `sanitize_text_for_log`, asserting the URL is
  redacted and the path is returned **unchanged**. Today no test passes a path at all, which is why the
  false claim survived. **This test is the whole point of the block.**
- **MUST STAY GREEN UNCHANGED** `tests/test_url_sanitizer.py::TestStripAuthParams` in full and
  `::TestSanitizeTextForLog`'s four existing cases.

**Dependencies:** `depends_on: []`. It precedes `B14` (`E7`) — if phase 06 later extends the matcher,
this block's wording must be revisitable, so it lands first and is written to be.

**Risk class: LOW.** Documentation only, zero product risk, and the added test is a two-line
characterisation.

**Prohibitions (binding)**

1. **`sanitize_text_for_log`'s behaviour does not change.** No regex is edited, no branch is added.
   Extending the matcher is **phase 06's** (`SEC-006`), not this plan's — the `Q5` decision assigned it
   elsewhere. This block must not pre-empt it.
2. `_strip_auth_params` and `sanitize_url_for_log` are **untouched**.
3. The docstring's **accurate** first sentence survives. The block corrects a false clause; it does not
   replace the docstring.
4. **MUST NOT** delete the `SEC-002:` comment entirely — the cross-reference to the phase that owns
   the exposure judgement is worth keeping; only the false clause goes.
5. No new test file; the new case goes inside `TestSanitizeTextForLog`.
6. No change to any log record's fields, level, or event name.
7. **MUST NOT** edit `_echo_ytdlp_line` or the two merge sinks — they are `B14`'s or phase 06's.

**Commit shape.** One commit, subject naming the sanitizer's documented capability, body stating that
**no behaviour changed**, that the third site was deleted with the transport by `B10`, and that the
capability itself is phase 06's `SEC-006` under the `Q5` decision. Cited `TRN-009` — **not**
`SEC-005`/`SEC-006`, which this plan does not claim.


### B8 — Carry the launch failure's actionable cause into the `ExtractionError`

**Findings carried:** `BRW-001` *(half a: the `from None` half)* — **HIGH** · `RUNTIME-ERROR` ·
**mandatory**.

**Goal.** A caller must learn **which** browser binary is missing and **how** to obtain it, without
the Playwright banner's box-drawing characters ever reaching a console.

**Why this half alone.** The code context re-measured the two mechanisms and they no longer behave
alike. **This half fires unconditionally** on every launch failure on every machine: `raise
ExtractionError(...) from None` sets `__cause__ = None` and `__suppress_context__ = True`, while
`__context__` stays populated with the Playwright error — whose message contains the missing
executable path **and** the `playwright install` remedy. Both are removed from the displayed
traceback. The validator's correction is binding: the remedy is to **carry** the cause into the
`ExtractionError` text, **not** to remove a `__context__` that is still there.

**Why the encoding half is not here.** It is conditional — it fires only on a strict-encoded stderr
and **not** on the log-file sink, where the JSON renderer ASCII-escapes the traceback — and its
remedy belongs in `config.py`'s `setup_logging`, a different module. It is owned by **no finding**
(§1.5). It is `B16`, conditional on §9 Q6, which **`D1`–`D4` did not answer**.

**Confirmed unaffected by `D1`–`D5`.** `infrastructure/browser.py` has no dependency on the download
transport, the stall bound, the process boundary or the redaction transform.

**The `D5` interaction, and why the two blocks stay separate — `S1i`.** `B15` also lands in
`BrowserManager.__aenter__`, so merging is tempting. **Not merged, because the verification shapes
differ and no test of one satisfies the other.** This block is an **information** fix: it re-scopes one
pinned test and adds three cases about what the raised message contains and that the Playwright banner
stays suppressed. Its anchors are the `except Exception:` arm and the raise statement. `B15` is a
**posture** fix: it adds a `Settings` field, gates two components, adds a conditional pre-driver check
and adds an ordering proof; its anchors are the launch args, `create_stealth_page`, `__aenter__`'s
entry, `Settings`, and eight documentation sites.

**Order: `B8` first (`E10`).** It is unconditional and independent, while `B15` changes the **default**
behaviour for every existing user under `D5`. Landing the information fix first means a revert of the
posture change leaves `B8` standing. `B15`'s prohibition 9 forbids it touching this block's anchors:
the `except` arm, its `exc_info=True`, its `from None`, and the `await playwright_instance.stop()`
before the raise.

**`B15` does NOT remove that hand-cleanup**, and this is worth stating because the two blocks are
adjacent: `B15`'s asset check goes **before** `async_playwright().start()`, where nothing needs
releasing, while this block's arm runs **after** the driver has started, where the cleanup is
load-bearing. Neither block may move the other across that boundary.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__aenter__` — the `except Exception:` arm's `raise ExtractionError("Failed to launch browser for video extraction") from None` | The message must carry the actionable content: the missing executable and the remedy, derived from the caught exception. `from None` is **kept** — it is what keeps the banner's box-drawing characters out of the displayed traceback, which is the second mechanism's whole point. |
| `src/vkdownloader/infrastructure/browser.py` | the same arm's `logger.error("browser_launch_failed", exc_info=True)` | **Read-only in this block.** Making this statement incapable of raising is `B16`'s subject and is gated. `B8` must **not** remove `exc_info=True`, and must not wrap the statement in a bare `try`. |
| `src/vkdownloader/infrastructure/browser.py` | the same arm's `await playwright_instance.stop()` | **Untouched.** Releasing the driver before raising is correct and is phase 04's `CON-005` territory. |
| `src/vkdownloader/infrastructure/browser.py` | `logger = get_logger(__name__)` | **structlog, not stdlib `logging`.** The remedy must be written against structlog's API. See §5.6 — following rule 12's text literally would break the renderer split. |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__aexit__` | **Untouched.** Plan 08 `B4` rewrote it; its six tests must stay green unchanged. |

**Tests required**

- **RE-SCOPE** `tests/test_browser_infrastructure.py::TestBrowserManager::test_browser_manager_launch_failure_raises_extraction_error`
  — it asserts `pytest.raises(ExtractionError, match="Failed to launch browser for video extraction")`,
  which **pins the message that names neither the binary nor the remedy**. It must be widened to the
  new text while **still asserting the application's own exception type reaches the caller** — that
  assertion is the finding's real content and must not be weakened away.
- **ADD** — the cause-content case: driven against a stand-in that raises an error whose message
  carries both the missing executable and the remedy, assert both reach the `ExtractionError`'s text.
- **ADD** — the suppression case: assert the displayed traceback does **not** contain the banner (i.e.
  `from None` was kept), so a future "fix" that drops `from None` to expose the cause is caught.
- **ADD** — a case where the caught exception's own message is uninformative: the block must state
  what the message looks like then. A remedy that produces an empty or uninformative string is worse
  than the current text.
- **MUST STAY GREEN UNCHANGED** the six plan-08 `B4` tests for `__aexit__`.

**Dependencies:** `depends_on: []`. Ordered before `B15` (same module, `C15`) and before `B16` (`C9`).

**Risk class: HIGH.** A HIGH finding, a user-facing error message, and a test pin that must be
re-scoped rather than deleted.

**Prohibitions (binding)**

1. **`from None` is kept.** The block carries the cause into the text; it does not expose the context.
2. **`exc_info=True` is not removed** from the log record, and the statement is **not** wrapped in a
   bare `try`/`except`.
3. `browser.py` gains **no new import** for the remedy beyond what it already has; if the exception's
   message must be normalised through a helper, that helper lives here and is module-private.
4. No stdlib `logging` import anywhere. **structlog only.**
5. `__aexit__` is **untouched**.
6. The block does **not** fix, claim, or close the encoding mechanism. Its report records the gap and
   points at `B16`.

**Commit shape.** One commit, subject naming the browser launch failure's lost cause, body carrying
the measured before/after (`__cause__`, `__suppress_context__`, and whether `playwright install`
appears in the surfaced text), and an explicit statement that the encoding mechanism remains open and
unowned.

#### §3.22 Decisions `B8`'s block Planner must make

**How much of the cause is carried, and in what shape.** Three options:

- **(a) Append the caught exception's message verbatim to the fixed text.** *Pro:* smallest; always
  accurate. *Con:* the Playwright message is the multi-line banner, so the surfaced text becomes
  multi-line and still contains the box-drawing characters — which puts `B16`'s hazard back on the
  console path this block exists to make safe. **Weakened.**
- **(b) Extract the two actionable elements** — the missing executable path and the install command —
  and append them to the fixed text as single-line fields. *Pro:* one line, no box-drawing characters,
  exactly the information the user needs. *Con:* needs a small module-private extraction helper and a
  decision about what to do when neither element is present.
- **(c) Replace the message entirely with the caught exception's text, prefixed by the application's
  own.** *Pro:* no extraction logic at all. *Con:* same box-drawing problem as (a).

→ **Recommended: (b)**, with an explicit fallback for the "neither element present" case, because
(a) and (c) reintroduce the very characters that cause the second mechanism. The block's Planner
confirms or overrules this with the measured content of a real Playwright error.

---

### B9 — Record that both chains are closed, and that phase 06's `SEC-004` is now doubly wrong

**Findings carried:** `phase05/VAL-501` (CRITICAL) + `phase05/VAL-502` (CRITICAL) — both
documentation findings against the audit inputs. **Re-scoped by `D2`.**

**Goal.** Record the outcome of both chains, and the fact that phase 06's `SEC-004` now asserts a
concealment **about a transport that no longer exists**.

**What changed under `D2`.** Revision 1 recorded two chains as **open**, and wrote a durable record
under `.ai/decisions/`. Both are now settled, and in opposite directions:

| Chain | Revision 1 | Now | Why |
|---|---|---|---|
| `phase05/VAL-502` **chain 2** — the shape of the `TRN-001` fix is a decision phase 06's `SEC-004` already owns | **OPEN** — the single hardest gate in the plan | **CLOSED** | `D2` answers it: the transport is deleted, not repaired. Recorded verbatim in §9. |
| `phase05/VAL-502` **chain 1** — `TRN-001` and `TRN-002` must land together | **OPEN**, satisfied by ordering (`B1` before `B10`) | **EVAPORATES** | The coupling existed because repairing one made the other worse. There is nothing left to couple: `TRN-001`'s subject is deleted, and `TRN-002` has been re-scoped to a different statement in a different module (§1.3 `S1b`). The ordering obligation is discharged by the deletion itself. |
| `phase05/VAL-501` — phase 06's `SEC-004` records `MET (argfile)` in two cells of its R5(d) table and its subject line claims the ffmpeg transport satisfies the stated intent | **OPEN** — "more clearly stale" | **MORE clearly stale** | Before `D2` the cells asserted a concealment that never worked. After `D2` they assert it **about a transport that does not exist**. The subject line names a deleted CLI option. Both errors are now unambiguous. |

**Where the record lives, and why it moved.** `.ai/audit/**` is **read-only** for this engagement, so the
correction itself still cannot be performed here. Revision 1 wrote a durable record under
`.ai/decisions/`; **Revision 2 keeps that** — a decision record is still the right artefact, and §9 in
this plan is its companion. The record must now state the **outcome** rather than the conflict.

**Why this is still a block and not a §1.5 deferral.** `phase05/VAL-501`'s correction cannot be performed here,
but a reader six months from now must be able to see **why** the transport is gone and **what** is now
wrong in phase 06. A decision that lives only in a commit message is a decision that gets lost.

**Semantic anchors owned**

| Path | Semantic unit | Change |
|---|---|---|
| `.ai/decisions/05-subprocess-browser-decision-record.md` | **one new file** | The durable record. `.ai/decisions/` exists and is **empty**, so nothing is overwritten. |
| `.ai/audit/06-credentials-secrets/findings.md`, `.ai/audit/99-validation/06-credentials-secrets-validated-findings.md` | — | **READ-ONLY. Not touched.** The record states what is wrong there and who owns the correction. |
| `.ai/audit/05-subprocess-browser/findings.md`, `.ai/audit/99-validation/05-subprocess-browser-validated-findings.md` | — | **READ-ONLY. Not touched, including this phase's own artifacts.** |
| this plan file, §9 | the decisions-taken record | The companion record, with the owner's words verbatim. |

**The record must contain, as discrete statements:**

1. **That both chains are closed**, with the dates and the owner's words (§9 `D1`, `D2`), and that
   chain 1 evaporated with the argfile rather than being satisfied by ordering.
2. **That `D2` deletes the transport**, not repairs it, and that the deletion is authorised as a
   breaking change: a script passing `--method ffmpeg` receives a usage error and a non-zero exit.
3. **That `phase05/VAL-501`'s correction is outstanding and belongs to phase 06**, stated precisely:
   replace both `MET (argfile)` cells; rewrite the subject line so it does not name a deleted
   transport; record `D1` as the reason the exposure argument no longer distinguishes the transports.
   **The record must not state what `SEC-004` should become** — that is phase 06's re-derivation.
4. **That `D1` retires the exposure argument**: on a single-user desktop the user can already read
   their own process list, so the concealment asymmetry between transports was never a security
   property in this deployment.
5. **`TRN-010`'s disposition**: moot with one transport, with its residue cross-referenced to phase
   06's `SEC-006` and marked moot for this deployment by `D1`.
6. **The console-encoding ownership gap** — still owned by no finding in any phase; phase 01 deferred
   encoding to phase 08 and phase 08 never filed it; **Q6 remains open**.
7. **Every correction this plan entered against the code context** (§1.7), so the next reader does not
   inherit them, and **the mojibake observation** about `cli-reference-clean.md` (§1.8), which is
   recorded as owned by no phase and deliberately not fixed here.

**Tests required:** none — prose. The gate is an **independent read** (§8.3).

**Dependencies:** `depends_on: []`. **Ordered with `B10`** — this is the only block whose content
depends on `B10` having been *decided*, which `D2` already has, so it does not wait for `B10` to
*land*. It is scheduled **last** among the unconditional blocks because its record is most accurate once
the deletion's exact shape is final.

**Risk class: LOW** (product) / **MEDIUM** (process — it is the only block that writes a file outside
`src/`, `tests/` and `docs/`).

**Prohibitions (binding)**

1. **No file under `.ai/audit/**` is created, edited, moved or deleted.** Phase 05's own artifacts
   included. The Validator proves this with `git diff --exit-code -- .ai/audit` and
   `git status --short -- .ai/audit`.
2. **No file under `.ai/plans/**` other than this plan file.**
3. Exactly **one** new file, under `.ai/decisions/`. Nothing is overwritten — the directory is empty.
4. The record **contains no verdict** on `SEC-004`, `SEC-005` or `SEC-006` — no "should be", no
   severity, no replacement wording. It states what is claimed, by whom, and who owns it.
5. **Every `VAL-` id in the record is qualified** as `phase05/VAL-NNN`.
6. No product code is touched. `git diff --exit-code -- src tests pyproject.toml` must be empty.
7. **MUST NOT** fix the `cli-reference-clean.md` mojibake. It is recorded, not fixed (§1.8).

**Commit shape.** One commit, subject naming the closed audit-artifact chains, body naming phase 06 as
the owner of the outstanding `SEC-004` correction, quoting `D2` and stating that `.ai/audit/**` was not
modified. Cited `phase05/VAL-501`, `phase05/VAL-502`.


### B10 — DELETE the ffmpeg download transport and everything that exists only to serve it

> **`D2` — DECIDED. This block is no longer `AWAITING DECISION`.** The owner's words: *"No you can
> delete it for now. If it will be needed we will add it in future."* Recorded with the others in §9.
> `phase05/VAL-502` chain 2 — "the shape of the `TRN-001` fix is a decision phase 06's `SEC-004`
> already owns" — is **closed by this decision**.

**Findings carried:** `TRN-001` (**CRITICAL**, now **disposed**) + `TRN-010` (**MEDIUM**, now **moot**)
— both `RUNTIME-ERROR` / `BEST-PRACTICE`.

**Goal.** `--method ffmpeg` must not exist. Today it exists, is documented, and executes **none** of
the transport the operator selected — the product writes every argument into a temporary file and
invokes `ffmpeg "@<path>"`, the installed muxer documents **neither** `@file` nor `-/opt`, so it takes
the token as a literal output filename, produces nothing, exits non-zero, and `perform_download`
silently substitutes segment download behind one INFO record naming the **fallback**, not the failure.
`D2` resolves the finding by **removing the feature**, which is the only repair that needs no
unmeasured mechanism.

**This is a deletion, and the rule for a deletion is subtraction.** The owner authorised a breaking
change. **Therefore:** no deprecation shim, no feature flag, no tombstone enum member, no "coming back
soon" note, no alias kept "for compatibility". `DownloadMethod.FFMPEG` is **removed outright** — a dead
enum member violates project rule 10, which requires every fixed value to be a live `StrEnum` member.
The `--method` flag itself stays; a script passing `--method ffmpeg` now receives Typer's own
invalid-choice error and exit `2`, which is the documented usage-error code.

**What is deleted — established against the live tree**

| Location | Deleted | Why it goes |
|---|---|---|
| `models/enums.py` | the `DownloadMethod.FFMPEG` member | No producer, no consumer, after the arm is gone. Rule 10. |
| `services/downloader.py` | `HLSDownloader` (the whole class) | Its only purpose is `download_with_ffmpeg`. |
| `services/downloader.py` | `_temp_argfile`, `_format_argfile` | Only ever produced the argfile the deleted spawn consumed. |
| `services/downloader.py` | the `case DownloadMethod.FFMPEG:` arm, including `_ffmpeg_progress_adapter` | The dispatch branch for the removed member. |
| `services/downloader.py` | the `FfmpegProgress`, `ProgressParser`, `read_progress` re-exports, their `__all__` entries and their lines in the symbol-ownership comment | These re-export the deleted stack. **Also a documentation obligation** (§5.2 item 6). |
| `services/ffmpeg_utils.py` | `read_progress`, `ProgressParser`, `FfmpegProgress`, `_ProgressHandler`, `_PROGRESS_KEY_HANDLERS` | The muxer's `-progress` stack, produced **only** by the deleted transport. Verified: `_build_ffmpeg_concat_command` passes **no** `-progress` argument, and the merge path reads its child with `process.communicate()`. |
| `src/vkdownloader/__init__.py` | `HLSDownloader` from `__all__` | **A public-API removal**, recorded in §5.5. |
| `cli.py` | the word `ffmpeg, ` from the `--method` help text, at **two** sites (`download` and `batch`) | Otherwise the CLI advertises a removed value. |
| seven documentation sites | see the table below | Same reason, plus `D2`'s own footprint. |

**What is preserved — established, and this list is binding**

| Preserved | Why |
|---|---|
| `--method` / `-m`, `DownloadMethod.YTDLP`, `DownloadMethod.AUTO` | The owner removed `--method ffmpeg`, not `--method`. Removing `AUTO` would change the CLI's **default**, which is a larger breaking change than was authorised. |
| `case _:` in `perform_download`'s dispatch, with its `unknown_download_method` record | It is the only handler for an unrecognised method, and `D-12 case 10` keeps it tested. **After the deletion it is load-bearing rather than defensive**, and must stay. |
| `check_ffmpeg_available` and its **single bare call** in `perform_download` | Still live: a yt-dlp or auto download can reach `download_hls_with_resume` -> `_merge_segments_batched` -> `_merge_batch_segments` / `_perform_final_merge`, and **segment merging still needs the muxer**. Discarding the answer is `B13`'s subject, not this block's — and this block must not start branching on it. |
| `iter_process_lines`, `cancel_subprocess` / `cancel_ffmpeg_process`, `_await_ffmpeg_with_timeout`, `_check_merge_space`, `_merge_segments_batched`, `_merge_batch_segments`, `_perform_final_merge`, `_build_ffmpeg_concat_command`, `_required_merge_bytes` | The merge transport. **Two** of `iter_process_lines`' three consumers are deleted; the other two are in `ytdlp_downloader.py` and survive. |
| `sanitize_text_for_log`, `_strip_auth_params`, `sanitize_url_for_log` | Shared by the yt-dlp transport and the merge sinks. |
| **every dependency in `pyproject.toml`** | Established by reading the dependency block: `playwright` (stealth, now a hard requirement under `D4`), `aiohttp` (segment downloader), `yt-dlp` (surviving transport), `pydantic`, `pydantic-settings`, `typer`, `rich`, `structlog`, `python-dotenv` — all keep their consumers. **The ffmpeg download path used no dependency the merge path does not. This block edits no dependency.** |
| `artifacts = ["src/vkdownloader/stealth.min.js"]` | Unrelated, and **more** load-bearing under `D4`. |

**`--method auto` after the deletion — established, because the arm's own comment becomes a lie.**
`DownloadMethod.AUTO` and `DownloadMethod.YTDLP` now resolve to the **same transport**:
`download_with_ytdlp_with_resume_fallback`. The single difference is that `AUTO` skips
`_resolve_cookies` when `settings.cookie_source == CookieSource.NONE`, while `YTDLP` always resolves.
So, precisely:

> **`--method auto` means: resolve cookies according to `cookie_source` — skipping browser resolution
> when it is `none` — then download via yt-dlp with segment-level resume as the fallback.**

Its arm comment today reads *"Auto: try yt-dlp first (more reliable), segment download for resume"*.
That sentence names a **two-transport choice that no longer exists**: there is no "first", and there
is nothing to try before anything else. **Correcting that comment is part of this block**, and it is
the same obligation as §5.2 item 6 — a decision-carrying comment that outlived its decision.

**The seven documentation sites** (`B10` owns all seven):

| Site | What must change |
|---|---|
| `README.md` | the `--method ffmpeg` worked example |
| `docs/99-reference/cli-reference.md` | the `--method` option row's value list, and the worked `--method ffmpeg` example |
| `docs/99-reference/cli-reference-clean.md` | **the same two, in a mojibake copy of the above** — established in §1.8: not a separate page, not an exact duplicate, the same document with every non-ASCII character mis-decoded, linked from exactly one research document, no `mkdocs.yml` to reconcile. **Its encoding is not this plan's defect and is not fixed here**; only its `--method` rows are corrected, because leaving a page advertising a deleted CLI option is worse. |
| `docs/01-tools/api-reference.md` | the assertion that the argv is **only** `['ffmpeg', '@<argfile>']` — and the surrounding `download_with_ffmpeg` prose, since the method is gone |
| `docs/01-tools/quality-selection.md` | the transport table's ffmpeg row and two `--method ffmpeg` worked examples |
| `docs/01-tools/vkdownloader-overview.md` | "**Secret-safe ffmpeg argument passing**: ... passed to ffmpeg via a temporary argument file (`ffmpeg @argfile`) instead of command-line arguments. This prevents session tokens and CDN URL signatures from leaking into process listings ... The tokens are absent from process listings on both platforms" — the strongest single claim in the corpus, false today, and about a transport that is about to stop existing |
| `docs/11-guides/vkdownloader-limitations.md` | the same claim plus the `--method ffmpeg` workaround row |

**Tests required**

- **DELETE, in the same change** — eight `DownloadMethod.FFMPEG` references across two files
  (`test_downloader.py`'s **D-12 cases 5, 6 and 7** — the success path, the failure-falls-back path and
  the failure-with-shutdown-set path — and `test_hls_downloader.py`'s `TestDownloadMethodLogging`
  cases). Under rule 2 these go with the code they describe; they are not weakened.
- **DELETE, in the same change** — every test class and case that exercises a deleted symbol:
  `TestHLSDownloaderDownload`, `TestTempArgfile` (including the three `test_format_argfile_*` cases),
  `TestFfmpegCookiePassing`, `TestReadProgress`, `TestProgressParser`, `TestFfmpegProgress`.
- **MUST STAY GREEN UNCHANGED** — `test_cli.py`'s `--method invalid_method` case: it proves the CLI's
  invalid-choice error and exit `2`, which is exactly what `--method ffmpeg` must now produce, and it
  becomes the **proof that the breaking change is clean**.
- **MUST STAY GREEN UNCHANGED** — `test_downloader.py`'s **D-12 case 10** (an unrecognised method
  returns `None` with the `unknown_download_method` record). It is the test that keeps `case _:`
  honest after the deletion.
- **MUST STAY GREEN UNCHANGED** — `::TestFfmpegAvailabilityCheck` in full: `check_ffmpeg_available`
  survives for the merge path and this block must not disturb it.
- **ADD** — the removal's own proof: `--method ffmpeg` is rejected by the parser with a non-zero exit
  and a message that does not offer `ffmpeg` as a choice. Assert on the exit code and on the absence of
  `ffmpeg` in the help text, **not** on the exact message wording.
- **ADD** — the `AUTO` semantics assertion Revision 1 never needed: `auto` reaches
  `download_with_ytdlp_with_resume_fallback` and skips `_resolve_cookies` when `cookie_source == NONE`.
  It is already covered by D-12 cases 1-3; **that coverage must survive the deletion unchanged** and
  the report must say so rather than adding a duplicate.

**Dependencies:** `depends_on: []`. **Blocks `B5` (`E2`)** — it deletes four of that block's six call
sites — and `B4` (`E3`), which no longer extends a deleted table. **`B1` and `B9` no longer depend on
it**: `phase05/VAL-502` chain 1 evaporated (§1.3 `S1b`, `S1e`), so `B1`'s old "must precede `B10`"
edge is gone, and `B9` needs only the decision, not the landing.

**Risk class: HIGH.** A large mechanical deletion across four `src/` modules, the package root, seven
documentation sites and two test files. Nothing here is technically uncertain; everything here is
**breadth**, and breadth is where an unreviewed commit loses a live symbol.

**Prohibitions (binding)**

1. **MUST NOT** add a deprecation shim, a feature flag, a tombstone enum member, an alias, or any
   "coming back soon" note. The owner said it can be re-added later **if needed**.
2. **MUST NOT** keep `DownloadMethod.FFMPEG` "for one release". Remove it outright; the CLI's existing
   invalid-choice error is the whole of the migration story.
3. **MUST NOT** touch anything in the preservation table above. In particular **MUST NOT** delete
   `check_ffmpeg_available`, its bare call, `iter_process_lines`, `cancel_subprocess`, or any merge
   helper; and **MUST NOT** branch on `check_ffmpeg_available`'s answer — that is `B13`'s.
4. **MUST NOT** leave the `AUTO` arm's "try yt-dlp first" comment in place. It is now false.
5. **MUST NOT** fix the `cli-reference-clean.md` mojibake. Only its `--method` rows are in scope.
6. **MUST NOT** edit any dependency in `pyproject.toml`, and **MUST NOT** remove the
   `stealth.min.js` artefact declaration.
7. **MUST NOT** delete a test in a separate commit from the code it tests. Rule 2: they travel together.
8. **MUST NOT** leave a re-export line in `downloader.py`'s `__all__` or symbol-ownership comment
   pointing at a deleted symbol.
9. The exit codes stay `130` / `1` / `2`. `--method ffmpeg` now produces `2`, which is already
   documented.

**Commit shape.** One commit, subject naming the removal of the ffmpeg download transport, body
carrying: the enumerated deletion list; the preservation list; the **`auto` semantics statement** from
above; the seven documentation files touched; the deleted and retained test classes; and the explicit
statement that this is the answer to `TRN-001`, that `TRN-010` is moot with one transport left, and
that phase 06's `SEC-004` must be re-adjudicated because it now describes a transport that no longer
exists. Cited `TRN-001`, `TRN-010`, `phase05/VAL-502`.


### B11 — Bound the stall at the transport's surviving re-wait

> **`D3` — DECIDED. This block is no longer `AWAITING DECISION`.** The bound exists, its default is
> `300.0`, it is configurable, and it is an **inactivity** bound. Recorded in §9.

**Findings carried:** `TRN-007` — **MEDIUM** · `BEST-PRACTICE` · **mandatory**.

**Goal.** `if process.returncode is None: await process.wait()` carries no bound, and it is the only
thing that can release a child once the reader has stopped.

**`D3` settles the policy question Revision 1 escalated — and settles it in the way that preserves the
documented decision.** The bound is an **inactivity** bound: no output for N seconds. It is therefore
**not** a whole-operation budget, so:

- **`NET-007`'s withdrawn whole-operation budget stays withdrawn.** Phase 03 withdrew it; `D3` did not
  reinstate it.
- **`_download_with_ytdlp`'s "no application-level download timeout is imposed, avoiding premature
  kill of legitimate long downloads" sentence does NOT need reversing.** This is a correction to
  Revision 1, which assumed the sentence would have to change and gated the block on `Q2`. It does not.
  The sentence stays true: a download that keeps producing output is never killed, no matter how long
  it runs. What changes is that a download that has gone **silent** is killed, and the docstring must
  say so — an amendment, not a reversal.

**Re-scoped by `D2`: two re-wait sites become one.** `download_with_ffmpeg`'s
`if process.returncode is None: await process.wait()` is deleted. The surviving site is
`_download_with_ytdlp`'s — and it is now the **only** unbounded completion wait in the product.

**The setting — fixed by `D3` and by this plan**

| Property | Value | Why |
|---|---|---|
| **Name** | `download_stall_timeout` | It bounds a **stall**, not a download. `download_timeout` already exists and means something else; a similar name would collide in `.env.example` and in operator memory. |
| **Default** | `300.0` | `D3`. Equals `download_timeout`'s own default on this machine, which keeps the two bounds comparable without making them the same bound. |
| **Bounds** | `ge=30`, `le=3600` | `D3`, mirroring `download_timeout` exactly. 30 s is below any legitimate inter-chunk gap on a healthy connection; 3600 s is an hour of total silence. |
| **Type** | `float` | `D3` gives `300.0`. `download_timeout` is `int`; a stall bound measured in seconds is more naturally a float, and the user asked for `300.0`. The asymmetry is deliberate and recorded here so no block "corrects" it. |
| **Home** | `Settings`, in `config.py`, adjacent to `download_timeout` | One concept, one place. |
| **Field description** | Must state, in its own words: it bounds the **inactivity** of a download's output stream — the wait after the child's output has been consumed — that on expiry the child is **terminated through the existing ladder** and the exception is **re-raised**; that it is **not** a whole-operation budget and a download that keeps producing output is never killed; and that it does **not** apply to the merge subprocesses, which `download_timeout` already bounds. | Rule 7 and rule 14. The description is the only place an operator can learn this, and getting it wrong reintroduces the exact confusion `NET-007` resolved. |
| **Three-place rule** | field description + a commented row in `.env.example` + the `download_timeout`-adjacent table in `docs/11-guides/configuration.md` | Rule 11. `model_config`'s `extra="forbid"` makes an unrecognised `VKDOWNLOADER_*` an error, so an `.env.example` value the model rejects, or a documented variable the model has never heard of, is a correctness bug. |
| **The `.env.example` value** | Must be **constructed against `Settings`** and the construction recorded in the block report | Phase 02 found a shipped `.env.example` value the model rejects. Do not repeat it. |

**The in-repo pattern to copy, pinned exactly.** `services/ffmpeg_utils.py` ->
`_await_ffmpeg_with_timeout`, signature `(process, timeout: float)` with **no default** so the bound
cannot be forgotten; it wraps `process.communicate()` in `asyncio.wait_for(..., timeout=timeout)`; its
`except (TimeoutError, asyncio.CancelledError):` arm re-enters `cancel_ffmpeg_process` and
**re-raises**; both its callers pass `download_timeout` from `Settings`. **A new helper must have the
same shape**: a mandatory `timeout` parameter and the re-raise arm. A bare `asyncio.wait_for` around
`process.wait()` is **prohibited** — it would leave the child unreaped, which is the defect class `B1`
and `B5` exist to close.

**Why an inactivity bound rather than `asyncio.wait_for(process.communicate(), ...)`.** The helper
template drains both pipes in one call, and this block's bound is on the **re-wait** — the wait that
follows the reader's consumption of the stream — not on the drain. The reader is a separate task
(`B2`, `B4`); folding it into `communicate()` would collapse the progress reporting and the
cancellation structure the reader owns. So the bound wraps the **wait**, not the drain, and the
inactivity semantics are implemented by the reader's continued liveness resetting the clock — which the
block must state precisely, because "inactivity" has no meaning unless something is measuring it.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — the `if process.returncode is None: await process.wait()` pair and the comment above it | The defect, and the **only** surviving instance. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp`'s docstring — the "no application-level download timeout is imposed, avoiding premature kill of legitimate long downloads" sentence | **Amended, not reversed.** It gains the stall bound's existence and its inactivity semantics; it does not lose its claim. |
| `config.py` | `Settings.download_stall_timeout` — a new `float` field with `default=300.0`, `ge=30`, `le=3600` and the description above | The setting `D3` fixed. |
| `config.py` | `Settings.download_timeout`'s `Field(description=...)` | **Amended only to cross-reference** the new field, so an operator reading one learns the other exists. Its own claimed boundary — segment/playlist HTTP requests, each ffmpeg merge subprocess, the off-loop extraction's `wait_for`, yt-dlp's socket timeout — is **unchanged** and still does not claim the transports. |
| `services/ffmpeg_utils.py` | `_await_ffmpeg_with_timeout` | **The template. Read-only.** A new helper may share its shape; the merge subprocesses are **not** re-bounded by this block. |
| `docs/11-guides/configuration.md` | the `download_timeout` row | **NOT this block's.** Plan 07's `C12` owns that row. This block **adds** a new row beside it and edits no existing row (`C12`). |
| `.env.example` | the commented `VKDOWNLOADER_DOWNLOAD_TIMEOUT` row | A new commented row is added **beside** it. The existing row is untouched. |
| `services/downloader.py` | `download_with_ffmpeg`'s re-wait | **DELETED by `B10`.** |

**Tests required**

- **ADD** — the stall case: a child that emits its output and then goes silent. Under the bound the
  call **returns within it** AND the child is **reaped**. Assert both halves — a timeout that leaves
  the child running is the failure this block must not ship.
- **ADD** — the liveness case, which is what makes "inactivity" real: a child that keeps emitting
  output **does not** trip the bound, no matter how long it runs. This is the test that proves
  `NET-007`'s decision is preserved and not quietly reversed. Without it, a total-time bound would
  pass the whole suite.
- **ADD** — the cancellation arm: cancelling the holder still propagates `CancelledError` **and** the
  termination ladder still runs. `_await_ffmpeg_with_timeout` guarantees both; the new helper must too.
- **ADD** — the setting: the default constructs against `Settings`; the documented `.env.example`
  value constructs against `Settings`; `ge=30` and `le=3600` reject out-of-range values.
- **MUST STAY GREEN UNCHANGED** `::TestYtDlpSubprocessShutdown` and the yt-dlp drain trio.

**Dependencies:** `depends_on: []`. **Reviewed after `B2` and `B4`** (`E5`) — those close the routes
that leave the reader stopped, and this block's report must say which routes remained when it ran.
Shares `_download_with_ytdlp` with `B6` (`C13`).

**Risk class: MEDIUM**, with a **policy** dimension. The product question is settled; what remains is
implementing an inactivity bound correctly, which means deciding what counts as liveness.

**Prohibitions (binding)**

1. **MUST NOT** introduce a whole-operation budget. `NET-007`'s withdrawal stands and `D3` preserved it.
2. **MUST NOT** reverse `_download_with_ytdlp`'s no-timeout sentence — only amend it.
3. A bound **MUST** use `_await_ffmpeg_with_timeout`'s shape: a mandatory `timeout: float` parameter
   with **no default**, and an `except (TimeoutError, asyncio.CancelledError)` arm that re-enters the
   ladder and **re-raises**. A bare `asyncio.wait_for` around `process.wait()` is **prohibited**.
4. **MUST NOT** re-bound the merge subprocesses. `download_timeout` already bounds them, and this is a
   different concept.
5. **MUST NOT** edit the `download_timeout` row in `docs/11-guides/configuration.md` (plan 07 `C12`).
6. `ffmpeg_utils.py` gains **no import**.
7. The new field is the **only** `Settings` field this plan adds, and it must satisfy the three-place
   rule exactly. No second knob, no alias.
8. **MUST NOT** change the `--method` surface or touch `B10`'s deletion.

**Commit shape.** One commit, subject naming the stall bound, body carrying: the chosen shape; the
measured before/after (a child that emits then stalls: before -> unbounded; after -> the configured
bound); the **liveness** measurement proving a continuously-emitting child is never killed; the
amended decision sentence quoted before and after; the three places the setting is written and the
`Settings` construction for each value; and the explicit statement that `NET-007` is **preserved**,
not reinstated. Cited `TRN-007`.


### B12 — Establish a process boundary: the minimum platform keyword, with the Windows residual documented

> **`D1` plus the standing Tech Lead decision — DECIDED. This block is no longer
> `D6` — DECIDED (Tech Lead). This block is no longer `AWAITING DECISION`.

**Findings carried:** `TRN-003` — **HIGH** · `BEST-PRACTICE` · **mandatory**.

**Goal.** A process the child creates for itself must not outlive the command, to the extent the
chosen mechanism delivers that on each platform.

**The measured absence, unchanged by `D2`.** A search over `src/` for `start_new_session`, `setsid`,
`process_group`, `creationflags`, `startupinfo`, `CREATE_NEW_PROCESS_GROUP`,
`CREATE_BREAKAWAY_FROM_JOB`, `JobObject`, `AssignProcessToJobObject` and `taskkill` returns **no API
usage anywhere**. `env=` and `cwd=` are absent from every spawn. The termination ladder addresses
`process.pid` and nothing else — no `pgid`, no `killpg`, no tree walk. The reproduction stands: a stub
child that spawns a process of its own, then the product's own `cancel_subprocess` on the direct child,
gives `direct_alive=False grandchild_alive=True` with the call reporting success.

**The decision, and what `D1` changed about it.** The remedy is the **minimum platform-appropriate
keyword per spawn** — `start_new_session=True` on POSIX (which creates a session and makes `killpg`
possible, so descendants are reachable) and `creationflags=CREATE_NEW_PROCESS_GROUP` on Windows, with a
matching `os.killpg` branch in `cancel_subprocess`. **A Windows Job Object with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` is rejected**: it is the only option that fully closes the finding
on Windows, and it costs a `ctypes`/pywin32 wrapper, a platform guard, a handle lifecycle that is not a
small thing to get wrong, and a relaxation of the packaging gate for a new `src/` module — against
project rule 5 at this project's scale. A descendant sweep is rejected outright: it replaces a
structural defect with a timing-dependent one and shells out to `taskkill` to fix a process-management
defect.

**`D1` is the reason the Windows residual is acceptable, and this is the honest statement of it.** On a
single-user desktop there is no shared host, no container and no CI: a surviving orphan holds a file
open **on the user's own machine**, where the user can see it, and the direct child — which holds the
credential material — is killed either way. `CREATE_NEW_PROCESS_GROUP` gives a new process group, but
**a new process group is not a killable tree by pid**, so on Windows a grandchild can still outlive the
command. That residual is **documented, not hidden**: the limitations guide states it, the commit body
states it, and the test asserts what happens on Windows specifically.

**Re-scoped by `D2`: four spawn sites become three** — `download_with_ffmpeg`'s is deleted. The three
survivors are `_merge_batch_segments`, `_perform_final_merge` and `_download_with_ytdlp`. The yt-dlp
child is now the **only** transport, so a boundary gap there has no sibling transport to hide behind —
`D2` makes the structural point sharper, not weaker.

**The correction the validator entered, binding on this block's wording.** The named failure scenario
("the muxer that yt-dlp started to merge the streams") is **contingent**: the vector passes
`--hls-prefer-native`, which steers yt-dlp to its own HLS downloader. The flag is accepted by the
installed `yt-dlp 2026.07.04` though absent from its `--help`. The **structural** defect and the
reproduction are unaffected. The commit body must state the conditional form.

**Why not CRITICAL, in the finding's own words.** The process that holds the credential material is the
**direct** child — `--cookies` is passed to yt-dlp, and that one is killed. The surviving descendant
holds an output file open and nobody can address it.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ffmpeg_utils.py` | `cancel_subprocess` — the `process.terminate()` call and the ladder around it | The only thing that addresses a pid. This is where the tree-wide signal belongs. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp`'s `asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=STDOUT)` call | Spawn site 1 — and the one the reproduction drove. |
| `services/ffmpeg_utils.py` | `_merge_batch_segments`'s and `_perform_final_merge`'s `asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)` calls | Spawn sites 2 and 3, both already inside the bounded `_await_ffmpeg_with_timeout` path. |
| `services/downloader.py` | `download_with_ffmpeg`'s `asyncio.create_subprocess_exec(*cmd, stdout=DEVNULL, stderr=PIPE)` call | **DELETED by `B10`.** |
| `services/ytdlp_downloader.py` | the new `os.killpg` branch in the ladder, POSIX only | The signal that makes the POSIX session useful. It must be guarded by a platform check, and the guard must be stated rather than assumed. |
| `infrastructure/browser.py` | `BrowserManager.__aenter__`'s `async_playwright().start()` and `self.playwright.chromium.launch(...)` | **Library-mediated and out of reach.** Their boundary arguments come from Playwright, not from this codebase. The finding names them; **this block records that they cannot be bounded here** and does not pretend otherwise. |
| `docs/11-guides/vkdownloader-limitations.md` | the limitations entry | **Where the Windows residual is documented.** This is a block obligation, not an optional edit. |

**Tests required**

- **ADD** — the descendant case, which is the finding's own reproduction: a stand-in child that spawns
  a process of its own; after the ladder runs, assert the **descendant is gone**. The test must **first
  assert the stand-in really did spawned something** — a test that passes because the child never
  spawned is not a test.
- **ADD** — the platform-asymmetry case: assert what happens on **Windows** specifically, so the
  partial closure is visible in the suite and not only in a comment. On Windows this test asserts that
  the grandchild **survives**; that is the honest outcome under this decision, and a test that quietly
  asserted otherwise would be a lie.
- **MUST STAY GREEN UNCHANGED** `tests/test_ffmpeg_utils.py::TestCancelSubprocess` in full —
  `test_returns_false_on_process_lookup_error`, `test_terminate_on_success`, `test_kill_on_timeout`,
  `test_backward_compatible_alias` — plus `::TestYtDlpSubprocessShutdown` and the yt-dlp drain trio.

**Dependencies:** `depends_on: [B5]` (`E6`). `B5` edits the surviving `cancel_subprocess` guards and
the ladder's documented contract; two blocks rewriting `cancel_subprocess`'s neighbourhood in the same
review is how one of them gets reverted.

**Risk class: HIGH** (finding), with the scope now **settled** — which removes the plan's largest open
question about this block and leaves only the implementation.

**Prohibitions (binding)**

1. **MUST NOT** introduce a Job Object, `CREATE_BREAKAWAY_FROM_JOB`, a descendant sweep, or a
   `taskkill` shell-out. All three were considered and rejected; §3's option table records why.
2. `cancel_subprocess`'s **signature, keyword-only `timeout`, and return contract are `B5`'s** and are
   untouched here.
3. **MUST NOT** modify the two Playwright-mediated launches, and **no test may assert they are
   bounded.**
4. **MUST NOT** introduce `env=` or `cwd=`. That half of `TRN-010` is measured **closed**, is moot
   under `D2`, and is not re-opened.
5. **MUST NOT** pass `limit=` at any spawn site — that is `B2`'s neighbourhood and `B2`'s prohibition 7
   forbids it here.
6. `ffmpeg_utils.py` gains **no import** beyond the platform-guarded `os.killpg` path, which needs only
   the already-imported `os`.
7. **MUST NOT** present the Windows outcome as a closure. The commit body and the limitations entry
   must both state the residual, and `D1` must be given as the reason it is acceptable.
8. The commit body states the failure scenario's **conditional** form (`--hls-prefer-native`), not the
   unconditional one the source report used.

**Commit shape.** One commit, subject naming the process boundary, body carrying: the chosen mechanism
per platform; the rejected options and why; the measured before/after (descendant alive after the
ladder: before -> `True`; after -> `False` on POSIX, still `True` on Windows); the explicit Windows
residual with `D1` as its justification; and the conditional-form statement. Cited `TRN-003`.


### B13 — Stop discarding the availability answer, and stop one absence surfacing three ways

> **`D6` — DECIDED (Tech Lead). Option (B), better degradation. This block is no longer
> `D6` — DECIDED (Tech Lead). This block is no longer `AWAITING DECISION`.

**Findings carried:** `TRN-008` — **MEDIUM** · `BEST-PRACTICE` · **mandatory**.

**Goal.** `check_ffmpeg_available` has exactly **one** call site in `src/` — the bare expression
statement in `perform_download` — and its return value is dropped. No branch anywhere depends on it.
The answer is cached write-once with no re-derivation and no invalidation hook, so a machine that loses
the muxer mid-session keeps the cached `True` and emits nothing. And one absence surfaces **three**
different ways.

**Re-derived after `D2`: four arms become three.** Revision 1 enumerated four surfacings; one of them
lived in the transport that `D2` deletes.

| Arm | Where | After `D2` |
|---|---|---|
| **(a) muxer download** | `services/downloader.py` -> `download_with_ffmpeg`'s `except OSError` arm | **DELETED with the method.** Its record was `ffmpeg_download_failed`, followed by `perform_download`'s silent substitution. |
| **(b) merge** | `services/ffmpeg_utils.py` -> `_merge_batch_segments` and `_perform_final_merge` | **SURVIVES, and is now the sharpest arm.** There is still **no `OSError` arm** around `await _await_ffmpeg_with_timeout(...)`, so the merge's raw `FileNotFoundError` escapes uncaught and produces **no product record at all** — which is exactly what `check_ffmpeg_available`'s own hint text ("segment merge will fail") predicts, delivered as an uncaught exception. |
| **(c) downloader** | `services/ytdlp_downloader.py` -> `_download_with_ytdlp`'s `except FileNotFoundError:` arm | **SURVIVES.** Logs **`ytdlp_not_found`** — *not* `download_failed`, and there is **no** `ModuleNotFoundError` arm anywhere in the module. A missing *module* surfaces as the child's non-zero exit through the ordinary `returncode != 0` arm. (§1.7 item 1 corrects both the code context and the artifact here.) |
| **(d) resume** | `services/ytdlp_downloader.py` -> `_attempt_segment_resume`'s `except (ExtractionError, OSError) as e:` arm | **SURVIVES.** Catches the merge's `FileNotFoundError` — an `OSError` — and logs it as **`failed_to_refresh_token`**, a token problem the operator will act on in the wrong direction. `QualityParseError` is a sibling of `ExtractionError` under `VKDownloadError`, not a subclass, so both arms remain reachable. |

**`check_ffmpeg_available` is still live and still correctly placed.** `D2` removes a consumer of the
probe, not the probe's reason to exist: a yt-dlp or auto download still reaches
`download_with_ytdlp_with_resume_fallback` -> `download_hls_with_resume` -> `_merge_segments_batched`
-> the merge helpers, and **segment merging still needs the muxer**.

**`D6`'s decision and its reason, recorded.** Option **(B), better degradation** — **not** a hard
failure. The reason is `D2`: with the explicit ffmpeg transport deleted there is no longer a
user-selected transport to violate, so a hard failure would break **every HLS download** on a
muxer-less machine for no user benefit. `D6` therefore requires four things and forbids a fifth:

| | Requirement | Why |
|---|---|---|
| 1 | **Emit ONE actionable warning naming the install step**, following the `check_ffmpeg_available` convention — a single `logger.warning(<event>, hint=...)` whose `hint` names what is missing and what will fail | The probe already emits such a warning on first derivation. The finding is that it is a warning **and nothing else** — the answer is discarded, so no later surfacing is coherent. One place, one message. |
| 2 | **USE the probe's answer at its single call site** instead of discarding it | **This is the finding's structural core.** The bare expression statement becomes a bound value that the call site's warning path consults. |
| 3 | **Stop `except (ExtractionError, OSError)` reporting a missing muxer as `failed_to_refresh_token`** — **mandatory under any option**, and in scope | Reporting a missing binary as a token problem sends the operator to act in the wrong direction. It is wrong regardless of which degradation shape is chosen. |
| 4 | **Give arm (b) a product record** so the merge's escaping `FileNotFoundError` stops being the only surfacing that produces nothing | With (a) gone, (b) is the last arm with no record at all. |
| ✗ | **NO exit-code change** | A hard failure would break every HLS download on a muxer-less machine for no user benefit. `D6` is explicit. |

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ffmpeg_utils.py` | `check_ffmpeg_available` — the module global `_ffmpeg_available` and the guard `if _ffmpeg_available is None:` | The write-once cache. The `ffmpeg_not_found` warning is emitted **only** on the first derivation, so a later absence is silent. Whether the block adds an invalidation path or leaves the cache alone is **not** decided by `D6` — the block's Planner chooses, and the report says which. |
| `services/downloader.py` | `HLSDownloader.perform_download` — the bare `check_ffmpeg_available()` statement, with its comment | **The discarded answer, and the only consumer.** Under `D6` the return value becomes load-bearing here for the first time: it feeds the warning path, and it does **not** gate progress. |
| `services/ffmpeg_utils.py` | `_merge_batch_segments` and `_perform_final_merge` — the absence of an `OSError` arm around `await _await_ffmpeg_with_timeout(...)` | **Arm (b).** Requirement 4. Note `_check_merge_space` already has its own `except OSError` arms: the merge **space probe** is handled, the merge **spawn** is not. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` — the `except FileNotFoundError:` arm logging `ytdlp_not_found` | **Arm (c).** Already structured and actionable; the block reconciles it with the single warning place so the install step is named once, consistently. |
| `services/ytdlp_downloader.py` | `_attempt_segment_resume` — the `except (ExtractionError, OSError) as e:` arm logging `failed_to_refresh_token` | **Arm (d).** Requirement 3. Must be narrowed so a `FileNotFoundError` is reported as the missing dependency it is. `QualityParseError` must keep reaching its own arm. |

**Tests required**

- **ADD** — **arm (b), which no test covers today and which is now the most valuable single test in the
  block**: the merge path with no muxer produces **one** actionable record naming the install step,
  instead of an escaping exception. Assert the record names the binary and the consequence.
- **ADD** — arm (d): a `FileNotFoundError` from the merge is **not** logged as
  `failed_to_refresh_token`, and a genuine `ExtractionError` **still is**.
- **ADD** — arm (c): the `FileNotFoundError` arm's record names the missing binary.
- **ADD** — the probe's answer is used: with the probe forced to `False`, the call site emits exactly
  **one** warning and **does not** raise and **does not** change the exit code. The "does not change
  the exit code" half is `D6`'s explicit instruction and must be asserted, not assumed.
- **ADD** — the cache: assert the chosen cache behaviour (write-once preserved, or re-derived on
  demand) and that a **second** absence is not silent under whichever shape the Planner chooses.
- **MUST STAY GREEN UNCHANGED** `::TestFfmpegAvailabilityCheck` in full — including
  `test_check_ffmpeg_available_caches_result`, which pins the write-once cache. It is re-scoped
  **only** if the block adds an invalidation path; if the block leaves the cache alone it stays green
  **unchanged**, and the report says which.
- **DELETED by `B10`**: Revision 1 added an arm-(a) test. **It does not exist** — the method it drove
  is gone, so that obligation is discharged by the deletion rather than by a test.

**Dependencies:** `depends_on: [B10]` (`E2`) — the arm enumeration must be re-derived against the
landed tree, and its result is **three** arms, not four.

**Risk class: MEDIUM.** Three call sites in two modules, the sharpest of them untested, and one
instruction (`D6`) that a well-meaning Implementor could over-apply into a hard failure.

**Prohibitions (binding)**

1. **MUST NOT** hard-fail. No branch on the probe's answer may raise, return early, or change an exit
   code. `D6` is explicit that a hard failure would break every HLS download on a muxer-less machine.
2. The `_attempt_segment_resume` narrowing is **mandatory** and is not optional under any reading.
3. **MUST NOT** edit `download_with_ffmpeg` or add an arm-(a) test — that transport is deleted.
4. **MUST NOT** add a `Settings` field, an environment variable or a CLI option. The availability probe
   is not a setting, and `D3`'s `download_stall_timeout` is unrelated.
5. **MUST NOT** emit more than one warning for one absence. "One actionable warning" is `D6`'s wording
   and the point of the change.
6. `shutil.which` is not replaced and no allow-list of executables is introduced.
7. `check_ffmpeg_available`'s existing `ffmpeg_not_found` **hint text** must stay accurate — it
   predicts "segment merge will fail", which is exactly what arm (b) does, so if the block gives arm
   (b) a record the hint must be reconciled with it. **Reuse its shape** — `logger.warning(<event>,
   hint=(<what is missing>; <what will fail>))` — rather than inventing a message convention.
8. Arm (d)'s `QualityParseError` arm stays reachable; the two arms may not be merged.

**Commit shape.** One commit, subject naming the availability probe, body carrying the chosen cache
shape; the **three** surviving arms before and after with their records; the explicit statement that
arm (a) was deleted with the transport; the explicit statement that the probe's answer is now **used**
at its single call site; and `D6`'s instruction that **no exit code changes** — with the measured
evidence for it. Cited `TRN-008`, `D6`.

### B15 — Gate the stealth posture behind `stealth_enabled`, and hard-fail only when it is explicitly enabled and the asset is missing

> **`D5` — DECIDED (Product Owner). This supersedes `D4`'s unconditional hard failure.**
> The owner, verbatim: *"я бы хотел, чтобы скачивающий сам решал нужен stealth или нет. Т.е. это должно
> быть configurable по умолчанию отключено."* — *"I would like the downloader itself to decide whether
> stealth is needed. That is, it should be configurable, disabled by default."*

**Findings carried:** `BRW-003` **re-scoped** — **MEDIUM** (retained per the validator's authority;
risk class HIGH below) · `RUNTIME-ERROR` · **mandatory**.

**Goal.** Stealth becomes the user's choice, exposed as configuration, **off by default**; and when the
user turns it on, an absent asset is an immediate error rather than a late confusion.

**`BRW-003` was "the asset's absence is silent at every log level." `D5` splits it in two, and the two
halves now behave differently:**

| Condition | Behaviour | Why |
|---|---|---|
| **`stealth_enabled` is `False` (the default)** | **Nothing consults the asset.** No check, no warning, no failure. | **The finding's original form dissolves.** Silence about an asset that was never asked for is not a defect. `create_stealth_page`'s injection branch is simply not taken. |
| **`stealth_enabled` is `True` and the asset is present** | Injection proceeds as today. | The posture the user asked for is delivered. |
| **`stealth_enabled` is `True` and the asset is missing** | **HARD FAILURE**, before the driver starts, message naming the path and the remedy. | The user asked for stealth and cannot have it. Extraction will fail downstream anyway, so failing fast at the cheapest point is strictly better than a confusing late failure — and `D5` makes the failure **conditional on an explicit opt-in**, so the user who gets it is one who asked for it. |

**What the stealth posture actually comprises today — established from the code, and it is four
components, not one**

| # | Component | Where | Gated by `stealth_enabled`? |
|---|---|---|---|
| 1 | `--disable-blink-features=AutomationControlled` launch argument | `BrowserManager.__aenter__`, the `chromium.launch(...)` call's `args` | **YES** |
| 2 | `page.add_init_script(path=str(self._stealth_path))` — the `stealth.min.js` injection | `BrowserManager.create_stealth_page` | **YES** |
| 3 | Context identity: `viewport`, `user_agent`, `locale`, `timezone_id` | `BrowserManager.create_stealth_page`, the `new_context(...)` call | **NO** — see below |
| 4 | `DEBUG("creating_stealth_page")` / `DEBUG("stealth_script_applied")` records | `create_stealth_page` | **NO** — the records describe what happened, and stay accurate |

**Why 1 and 2 are gated and 3 is not — the reasoning, because it is the block's one real judgement.**

- **1 and 2 are anti-detection measures and nothing else.** `--disable-blink-features=AutomationControlled`
  exists solely to suppress the `navigator.webdriver` signal, and `stealth.min.js` exists solely to mask
  browser fingerprints — `docs/STRUCT.md` itself calls it an "Anti-bot browser evasion stub". With
  stealth off, suppressing those signals would be a lie about what the tool is doing and would make
  detection *harder* to diagnose. Both are gated together.
- **3 is ordinary browser configuration, not evasion.** Established against the code:
  `settings.user_agent` is consumed by **four** call sites — the browser context,
  `segment_downloader`'s HTTP `User-Agent` header, yt-dlp's `--user-agent`, and the ffmpeg transport's
  `-headers` value (deleted by `B10`) — so it is **request identity for the whole download path**, and
  gating it at the `Settings` level would break the other three consumers. `viewport` is a hard-coded
  literal, not a setting at all. `locale` and `timezone` are consumed **only** by the browser context,
  so gating them would be technically safe — **but they should not be gated.** A Russian locale and a
  Moscow timezone are what a real user's browser looks like; applying them is **correctness, not
  evasion**, and suppressing them would make extraction *less* likely to succeed for a user in that
  region while buying no anti-detection gain the flag is not already withholding. **Their field
  descriptions are corrected rather than acted on** — `config.py` describes them as "for browser
  stealth configuration", which is what made them look like stealth in the first place, and it is
  misleading. `user_agent`'s description ("User agent string for browser requests") is already accurate
  and is **unchanged**.

**The new setting**

| Property | Value | Why |
|---|---|---|
| **Name** | `stealth_enabled` | States what it enables. Not `stealth` (ambiguous with the asset), not `use_stealth` (verb-y), not `anti_detection` (broader than what it gates). |
| **Type** | `bool` | **The owner specified a flag, and `D5` says configuration, not policy.** Not an enum, **not a tri-state**: there is no third state, because "no preference" is answered by the user's answer. |
| **Default** | `False` | The owner's words: *"по умолчанию отключено"*. |
| **Home** | `Settings`, in the existing **`# Browser Automation settings`** group, immediately after `locale` | It belongs with `headless`, `user_agent`, `timezone` and `locale`, which is the group it lives in. |
| **Field declaration** | `stealth_enabled: bool = Field(default=False, description=...)` | Matches the sibling convention exactly: `headless: bool = Field(default=False, description="Run browser in headless mode (no GUI)")` — a `bool` field carries **no** `ge`/`le` and **no** `@field_validator`, because `bool` has no out-of-range value. The `@field_validator("user_agent", "timezone", "locale", mode="before")` exists only to reject empty strings, which cannot happen to a `bool`. |
| **Description** | Must state in its own words: it gates the anti-detection measures (the automation-suppression launch argument and the `stealth.min.js` init script); it does **not** gate the browser context's viewport, user agent, locale or timezone; when enabled the `stealth.min.js` asset is **required** and its absence is a hard error; and it is **off by default**. | Rule 14: the description is the only place a user learns all four facts, and the last one is the behaviour change. |
| **Three places** | field description + a commented `.env.example` row + a new row in `docs/11-guides/configuration.md` beside the other browser rows | Rule 11. `model_config`'s `extra="forbid"` makes an unrecognised `VKDOWNLOADER_*` an error, so an `.env.example` value the model rejects — or a documented variable the model has never heard of — is a correctness bug, not a courtesy. **Phase 02 found exactly that class of bug.** |
| **`.env.example` placement** | `# VKDOWNLOADER_STEALTH_ENABLED=false`, appended as the **last row of the existing Browser Automation block** (after `VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT`) | Append rather than insert, so the block's existing order is untouched — rule 5, minimal diff. |
| **No validator** | None | See the `bool` convention above. A validator here would be overengineering (rule 5). |

**Where the gate lives.** In `BrowserManager`, read from `self.settings.stealth_enabled` at the two
consumption points — `__aenter__` for the launch argument, `create_stealth_page` for the injection.
**Not** as a computed property on `Settings`, and **not** in `Settings` at all beyond the field:
`Settings` holds data; `BrowserManager` is the module that owns the stealth posture. There is no policy
object, no profile list, no heuristic, and no CLI subcommand — `D5` is a flag.

**Where the asset check belongs — `__aenter__`, before the driver. Verified that this placement
actually works.**

`BrowserManager.__init__` assigns `self._stealth_path` **before** any I/O, so the value is available at
the first statement of `__aenter__`. `__aenter__`'s structure is:

```
logger.info("starting_browser")
playwright_instance = await async_playwright().start()   <-- the driver starts HERE
try:
    browser = await playwright_instance.chromium.launch(...)
except Exception:
    logger.error("browser_launch_failed", exc_info=True)
    await playwright_instance.stop()                     <-- cleanup exists BECAUSE the driver started
    raise ExtractionError(...) from None
```

Two things follow, and both confirm the placement:

1. **The check costs nothing when placed before line 2.** No driver is started, no browser is launched,
   and **no cleanup is required** — Python's `async with` does not call `__aexit__` when `__aenter__`
   raises, so a raise *after* the driver starts would leak the started driver unless it were cleaned up
   by hand. The existing `except Exception` arm does exactly that hand-cleanup, which is evidence the
   original author knew the invariant. **Placing the check first removes the need for it entirely.**
2. **The single call site can meaningfully handle it.** `extractor.py`'s `_extract_with_browser` does
   `async with BrowserManager(self.settings) as browser:` followed by `page = await
   browser.create_stealth_page()`, with **no `try`/`except` around either**. A raise from `__aenter__`
   propagates out of the `async with` and out of the extraction, which is exactly the fail-fast
   behaviour `D5` asks for when stealth was explicitly enabled.

**Rejected placements, and why:**

| | Candidate | Verdict |
|---|---|---|
| ✗ | `create_stealth_page` (where `D4`'s block looked) | Rejected: by then Chromium is **already launched** and must be torn down for nothing, and the raise comes from inside the caller's `async with` body — the least convenient place to receive a configuration failure. |
| ✗ | `BrowserManager.__init__` | Rejected: it is synchronous and would turn a typed extraction failure into a **construction-time** exception at every construction site, moving the failure outside the context manager where no cleanup contract exists. |
| ✓ | **`__aenter__`, before `async_playwright().start()`** | **Chosen.** Cheapest possible failure point; no resource to release; the shape is already in-repo, since that method already converts a launch failure into `ExtractionError`. |

**Exception type.** `ExtractionError`, unchanged from `D4`'s analysis and unchanged by `D5`. It already
means "video data extraction fails", already carries `error_code = ErrorCode.EXTRACTION_ERROR` and a
`status_label()`; `QualityParseError` is categorically the wrong type (it is about a quality string);
`DownloadError` is about the download. **No new exception class** — rule 5. **Does the caller need to
distinguish "asset missing" from "browser unavailable"? No.** Both mean "extraction cannot run", both are
`ExtractionError`, the single call site has no `try`/`except` to distinguish in, and the **message**
carries the distinction. What *is* worth adding is **one `ErrorCode` `StrEnum` member**, because
`ErrorCode` exists precisely for "stable machine-readable code for log filtering" and a missing asset is
a different operational cause from a browser that will not launch — a `StrEnum` member, not a class.

**The message shape — reuse `check_ffmpeg_available`'s convention, do not invent one.** That function's
only record for a missing dependency is:

```
logger.warning("ffmpeg_not_found", hint=("<what is missing>; <what will fail>"))
```

`B15` uses the same shape — one `hint` kwarg naming the missing path and the consequence — and puts the
**same text** in the raised `ExtractionError`, so the log record and the exception say the same thing.
Wording must name (a) the missing path, (b) that the asset is a declared build artefact, so a missing
file means a broken build or a partial deployment rather than a bad install, and (c) that stealth was
explicitly enabled and therefore cannot be satisfied.

**`create_stealth_page`'s existing guard — a deliberate non-removal.** With the check moved to
`__aenter__`, the `if self._stealth_path.exists():` branch in `create_stealth_page` becomes
unreachable-as-a-failure-path. **It stays, as defence in depth**: it is the last line before a page is
handed out, and removing it would trade a redundant check for an unguarded one. The block must update
the docstring — the page now carries the injected script **iff** `stealth_enabled` is true.

**The behaviour change, stated loudly.** Stealth was previously **always on**: the launch argument and
the script injection were unconditional. Defaulting `stealth_enabled` to `False` **removes stealth from
every existing user's default run.** That is what `D5` asks for, and it is a real change — and it
interacts with the reason `D4` was raised in the first place, high bot protection. A user on a
bot-protected origin who relied on the always-on posture must now set
`VKDOWNLOADER_STEALTH_ENABLED=true`. **Nothing in this plan decides whether that is acceptable for
them**; the block's job is to make it loud, not to soften it. §5.5 records it as a behaviour change and
§10 discloses it.

**Documentation that becomes wrong — eight claims and three docstrings.** A reader who reads any of
these after `B15` would be misinformed, so they are **in the block's scope**, not optional:

| Site | The claim |
|---|---|
| `docs/01-tools/vkdownloader-overview.md` | *"Secure-by-default browser stealth configuration"* — **this is the claim `D5` reverses outright** |
| `docs/01-tools/vkdownloader-overview.md` | *"Browser settings: User agent, locale, timezone for stealth; `headless` mode toggle for server/CI/Docker"* — the first half is now accurate only as context configuration, not stealth |
| `docs/01-tools/vkdownloader-overview.md` | the module table row: *"Playwright browser lifecycle management with stealth configuration (user agent, locale, time…)"* |
| `docs/01-tools/api-reference.md` | `BrowserManager`: *"Async context manager for Playwright browser automation with stealth configuration"* |
| `docs/01-tools/api-reference.md` | `create_stealth_page()`: *"Create a new page with stealth configuration"* |
| `docs/01-tools/quality-selection.md` | *"Opens video page in stealth browser"* |
| `docs/11-guides/configuration.md` | the `timezone` row: *"Timezone for stealth configuration"* |
| `docs/11-guides/configuration.md` | the `locale` row: *"Locale for browser stealth"* |
| `docs/11-guides/vkdownloader-limitations.md` | *"`navigator.webdriver` flag (masked by stealth.min.js)"* — now true only when enabled |
| plus the three **in-code** docstrings | `BrowserManager`'s class docstring, `__aenter__`'s, and `create_stealth_page`'s — all say "with stealth configuration" unconditionally |
| `src/vkdownloader/config.py` | the `timezone` and `locale` field descriptions — *"for browser stealth configuration"* |

`docs/STRUCT.md`'s entry (*"stealth.min.js # Anti-bot browser evasion stub"*) is a **file listing**, not
a claim about when it is applied, and **stays correct**.

**Deliberate non-change, recorded so no block "fixes" it.** `BrowserManager` and `create_stealth_page`
keep their names even though stealth is now conditional. Renaming a **public API** —
`BrowserManager` is in `vkdownloader/__init__.py`'s `__all__` — for a default flip is disproportionate,
and both names still describe the capability that exists when the flag is on.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `src/vkdownloader/config.py` | `Settings.stealth_enabled` — a new `bool` field inserted immediately after `locale` in the `# Browser Automation settings` group | The flag. `Field(default=False, description=...)`, no bounds, no validator. |
| `src/vkdownloader/config.py` | the `timezone` and `locale` field descriptions — *"for browser stealth configuration"* | **Corrected, not gated.** They describe ordinary context configuration. |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__aenter__` — the `chromium.launch(...)` call's `args=[...]` | **Component 1, gated.** The automation-suppression argument is present only when `stealth_enabled` is true. |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__aenter__` — the statements between its entry and `playwright_instance = await async_playwright().start()` | **Where the conditional asset check goes.** Before the driver, so it costs nothing and needs no cleanup. |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__aenter__` — the `except Exception:` arm and its `raise ExtractionError(...) from None` | **`B8`'s anchor. Untouched by this block** (`S1i`). |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__aenter__` — its docstring, *"Start Playwright and launch browser with stealth configuration"* | Conditionalised. |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__init__` — `self._stealth_path = Path(__file__).parent.parent / "stealth.min.js"` | **Read-only.** It is the value the check reads and the message names. No new state. |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager` — its class docstring | Conditionalised: stealth configuration is applied **when enabled**. |
| `src/vkdownloader/infrastructure/browser.py` | `create_stealth_page` — the `if self._stealth_path.exists():` statement and its body | **Component 2, gated**, and **the guard stays** as defence in depth. |
| `src/vkdownloader/infrastructure/browser.py` | `create_stealth_page` — the `new_context(...)` call's `viewport` / `user_agent` / `locale` / `timezone_id` arguments | **Component 3, NOT gated.** Untouched. |
| `src/vkdownloader/infrastructure/browser.py` | `create_stealth_page` — the `logger.debug("creating_stealth_page")` and `logger.debug("stealth_script_applied")` records | Stay accurate as written: they describe what happened, and with the flag the second one is conditional by construction. |
| `src/vkdownloader/infrastructure/browser.py` | `create_stealth_page`'s docstring and its `Returns:` line | Must say the page carries the injected script **iff** the flag is on. |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__aexit__` | **Untouched.** Plan 08 `B4` rewrote it; its six tests must stay green unchanged. |
| `src/vkdownloader/infrastructure/browser.py` | the `await self.browser.new_context(...)` call and its `# type: ignore[union-attr]` | **Untouched.** `BRW-002` is rejected and no release path may be added here (§1.4). |
| `src/vkdownloader/models/enums.py` | `ErrorCode` — one new `StrEnum` member for the missing-asset cause | Rule 10. **One member**, no new exception class. |
| `.env.example` | the Browser Automation block | One commented row appended. |
| `docs/11-guides/configuration.md` | the browser settings table | One new row beside the others; plus the `timezone` and `locale` description corrections. |
| the eight documentation claims + three docstrings listed above | | Corrected. |
| `pyproject.toml` | the `artifacts` declaration | **Read-only.** `B10` must not remove it, and under `D5` it is what makes a missing asset mean a broken build. |

**Tests required**

- **ADD** — the **flag default**: `Settings()` constructs with `stealth_enabled is False`; the
  `.env.example` value constructs; `VKDOWNLOADER_STEALTH_ENABLED=true` constructs.
- **ADD** — **stealth off, asset present**: with the flag false, the launch call's `args` **does not
  contain** `--disable-blink-features=AutomationControlled`, and `add_init_script` is **not** called.
  The page is still returned.
- **ADD** — **stealth off, asset absent**: with the flag false, an absent asset produces **no error, no
  warning and no check** — nothing consults `self._stealth_path`. This is the case that dissolves
  `BRW-003`, and it must be asserted, because a block that "helpfully" checks regardless of the flag
  would silently reintroduce the always-on posture in a different shape.
- **ADD** — **stealth on, asset present**: the launch `args` **does** contain the automation-suppression
  argument and `add_init_script` **is** called.
- **ADD** — **stealth on, asset missing**: `__aenter__` raises `ExtractionError`; the message names the
  path, names the broken-build-or-partial-deployment consequence, and names the remedy.
- **ADD** — **the ordering proof, and it is the gate**: on the stealth-on/asset-missing path,
  `async_playwright().start()` is **never called**. Without it the check could sit after the launch
  and pass every other assertion while achieving nothing over checking at page-creation time.
- **ADD** — **`ErrorCode`**: the raised exception's `error_code` is the new member, not
  `EXTRACTION_ERROR`.
- **ADD** — **component 3 is not gated**: with the flag false, `new_context` is still called with the
  configured `user_agent`, `locale`, `timezone_id` and the 1920x1080 viewport. This pins the decision
  `S1h` made, so a later "consistency" argument cannot quietly gate them.
- **MUST STAY GREEN UNCHANGED** `::TestBrowserManager`'s six plan-08 `B4` tests and `B8`'s re-scoped
  launch-failure case.

**Dependencies:** `depends_on: [B5, B8, B11]` (`E5`, `E10`, `E20`).

**Risk class: HIGH** for a block that adds a **default-facing behaviour change**. `D5`'s default flip
is the largest user-visible change in this plan after `B10`'s deletion, and it is the change most likely
to be misread as a bug. §5.1b.

**Prohibitions (binding)**

1. **No heuristic, no policy engine, no profile list, no CLI subcommand, no per-site configuration.**
   `D5` is a flag. A "decide whether stealth is needed" implementation that guesses is exactly what the
   owner did **not** ask for.
2. **MUST NOT** gate the context identity triple (`viewport`, `user_agent`, `locale`, `timezone_id`).
   Their *descriptions* are corrected; their *behaviour* is untouched. `S1h`.
3. **MUST NOT** check the asset when the flag is false. That is what makes `BRW-003`'s original form
   dissolve, and checking anyway reintroduces the always-on posture.
4. **MUST NOT** add a warning-level `else` to `create_stealth_page` as the enabled-path remedy. When
   stealth is explicitly enabled and the asset is missing, the answer is a **hard failure**, not a
   warning. (The flag-off path emits nothing at all, which is a different thing and is correct.)
5. **MUST NOT** introduce a new exception class. `ExtractionError` plus one `ErrorCode` `StrEnum` member
   is the whole of it.
6. **MUST NOT** add a fallback that continues without stealth, a "warn and proceed" mode, or any
   second switch. `D5` is a boolean.
7. **MUST NOT** move the check into `__init__`, and **MUST NOT** place it after
   `async_playwright().start()` — the ordering proof test is the gate.
8. **MUST NOT** remove `create_stealth_page`'s `if self._stealth_path.exists():` guard entirely. It is
   the last line before a page is handed out.
9. **MUST NOT** touch `B8`'s anchors — the `except Exception:` arm, its `exc_info=True`, its `from
   None`, or the `await playwright_instance.stop()` before the raise (`S1i`).
10. **MUST NOT** touch `__aexit__`, the `# type: ignore[union-attr]`, or add a context release path
    (`BRW-002` is rejected).
11. **MUST NOT** edit `pyproject.toml`, and `B10` **MUST NOT** remove the `stealth.min.js` artefact
    declaration.
12. **MUST NOT** rename `BrowserManager` or `create_stealth_page`. A public-API rename for a default
    flip is disproportionate; the names still describe the capability that exists when the flag is on.
13. **MUST NOT** invent a new missing-dependency message convention. Reuse `check_ffmpeg_available`'s
    `logger.warning(<event>, hint=(<what is missing>; <what will fail>))` shape, with the same text in
    the raised exception.
14. `browser.py` gains **no new import** beyond structlog's `get_logger`, which it already uses.
15. `config.py`'s new field must satisfy the **three-place rule exactly**. No second knob, no alias.

**Commit shape.** One commit, subject naming the opt-in stealth setting, body carrying: the owner's
`D5` words verbatim with an English rendering; the **four-component table** with the gated/ungated
decision and the reasoning for component 3; the placement decision with the two rejected candidates and
the `async with` / `__aexit__` invariant that confirms the chosen one; the exception and `ErrorCode`
choice; the `check_ffmpeg_available` message shape reused verbatim; the measured before/after (the
launch `args` and the injection under each flag value; the enabled/asset-missing path before -> no
check at all, after -> `ExtractionError` before the driver starts); the **behaviour-change warning** that
every existing user's default run loses stealth; the eleven documentation claims and docstrings
corrected; the deliberate non-changes (`S1h`, and the no-rename decision); and `D5`'s supersession of
`D4`. Cited `BRW-003`, `D5`.

### B16 — Give the console sink an encoding-safe error handler

> **`D7` — ADOPTED HERE (Tech Lead). Option (A). This block is no longer `CONDITIONAL`; there is no
> gate on it.** Recorded in §9.

**Goal.** A log record carrying characters the console stream's encoding cannot represent must not
raise out of `logging.StreamHandler.emit`.

**The ownership gap, recorded because it is the reason the gap survived.** Phase 01's
`ENT-001`/`ENT-002` are sink-*routing* findings and deferred encoding to phase 08; phase 08 never filed
it; a corpus search for `cp1251` finds it only as *evidence* inside `ENT-001`, `ENT-002` and `OUT-002`.
**No finding in any phase owns it**, which is precisely why it survived two audits. `D7` adopts it here.

**The measured behaviour, which makes it conditional-by-environment and not by-theory.** With this
machine's real default `sys.stderr` (cp1251, `errors="backslashreplace"`), the statement **returns
normally** — the box-drawing characters are escaped into the record. Re-wrapped as cp1251 with
`errors="strict"`, it **raises** and `ExtractionError` is never constructed. With `log_file` set, it
**returns normally** — the `JSONRenderer` ASCII-escapes the traceback, so the `FileHandler` writes only
7-bit characters. A search of `src/` for `reconfigure`, `PYTHONIOENCODING`, `errors=` and `encode(`
returns nothing: `setup_logging` gives the console a bare `logging.StreamHandler()`.

**Why the remedy belongs in `config.py`, not `browser.py`.** The defect is in the **sink**, not the call
site: a `StreamHandler` constructed with no `errors=` inherits the stream's error handler, and a record
that cannot be encoded propagates out of `emit`. Fixing it at the call site would be a per-callsite
`try`, which is the anti-pattern plan 08 `B4` named. That is also why this is a separate block from `B8`
and from `B15`, both of which land in `browser.py`.

**`D7`'s reasons, recorded — and one of them checked against the code.**

| Reason `D7` gave | Holds? |
|---|---|
| It is a small `config.py` change plus a test | **Yes.** One handler construction, one field-free attribute, two test cases. |
| It is the mechanism behind `BRW-001`'s HIGH reclassification | **Yes.** `BRW-001`'s unconditional half is `logger.error(..., exc_info=True)` raising `UnicodeEncodeError` where an `ExtractionError` should be constructed. |
| It has no owning phase, which is why it survived 01 and 08 | **Yes**, and it is the reason an audit-pipeline decision was needed rather than a routing one. |
| With `D5` the browser path is now reached on ordinary runs, so the exposure is more common | **NO — and this is recorded rather than repeated.** Verified against the code: `Settings.cookie_source` defaults to **`CookieSource.NONE`**, so `BrowserManager` is **not** entered on an ordinary default run at all; it is reached only when `VKDOWNLOADER_COOKIE_SOURCE=browser`. And `D5` does not change that default — stealth is an axis **orthogonal** to whether the browser is used for cookie extraction. Turning stealth off does not stop the browser from launching. **The fourth rationale is therefore not borne out.** It does not affect the decision, which stands on the first three, but it is recorded so no future reader cites it as a fact about the code. |

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `src/vkdownloader/config.py` | `setup_logging` — the `logging.StreamHandler()` construction on the `log_file is None` branch | The defect. The handler must be constructed with an encoding-safe `errors=` value, so a non-encodable record is escaped rather than raised. |
| `src/vkdownloader/config.py` | `setup_logging` — the `FileHandler` + `JSONRenderer` branch | **Unchanged.** That sink already writes 7-bit characters only, and the measured behaviour confirms it does not raise. |
| `src/vkdownloader/cli.py` | `_run_command_preamble`'s fallback to the console sink when configuration failed | **Read-only.** `B16` must not become a second configuration path. |
| `src/vkdownloader/infrastructure/browser.py` | `BrowserManager.__aenter__`'s `except Exception:` arm, and `B15`'s new asset check | **Read-only, both.** `B16` must **not** wrap the `logger.error` statement in a `try`, must **not** remove `exc_info=True`, and must not touch `B15`'s flag or check. |

**Tests required**

- **ADD** — the strict-stream case, which does not exist today: `sys.stderr` re-wrapped as a
  strict-encoded stream, a record carrying non-encodable characters emitted through the configured
  console sink, and **no exception** escaping. This is the case that does not exist and the whole point
  of the block.
- **ADD** — the negative case: the record is still emitted and still **contains** the information,
  escaped rather than dropped. A fix that suppresses the record instead of escaping it is not a fix.
- **MUST STAY GREEN UNCHANGED** every `tests/test_config.py` case and the six plan-08 `B4` tests, and
  `B8`'s and `B15`'s `browser.py` cases.

**Dependencies:** `depends_on: [B8]` (`C9`).

**Risk class: LOW-MEDIUM.** A narrow `config.py` change with a small blast radius — but it is the block
with **no finding behind it**, which is why `D7` is recorded as an adoption rather than a fix.

**Prohibitions (binding)**

1. `browser.py` is **not** edited by this block. No per-callsite `try`, no removal of `exc_info=True`,
   no touching of `B8`'s arm or `B15`'s flag.
2. `setup_logging`'s **file** branch is not changed.
3. **No `PYTHONIOENCODING` manipulation**, no `sys.stderr.reconfigure(...)`. The fix is the handler's
   `errors=` value; reconfiguring the interpreter's streams behind the user's back is a side effect this
   project has no precedent for and did not ask for.
4. The block may **not** claim or close `BRW-001` — that is `B8`'s, and only half (a) of it.
5. No `Settings` field. `B11`'s `download_stall_timeout` and `B15`'s `stealth_enabled` are the plan's
   only two.

**Commit shape.** One commit, subject naming the console sink's encoding handling, body carrying the
measured before/after for a strict-encoded stream, `D7`'s four reasons **with the fourth marked as not
borne out by the code** (`cookie_source` defaults to `NONE`; stealth and browser use are orthogonal), and
the statement that the defect had NO owning finding in any phase and is adopted here by the Tech Lead's
decision. Cited `D7`.

## §4 Dependency graph and execution order

### §4.1 The graph

```
        ┌──────────────────────────────────────────────────────────────────────┐
        │  WAVE 0 — no dependency, no decision gate (7 blocks)                  │
        │                                                                      │
   B2  TRN-004  ───────────────────────────────────────►                     │
   B3  ~~TRN-005~~ DELETED by D2                                              │
   B4  TRN-006 sink ──────────┐                                               │
   B6  TRN-011 ───────────────┤                                               │
   B7  TRN-009 claim ─────┐   │                                               │
   B8  BRW-001(a) ────────┼───┼──►                                            │
   B14 merge sinks ◄──────┘   │                                               │
   B16 console sink  CONDITIONAL, Q6 open ──────────────────────────────────► │
        └─────────────────────┼───────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴───────────────────────────────┐
        │  WAVE 1 — the deletion, and everything it moves      │
        │                                                       │
   B10 DELETE the transport ──┬──► B5  TRN-012 (6 sites -> 2)   │
        │                     ├──► B4  (parse half removed)    │
        │                     └──► B1  TRN-002 re-scoped        │
│                     └──► B13 TRN-008 (4 arms -> 3, D6 decided) ──────►
        └─────────────────────┬────────────────────────────────┘
                              │
        ┌─────────────────────┴───────────────────────────────┐
        │  WAVE 2 — settled boundaries (no gates)               │
        │  B11 stall bound (D3)   B12 process boundary (D1)     │
        │  B5  cancellation contract (after B10, after B1)      │
        │  B15 stealth hard failure (D4, after B5, after B8)    │
        └───────────────────────────────────────────────────────┘
                              │
                              ▼
                    B9  record the closed chains (last)
```

**Formal edges (14 live blocks + 1 deleted, 9 edges):**

| From | To | Conflict | Why |
|---|---|---|---|
| **E1** | *retired* | — | **`phase05/VAL-502` chain 1 — EVAPORATED.** Revision 1 made `B1` precede `B10` so that repairing `TRN-001` could not convert a benign ordering into a data-loss one. There is no repair now, and `B1`'s subject has been re-scoped to a different statement in a different module (§1.3 `S1b`). **The chain is discharged by the deletion itself**, not by an ordering. |
| **E2** | `B10` -> `B1`, `B5`, `B4`, `B13` | `C1`, `C2`, `C3`, `C17` | **The deletion is upstream of four blocks.** It removes four of `B5`'s six `cancel_subprocess` sites, deletes `B4`'s parse half along with `_PROGRESS_KEY_HANDLERS`, re-scopes `B1`'s subject onto the cookie-file `finally:` that must not be mirrored into a helper being deleted, and deletes `B13`'s arm (a). Each of those four must be reviewed against the **landed** tree, not against the tree Revision 1 described. |
| **E3** | `B2` -> `B4` | `C4` | Prevention then reporting of the same reader failure. `B2` makes the yt-dlp reader survive an oversized line; `B4` makes its death visible. **Survives `D2`**: both subjects — `iter_process_lines` and `_await_first_and_cancel_others` — are still reachable from `_download_with_ytdlp`. |
| **E4** | `B1` -> `B5` | `C5` | `B1` hardens the cookie-file `finally:` in the same `_download_with_ytdlp` whose `except asyncio.CancelledError:` arm `B5` re-scopes. Two blocks in one function's error paths in the same review. |
| **E5** | `B5` -> `B15` | `C6` | **`D5` restates the dependency.** Under `D4` the failure was unconditional, so `B5` mattered because a hard failure must be *read*. Under `D5` the failure fires **only when the user has explicitly enabled stealth** — rarer, and therefore *more* important to be right when it does fire: a user on a bot-protected origin has opted in precisely because detection matters to them. `B5` still makes the module's warning channel trustworthy first. |
| **E6** | `B5` -> `B12` | `C7` | `B12` changes what `cancel_subprocess` *does*; `B5` owns what its two surviving callers *read*, plus the function's signature, keyword-only `timeout` and return contract. |
| **E7** | `B7` -> `B14` | `C18` | `B14` applies the transform at the two merge sinks; `B7` makes the docstring honest first, so the repository is never in a state where a false claim has been replaced by nothing. |
| **E8** | `B5` -> `B11` | `C8` | `B11`'s timeout arm must re-enter the termination ladder and re-raise. The ladder's documented contract is `B5`'s; `B11` is reviewed against the landed text. |
| **E9** | `B8` -> `B16` | `C9` | Different modules. `B16`'s negative measurement depends on `B8`'s landed text, and `B4`/`D4` make the ordering worse — see `B16`. `B16` must not edit `browser.py`. |
| **E10** | `B8` -> `B15` | `C15` | **Same method, different statements, different verification shapes — and a stated non-merge (`S1i`).** `D5` puts a `Settings` field, two gated components and a conditional pre-driver check into `__aenter__` alongside `B8`'s `except` arm. The two stay separate because no test of one satisfies the other, and `B8` goes first because it is unconditional while `B15` changes the **default** behaviour for every user — a revert of the posture change must leave the information fix standing. |
| **E11** | `B10` -> `B13` | `C11` | **Preferred order, not a hard edge** — with `D6` this edge is now satisfied and the block is ungated. `TRN-008`'s arm (a) is the `FileNotFoundError` a repaired `TRN-001` would no longer raise; under `D2` the transport is deleted and the arm is gone. `B13`'s four-arm table is re-derived against the landed tree and the result is **three** arms. |
| **E20** | `B11` -> `B15` | `C19` | **New with `D5`.** Both blocks add a `Settings` field and both must satisfy the same three-place rule across the same three files (`config.py`, `.env.example`, `docs/11-guides/configuration.md`). `B11` goes first so the pattern is established and reviewed once. Strict: `B11` is position 10, `B15` is position 11 in §4.2. |

**Acyclicity proof.** Assign ranks: `rank(B2) = rank(B6) = rank(B7) = rank(B8) = rank(B14) = rank(B16)
= 1`; `rank(B4) = rank(B10) = 2`; `rank(B1) = rank(B5) = 2`; `rank(B11) = rank(B12) = rank(B13) = 3`;
= 1`; `rank(B4) = rank(B10) = 2`; `rank(B1) = rank(B5) = 2`; `rank(B11) = rank(B12) = rank(B13) = 3`;
`rank(B9) = rank(B15) = 4`. For every edge `u -> v`: `(B10, B1)` gives `2 = 2` — **not strict**, and it
is handled by `E2`'s stated rationale (both land in wave 1, `B10` first by position, with the
one-directional review obligation) rather than by the rank. `(B10, B5)` gives `2 = 2`, same treatment.
`(B10, B4)` gives `2 = 2`, same. `(B10, B13)` gives `2 < 3` **strict**. `(B2, B4)` gives `1 < 2`.
`(B1, B5)` gives `2 = 2` — treated as a preference within wave 1. `(B5, B15)` gives `2 < 4` **strict**.
`(B5, B12)` gives `2 < 3` **strict**. `(B7, B14)` gives `1 = 1` — a **preference**, not an edge.
`(B5, B11)` gives `2 < 3` **strict**. `(B8, B16)` gives `1 = 1` — a preference. `(B8, B15)` gives
`1 < 4` **strict**. `(B11, B15)` gives `3 < 4` **strict** — the one new edge `D5` adds, and the only
one whose strictness comes from an ordering decision rather than from a dependency. Every **strict**
edge increases the rank and the four non-strict pairs are ordered preferences inside a single wave, so
no edge points backwards: **the graph is a DAG**. A topological order consistent with §4.2 is
`B10, B1, B5, B4, B2, B7, B14, B6, B8, B11, B15, B16, B12, B13, B9`.

### §4.2 The linearised order, and the reason for each position

Execution is **sequential with one Implementor at a time**. `D2` made this mandatory rather than
merely advisable: `B10` deletes four `src/` modules' worth of symbols and re-exports, and two
Implementors working those modules at once is how a deletion loses a live symbol.

| # | Block | Why here |
|---|---|---|
| 1 | **B10** `TRN-001`+`TRN-010` — **the deletion** | **First, because everything downstream must be reviewed against the landed tree.** Four blocks are re-scoped by it and four more are pinned by it. It is also the block with the widest blast radius — four `src/` modules, the package root, seven documentation sites, two test files — and the widest blast radius should land while the tree is otherwise quiet and the rest of the plan is unblocked to re-scope against it. It needs no decision: `D2` is made. |
| 2 | **B1** `TRN-002` re-scoped | Its subject is a statement `B10` does **not** delete, so it could go anywhere in wave 1 — but its prohibition 1 says it must not mirror the fix into `_temp_argfile`, and it cannot be written against a helper that still exists. Second, immediately after the deletion. |
| 3 | **B5** `TRN-012` | The deletion removes four of its six sites; the two that survive are the whole block. Third, so its diff is reviewed against a settled tree rather than half-done. |
| 4 | **B4** `TRN-006` sink half | Its parse half is deleted by `B10`, so its anchor table shrinks by half. Fourth — right after the blocks whose anchors it shares. |
| 5 | **B2** `TRN-004` | **Unaffected by `D2`** and unconstrained. Fifth because it needs the most independent reading (§6) and because `B4` above is its reporting partner. |
| 6 | **B7** `TRN-009` claim | Documentation, zero risk, and the precondition for `B14`. Sixth so no block report inherits the false claim. |
| 7 | **B14** merge sinks | Two lines and two tests. **No longer gated** — the `Q5` split is decided. Seventh, right after `B7`. |
| 8 | **B6** `TRN-011` | Self-contained, MEDIUM, one buffer, **unaffected by `D2`**. Eighth because it shares `_download_with_ytdlp` with `B11` and it is easier to review one of the two before the other arrives. |
| 9 | **B8** `BRW-001`(a) | The other unconditional HIGH. Ninth — and it precedes `B15` (`S1i`, `E10`), which lands in the same method. |
| 10 | **B11** `TRN-007` — **settled by `D3`** | Tenth. It adds the plan's **first** `Settings` field and therefore the **first** exercise of the three-place rule — field description, `.env.example`, configuration guide. Placed **before `B15`**, which adds the plan's **second** `Settings` field, so the second copies a pattern the first has already established and reviewed. **This ordering is why `B15` sits where it does** — not merely `E5`. |
| 11 | **B15** `BRW-003` **re-scoped by `D5`** | After `B8` (`S1i` — the information fix before the posture change), after `B5` (`E5`), and after `B11` (`E20` — the settings-field pattern). Eleventh. It is the largest user-visible behaviour change after `B10`, and it lands where the three-place rule it must follow is already proven and where the browser method it modifies is already settled by `B8`. |
| 12 | **B16** console sink — **adopted by `D7`** | After `B8` (`C9` — its negative measurement depends on `B8`'s landed text). Twelfth, and no longer gated: it is a single handler construction with two tests, and it is the only block in the plan with **no finding behind it**, so it lands late but unobstructed. |
| 13 | **B12** `TRN-003` — **settled by `D1`** | After `B5` and `B11`, both of which edit `cancel_subprocess`'s neighbourhood. Thirteenth because it is the widest behavioural surface (three spawn sites plus the ladder) and its decision, though made, has a documented residual that a reviewer should read against settled code. |
| 14 | **B13** `TRN-008` — **settled by `D6`** | Fourteenth. Its arm enumeration must be re-derived against the landed tree and the result is **three** arms. It sits after `B12` because both touch the muxer. No longer gated. |
| 15 | **B9** `phase05/VAL-501`+`phase05/VAL-502` record | **Last.** Revision 1 put it first, on `phase05/VAL-501`'s "record before anything is scheduled". That instruction is **spent**: `D2` has already been taken and recorded in §9, so there is no longer an unscheduled risk to warn anyone about. What remains is the correction record, most accurate once the deletion's exact shape is final — and it must now also record `D5`, `D6` and `D7`. |

**Zero gates.** The order above contains **no conditional position**. All fifteen blocks are
executable without a further decision: `B13`'s and `B16`'s previous "only if answered" conditions
are discharged by `D6` and `D7`.

**One new ordering edge, from `D5`.** `E20`: `B11` before `B15`. Both add a `Settings` field and both
must satisfy the same three-place rule across the same three files (`config.py`, `.env.example`,
`docs/11-guides/configuration.md`). `B11` goes first so the pattern is established and reviewed once,
and `B15` copies it. This is conflict `C19`.

### §4.3 Conflict matrix — every pair sharing a semantic anchor

`C1`–`C18`. **Semantic names are the key; line numbers are historical locators and are deliberately
absent.** Rows `C1`, `C3`, `C4` and `C10` are re-derived from Revision 1.

| # | Findings · blocks | **Shared semantic anchor** (semantic key) | Nature | Resolution |
|---|---|---|---|---|
| **C1** *(re-derived)* | `TRN-001` deletion ↔ `TRN-002` re-scoped · **B1 <- B10** | `_temp_argfile` / `_format_argfile` and the `download_with_ffmpeg` cookie-file `finally:` — all deleted | **Retired conflict.** Revision 1's `C1` was the `phase05/VAL-502` chain-1 ordering on the argfile's destroy. Both subjects are gone and `B1`'s subject has moved. **No edge.** `B1`'s prohibition 1 records the residue: it must not mirror the fix into a helper being deleted. |
| **C2** *(new)* | `TRN-001` deletion ↔ `TRN-012` · **B5 <- B10** | The four `cancel_subprocess` call sites inside `download_with_ffmpeg`, and `downloader.py`'s `cancel_subprocess` re-export | **Anchor removal.** `B5` loses four of six sites and one of its two modules. | **Edge `E2`, wave 1, `B10` first.** `B5`'s report re-verifies its two surviving sites against the landed tree. |
| **C3** *(re-derived)* | `TRN-001` deletion ↔ `TRN-006` · **B4 <- B10** | `read_progress`, `ProgressParser`, `FfmpegProgress`, `_PROGRESS_KEY_HANDLERS` in `ffmpeg_utils.py`, plus `downloader.py`'s re-exports of them | **Anchor removal.** `B4` loses its parse half and one of its two modules. | **Edge `E2`, wave 1, `B10` first.** `B4` is reviewed against the landed `ffmpeg_utils.py`. |
| **C4** *(re-derived)* | `TRN-004` ↔ `TRN-006` sink · **B4 <- B2** | `iter_process_lines`'s liveness and `_await_first_and_cancel_others` as its observer | **Prevention then reporting.** Both survive `D2` intact. | **Edge `E3`: `B2` first.** `B4`'s report states how many routes remained when it ran. |
| **C5** *(new)* | `TRN-002` re-scoped ↔ `TRN-012` · **B5 <- B1** | `_download_with_ytdlp` — its `finally:` (the cookie destroy) and its `except asyncio.CancelledError:` arm (a `cancel_subprocess` guard) | **Same function, adjacent error paths.** `B1` hardens the `finally:`; `B5` re-scopes the arm above it. | **Preference within wave 1: `B1` first.** Not an edge; both are small and the review reads better in file order. |
| **C6** *(new)* | `TRN-012` ↔ `BRW-003` escalated · **B15 <- B5** | `infrastructure/browser.py`'s record channel vs the spurious `yt_dlp_cancel_not_clean` records `B5` removes | **Noise — and `D4` raises the stakes.** A hard failure that nobody sees is the failure `D4` exists to prevent. | **Edge `E5`: `B5` first.** |
| **C7** | `TRN-003` ↔ `TRN-012` · **B12 <- B5** | `cancel_subprocess`'s signature, keyword-only `timeout`, and return contract | **Contract ownership.** `B12` changes what the ladder does; `B5` owns what it means. | **Edge `E6`: `B5` first**, plus a binding prohibition on `B12` touching signature, timeout or return value. |
| **C8** | `TRN-007` ↔ `TRN-012` · **B11 <- B5** | The termination ladder `B11`'s timeout arm re-enters | **Contract ownership**, same shape as `C7`. | **Edge `E8`: `B5` first.** |
| **C9** | `BRW-001` ↔ the console-encoding gap · **B16 <- B8** | `browser.py`'s `except Exception:` arm — `logger.error(..., exc_info=True)` and the `ExtractionError` it precedes | **Same arm, different module for the remedy.** `D4` makes this ordering *worse*: a user on a broken deployment hits the encoding path on the way to `D4`'s correct error. | **Edge `E9`: `B8` first.** `B16` is `CONDITIONAL` on `Q6`, which is open. |
| **C10** *(re-derived)* | `TRN-001` deletion ↔ `TRN-008` · **B13 <- B10** | Arm (a): the `FileNotFoundError` from the muxer transport's spawn | **Anchor removal, and it resolves in `B10`'s favour.** The arm does not need re-deriving after the deletion; it is gone. | **Edge `E2`, wave 1, `B10` first**, so `B13`'s enumeration is three arms rather than four. |
| **C11** | `TRN-007` ↔ phase 03 `NET-007` and `download_timeout`'s declared boundary · **B11** | `Settings.download_timeout`'s `Field(description=…)`; the "no application-level download timeout is imposed" sentence | **Cross-phase, policy — and `D3` resolved it in `NET-007`'s favour.** An inactivity bound is not a whole-operation budget, so the withdrawal stands and the sentence needs amendment, not reversal. | **Prohibition: no whole-operation budget; the guide's existing row is not edited (plan 07 `C12`).** `B11` **adds** a row beside it and amends the field description to cross-reference. |
| **C12** | `TRN-007` ↔ plan 07 `C12` · **B11** | `docs/11-guides/configuration.md`'s `download_timeout` row | **Cross-plan, statement-level.** Plan 07 owns the existing row. | **Prohibition: `B11` adds a new row and edits no existing row.** Its report says so. |
| **C13** | `TRN-011` ↔ `TRN-007` · **B6`, `B11** | `_download_with_ytdlp`'s `output_chunks` accumulator and its unbounded re-wait | **Same function, different statements.** Both survive `D2`. | **No edge. Review obligation on both:** each states it did not touch the other's statement. |
| **C14** | `TRN-002` ↔ phase 07 `ART-008` · **B1** | The same temp-file destroy, filed independently by phase 07 | **Cross-phase, same pattern — and now the pattern's *other* instance.** Phase 07's row is about the cookie file in the segment path; `B1`'s surviving instance is the cookie file in the yt-dlp path. | **No edge.** `B1`'s report cites `ART-008` and phase 07's merge-layer fix as the **in-repo precedent** for the fix shape. Phase 07's files are not edited. |
| **C15** *(revised by `D5`)* | `BRW-001`(a) ↔ `BRW-003` · **B15 <- B8** | `infrastructure/browser.py` — `BrowserManager.__aenter__`: its `except Exception:` arm, its `raise ... from None`, its `await playwright_instance.stop()`, **and** the pre-driver asset check `B15` adds | **Same method, no shared statement, different verification shapes — a stated NON-merge (`S1i`).** `B8` is an *information* fix: one re-scoped pin plus three cases about message content and banner suppression. `B15` is a *posture* fix: a `Settings` field, two gated components, a conditional check and an ordering proof. **Edge `E10`, `B8` first.** `B15`'s prohibition 9 forbids it touching `B8`'s four anchors; `B8` must not gate or check anything. Neither may move a statement across the driver-start boundary, because the hand-cleanup exists only for statements after it. |
| **C16** *(new)* | `TRN-011` ↔ `TRN-012` · **B6`, `B5** | `ytdlp_downloader.py` — the `output_chunks` accumulator and the two `cancel_subprocess` guards | **Same module, and after `D2` that is *all* they share.** Revision 1 separated them because they touched different modules; now both live entirely in one file. | **No edge — review obligation on both.** Different statements, different failure modes, different verification; module overlap alone is not a shared anchor (rule 1, single responsibility). |
| **C17** *(new)* | `TRN-001` deletion ↔ `TRN-002` re-scoped · **B1 <- B10** | `_temp_argfile`'s `finally:` and the yt-dlp cookie `finally:` — the same `missing_ok=True` pattern, one deleted | **Prohibition, not ordering.** `B1` must not "helpfully" propagate its fix into a helper `B10` is deleting, and must not add a shared cleanup abstraction for what is, after the deletion, a single site. | **Prohibition on `B1`** (rule 5: one site does not need a helper). No edge. |
| **C18** *(re-derived from `C6`)* | `TRN-009` claim ↔ capability · **B14 <- B7** | `sanitize_text_for_log`'s docstring, and the two merge sinks' claim about what reaches them | **Sequential wording.** `B14` may make the docstring's reach true for two more sinks; `B7` makes it honest first. | **Preference: `B7` first**, written to be revisitable. |

| **C19** *(new, `D5`)* | `TRN-007` ↔ `BRW-003` · **B11 -> B15** | `Settings` — two new fields (`download_stall_timeout`, `stealth_enabled`) and the **same three-place rule** across `config.py`, `.env.example` and `docs/11-guides/configuration.md` | **Same rule, three files, two blocks.** Neither may satisfy the rule independently and inconsistently. | **Edge `E20`: `B11` first**, so the pattern is established and reviewed once and `B15` copies it. `B15` must not re-derive it; if `B11` is reverted, `B15` still satisfies the rule on its own. |
### §4.4 Every grouping changed from the artifact's own order, and why

**A note on the artifact's ordering content, stated once so no block report mis-cites it.** The
validated artifact publishes **no numbered fix list**. Its ordering content is (i) the finding order
`TRN-001` … `BRW-003`, and (ii) **Checkpoint 4 — R4 Assess Rollout Safety**, which records *unsafe-
ordering pairs: 2* and files them as one finding, `phase05/VAL-502`. This plan honours R4's
*constraints* — and `D2` **discharged both of them structurally**: chain 1's coupling evaporated with
the argfile, and chain 2's shape decision was answered by the owner.

| Artifact's order | This plan | Why it changed |
|---|---|---|
| `TRN-001` first, repaired | **`B10`, deleted, and placed FIRST in execution** | Two independent reasons, and both are new. `D2` answers the finding by removal rather than repair. And because `B10` is upstream of four blocks' anchor sets, it must land before they are written, not after. |
| `TRN-002` as a HIGH before `TRN-001` | **`B1`, second, and re-scoped to MEDIUM** | `D2` deletes its orphan half and moves its surviving half to a different statement in a different module. Priority follows the measured residue, not the original shape. |
| `TRN-005` as a HIGH third | **`B3`, DELETED as moot** | `read_progress` is deleted with the transport and the merge path never emitted `-progress`. §1.8. |
| `TRN-006` as one item across two modules | **`B4`, one half, one module** | `D2` deletes the parse half. The surviving sink half is the observer for the only reader left. |
| `TRN-007` as a policy question | **`B11`, decided by `D3`** | And the decision went the finding's way: an inactivity bound preserves `NET-007`, so the docstring needs amendment, not reversal. |
| `TRN-003` as a scope question | **`B12`, decided by `D1` + the standing Tech Lead decision** | `D1` changed the cost/benefit, not the remedy, and supplied the justification for accepting the Windows residual. |
| `TRN-010` as a MEDIUM finding | **OUT — moot** | An asymmetry between two transports cannot survive one transport's deletion. Cross-reference recorded. |
| `BRW-003` as a MEDIUM best-practice note | **`B15`, ESCALATED to a hard failure by `D4`** | Stealth is a precondition for the tool working on the target class of origin, so a warning is the wrong remedy. |
| `phase05/VAL-501`, `phase05/VAL-502` as the last two items, "record before scheduling" | **`B9`, last** | The instruction is spent: `D2` has been taken and §9 records it. What remains is the correction record, most accurate last. |
| The sixteen findings in ID order | **The order in §4.2** | Driven by the nine edges, by `B10`'s new upstream position, and by risk: deletion first because it re-derives everything else; settled boundaries in the middle; the one open question and the one unowned defect last. |

## §5 Risks

### §5.1 The test-pinning risk

Project rule 2: *if tests conflict with architecture or business logic, fix or remove the tests; never
distort production code for tests.* **Nine** test groups in this plan assert defective behaviour or an
invariant a remedy would break; the full, corrected inventory is §2.6.

**`D2` retires four of them by deleting the code they describe**, and that is the *correct* outcome
rather than a weakened gate: `test_download_with_ffmpeg_uses_argfile_syntax`, `test_temp_argfile_creates_and_cleans_up`,
`TestReadProgress::test_read_progress_stops_on_end`, and `test_check_ffmpeg_available_caches_result`'s
re-scope obligation all disappear with `download_with_ffmpeg`, `_temp_argfile` and `read_progress`.
The rows below that name them are marked **[deleted by `B10`]**. **Two obligations are *replaced*, not
dropped:** `B1`'s ordering assertion moves from the deleted argfile test to a new cookie-cleanup test, and
`B2`'s regression net narrows from six drain tests to the **yt-dlp trio** — and §5.3 records that
narrowing explicitly so no reviewer reads it as a relaxed gate.

| Block | Test | What it pins | Disposition |
|---|---|---|---|
| **B10** | `test_download_with_ffmpeg_uses_argfile_syntax` | **Confirmed pin.** The non-functional `@argfile` invocation, by name. | **Re-scoped, not deleted, not weakened.** The new contract differs per option and the report states which. |
| **B1** | `TestTempArgfile::test_temp_argfile_creates_and_cleans_up` | **Confirmed pin.** The ordering that *is* `TRN-002`. | **Re-scoped**, plus a new assertion that the file is still present while the child runs. |
| **B3** | `TestReadProgress::test_read_progress_stops_on_end` | **Confirmed pin.** The `break` that abandons the child, with the comment `# This should not be read`. | **Re-scoped** to assert the tail reaches the collector. |
| **B8** | `TestBrowserManager::test_browser_manager_launch_failure_raises_extraction_error` | **Confirmed pin.** The message that names neither the binary nor the remedy. | **Re-scoped**; the `ExtractionError` assertion must survive. |
| **B13** | — | — | **YES** | **YES** | MEDIUM | *Planner:* **retained after `D6`.** The remedy shape is fixed (option B), but three call sites change and there is a real fork: **whether the cache gains an invalidation path or is left write-once**, and where the single warning is emitted so arm (b), arm (c) and arm (d) all reconcile with it. *Validator:* arm (b) is **untested today** and is now the sharpest arm, and `D6`'s "no exit-code change" instruction is exactly the kind a well-meaning Implementor over-applies — the Validator must confirm no branch raises and no exit code moves. |
| **B4** | `TestReadProgress::test_read_progress_handles_na_values` | The `N/A` guard that **is** present. | **Must stay green unchanged.** `B4` extends the guard. |
| **B5** | `TestCancelSubprocess::test_returns_false_on_process_lookup_error` | The **correct** "already gone" contract the six sites misread. | **Must stay green unchanged.** `B5` changes the callers, not the function. |
| **B2** | `TestIterProcessLines::*` and the six drain tests | `fire()`'s exactly-once invariant and the drain-vs-`wait()` race. **This is the regression net for the whole plan** — a task-wrapped or raced read breaks six green tests that have nothing to do with this finding. | **Must stay green unchanged.** The gate is the **full suite**, not the four cases in the class. |
| **B6** | `TestEchoYtdlpLine::test_ytdlp_echo_false_*` (4) | With `echo=False` nothing is written to stderr. | **Must stay green unchanged — no edits at all.** |
| **B2**, **B3**, **B8**, **B15** | Plan 08's six `__aexit__` tests; `TestCancelSubprocess`'s three return-contract tests | `B4`'s and `B5`'s contracts and plan 08's browser release. | **Must stay green unchanged.** They are the net for anyone who "tidies" an unrelated block. |

The failure mode this risk creates is uniform: an agent under gate pressure **weakens an assertion
rather than fixes the code**. Every block's Validator is briefed on it, and every re-scoped test must
assert the **new** contract, not a weaker one.

### §5.1a The deletion risk — `B10` is this plan's largest single hazard

`D2` turned a plan whose widest block was a ~30-line reordering into one whose widest block removes
symbols from **four `src/` modules, the package root, seven documentation files and two test files**.
Nothing about it is technically uncertain. Everything about it is **breadth**, and breadth is where an
unreviewed commit loses a live symbol.

| Failure mode | Containment |
|---|---|
| **A symbol is deleted while a live reference survives** — the `mypy`/`ruff` gate catches an import, but not a reference inside a **string**, a **docstring**, a `__all__` entry, or the facade's **symbol-ownership comment**. | `B10`'s acceptance criteria require the deletion list *and* the preservation list to be re-derived by grep after the change, and the report to show both. The ownership comment is called out explicitly, because it is prose about code and no tool checks it. |
| **A test is deleted in a different commit from the code it tests.** | Prohibited explicitly. Rule 2: they travel together, and the commit body must enumerate the deleted test classes by name. |
| **The second `--method` help site is missed.** `cli.py` declares the option twice (`download` and `batch`) with identical help text. Grep finds one instance at a time. | The acceptance criterion names **two sites** and the report must show both diffs. |
| **`docs/99-reference/cli-reference-clean.md` is forgotten**, because it is a **mojibake copy** whose `--method` rows are still perfectly greppable while the rest of the file is not readable. | It is the seventh site in `B10`'s table and in §2.4, with its nature established in §1.8. The prohibition says: fix its `--method` rows, **do not** fix its encoding. |
| **A "helpful" reader preserves a deleted symbol "for compatibility"** — re-adding `HLSDownloader` to `__init__.py`, or keeping `_temp_argfile` because phase 07's `ART-008` cites it. | Prohibition 1 and 2: no shim, no flag, no tombstone, no alias, and remove the enum member outright. Phase 07's row is a phase-07 row; `B10` cites it, does not honour it. |
| **The deletion is mistaken for a regression when a previously-quiet path starts erroring.** | `B15`'s commit body carries the same warning for its own hard failure; `B10`'s carries the breaking-change statement. Both are in §5.5. |
| **`--method auto`'s semantics change without anyone noticing.** | The precise new semantics are stated at the block, D-12 cases 1-3 must survive unchanged, and the arm's stale "try yt-dlp first" comment is a named obligation. |

### §5.1b The escalation risk — `D4` turns a silence into a failure

| Failure mode | Containment |
|---|---|
| **The check lands after `async_playwright().start()`**, so the hard failure still costs a browser launch — the worst of both worlds: a teardown for a condition that was knowable first. | The ordering proof is a **required** test: on the missing-asset path, the driver start is asserted **never called**. Without it, `B15` could pass while achieving nothing over Revision 1's placement. |
| **A deployer reads the new failure as a bug in the change.** | The commit body states the intent explicitly and names the packaging cause (a broken build or partial deployment). |
| **The requirement is quietly downgraded** — a flag, a fallback, a "continue without stealth" path. | Prohibition 3: `D4` is unconditional. A flag for a hard requirement is a way of not having one. |
| **The new failure is confused with `B8`'s** browser-unavailable failure, and one masks the other. | `C15` keeps them as two distinct paths in one method, `B15`'s prohibition 2 forbids a new exception class, and the two blocks' tests are named separately in their acceptance criteria. |
| **The check drifts into `__init__`** and changes the failure mode for every construction site. | Prohibition 4, with the reasoning recorded at the block. |

### §5.1c The opt-in risk — `D5` turns a default on into a default off

| Failure mode | Containment |
|---|---|
| **The default flip is misread as a bug.** Stealth was **always on**. `stealth_enabled = False` **removes it from every existing user's default run.** A user on a bot-protected origin who relied on the always-on posture will start failing extraction and may file that as a regression introduced by this plan. | `B15`'s commit body carries the warning explicitly, §5.5 records it as a behaviour change, and §10 discloses it. **This is the change most likely to be misread, and the block report must say so in the first paragraph, not the last.** |
| **The change interacts with the very reason `D4` was raised.** `D4` said *"bypassing detection is required for the tool to work ... high bot protection"*, and `D5` then made it opt-in. Both are the owner's decisions and `D5` supersedes `D4`, but the tension is real: **on a bot-protected origin, the new default is the setting least likely to work.** | Recorded, not resolved — resolving it would be re-opening `D5`. The block's job is to make the trade-off visible in the field description, the configuration guide and the commit body so the user can set the flag; the block does **not** choose a default other than the one the owner specified. |
| **The flag is checked but the components are not gated**, or vice versa — the posture becomes incoherent (no injected script but the automation flag still suppressed, or the reverse). | `B15`'s test set pins **each** component under **each** flag value, including the case that **component 3 is never gated**. Prohibition 1 forbids a policy engine that could make the gating conditional on anything else. |
| **The asset check fires when stealth is off**, reintroducing the always-on posture in a different shape — and making a default run fail on a build that legitimately omits the asset. | **Prohibition 3**, and the *stealth-off / asset-absent* test asserts **no error, no warning and no check**. That test exists specifically because this is the block's most likely well-meaning over-reach. |
| **The ungated components get "tidied" into the gate** for consistency, changing locale and timezone behaviour for users who never asked. | **Prohibition 2**, and `S1h`'s reasoning is at the block. The `component 3 is not gated` test pins it so a later consistency argument cannot act without failing a test. |
| **`D5` is read as "build something that decides".** The owner's phrasing — *"чтобы скачивающий сам решал нужен stealth или нет"* — can be misread as a request for an automatic decision. It is not: the same sentence says *"это должно быть configurable по умолчанию отключено"* — it should be **configurable** and **disabled by default**. | **Prohibition 1** forbids a heuristic, a policy engine, a profile list, a CLI subcommand and per-site configuration. The plan's reading is stated at the block; if the owner meant an automatic decision, that is a new request, not this one. |
| **`B8` and `B15` are merged** because both land in `__aenter__`. | **`S1i` states the non-merge with its reason** — different verification shapes, and a revert of one must not take the other. `B15`'s prohibition 9 names `B8`'s four anchors as untouchable. |

### §5.2 The prohibitions that survive a fix — this plan's biggest hazard

**Eleven** things the code says, or the validator narrowed, or a decision recorded, that a fix must not
quietly undo.

1. **The yt-dlp "no application-level download timeout" decision — and `D3` PRESERVED it.** The
   docstring states that no application-level download timeout is imposed, avoiding premature kill of
   legitimate long downloads. `D3` chose an **inactivity** bound, not a whole-operation budget, so
   **this sentence is still true after `B11` lands**: a download that keeps producing output is never
   killed, however long it runs. Revision 1 assumed the sentence would have to be reversed and gated
   the block on a product question; **that was wrong, and `D3` corrected it.** `B2`, `B4`, `B5`, `B6`
   and `B10` must not add a timeout to any transfer stage, and the sentence is **byte-identical** after
   each of them. Only `B11` may amend it, and only to name the new setting and its inactivity
   semantics.
2. **`NET-007`'s withdrawn whole-operation budget — still withdrawn.** `D3` did not reinstate it.
   `B11` is an **inactivity** bound and **may not** become a whole-operation budget. Phase 03's
   decision stands, and `B11`'s liveness test is the proof that it was preserved rather than quietly
   reversed.
3. **`ffmpeg_utils.py` is a leaf.** It imports only `..exceptions` and `..utils.formatting`. The stop
   state reaches `iter_process_lines` and `read_progress` **as a parameter** precisely so it can stay
   a leaf. `B2`, `B4`, `B5`, `B6` and `B11` must not add an import to it.
   **`B14` is the single knowing exception**, and it is the block's most conspicuous judgement: it
   adds `sanitize_text_for_log` so the two merge sinks stop emitting raw child output. The alternative
   — routing the text out to the caller to sanitise — would move a security-relevant operation away
   from the sink that emits it. `utils` is a layer the module is already permitted to import from, and
   **`B14`'s report must say this explicitly** rather than let the new import look incidental.
4. **`cancel_subprocess` is correct as documented.** "True if process was cancelled, False if process
   was already gone." The defect is in its readers. **`B5` changes the two surviving readers; `B12`
   and `B11` may not change the contract.** `D2` reduces the readers from six to two, which makes the
   remaining misreading more concentrated, not less.
5. **`download_with_ffmpeg`'s `finally:` guarantee is no longer an obligation** — `D2` deletes the
   method. `B1`'s surviving instance is `_download_with_ytdlp`'s cookie `finally:`, and its guarantee
   is **narrower**: the child is always reaped or cancelled before it runs, so a failure there masks
   an outcome but cannot orphan a child. **No block may harden it as if it could.**
6. **`_temp_argfile`'s `0o600` request** — moot. `D2` deletes the helper, the chmod and its
   `SEC-001`/`SEC-003` comment together. Phase 07's `ART-008` and `ART-007` are unaffected as phase-07
   rows; `B1` cites `ART-008` as a **precedent** and edits nothing.
7. **`_await_first_and_cancel_others` settles its losers before returning, by plan 08's design.** `B4`
   may report a failed task's exception; it may **not** silently reverse that decision record. If it
   reverses any part, the report names the part and the reason. `D2` raises the stakes: after the
   deletion this helper observes the **only** reader the product has.
8. **`_echo_ytdlp_line` writes nothing when `echo=False`.** Four green tests hold it. `B6` must not
   make `echo=False` write anything — including "redacted" output. `B14` **must not touch it at all**:
   the console echo is phase 06's `SEC-005` under the `Q5` split.
9. **`sanitize_text_for_log` matches URLs only.** `B7` must not change that — the matcher is phase
   06's `SEC-006`. `B14` must not change it either; `B14` only *applies* the transform. And both merge
   sinks must transform **before** truncating, or a 200-character cut can split a URL and defeat the
   redaction.
10. **`--method auto`'s arm comment.** It reads "try yt-dlp first (more reliable), segment download for
    resume" — a **two-transport** sentence that `D2` makes false, since there is no "first" any more.
    `B10` must correct it, and the corrected semantics ("resolve cookies per `cookie_source`, then
    download via yt-dlp with segment resume as the fallback") are stated at the block.
11. **`stealth.min.js` is a declared artefact and a hard requirement under `D4`.** `B10` must not
    remove the `pyproject.toml` declaration, and `B15` must not edit `pyproject.toml` at all. A missing
    asset now means a broken build or a partial deployment, and `B15`'s hard failure is the correct
    response to exactly that.

### §5.3 Implementation risks

| Risk | Blocks | Containment |
|---|---|---|
| **`B10` deletes a live symbol.** The widest hazard in the plan; §5.1a carries the full treatment. | B10 | Deletion **and** preservation lists re-derived by grep after the change; the facade's symbol-ownership comment called out because no tool checks prose. |
| **`B1`'s fix is propagated into a helper `B10` is deleting**, or into a shared cleanup abstraction for what is, after the deletion, a single site. | B1 | Prohibition 1 and 2; `C17` records the pair as a prohibition rather than an ordering. |
| **`B2`'s partial fix is worse than nothing** — the reader returns without draining, or the reassembly path becomes a new unbounded wait. | B2 | §3.18's binding list survives every option: `fire()` exactly-once, `watch_task` awaited, no unbounded wait in the new path, EOF and stop still distinguishable. The **full suite** is the gate, and after `D2` the net is the yt-dlp trio plus the exactly-once assertion. |
| **`B4` reverses plan 08's cancellation contract while making failures visible**, or — the specific over-correction — re-raises the failed task's exception, turning a drain into a crash. | B4 | §3.20's recommendation plus prohibition 7. `D2` raises the stakes: this helper now observes the only reader the product has. |
| **`B5`'s fix is satisfied by deleting the warning.** | B5 | The negative case is mandatory: a child **still running** after the ladder must still produce the record. |
| **`B6` bounds the buffer in the direction that loses the message explaining the failure.** | B6 | §3.21 rejects (b); the failure-path test asserts the message is still usable. |
| **`B11` implements the inactivity bound as a total one**, silently reversing `NET-007` behind a correct-looking setting name. | B11 | The **liveness** test is mandatory: a child that keeps emitting output does not trip the bound, however long it runs. The field description must say "inactivity" in its own words. |
| **`B11`'s bound does not reap the child on timeout.** | B11 | The timeout arm is required to re-enter the ladder and re-raise, and the test asserts **both** halves. A bare `asyncio.wait_for` is prohibited because it introduces the orphan class `B1` and `B5` close. |
| **`B12` implements a Job Object anyway**, "because it is the only complete fix" — which it is, and which the decision rejected. | B12 | §3's option table records the rejection and its cost; prohibition 1 names all three rejected mechanisms. `D1` is recorded as the reason the Windows residual is acceptable. |
| **`B13` presents the Windows outcome as a closure.** | B12 | The platform-asymmetry test asserts that on Windows the grandchild **survives**, and the limitations entry plus the commit body both state the residual. |
| **`B14` truncates before transforming**, so a 200-character cut splits a URL and defeats the redaction. | B14 | The ordering proof test, and prohibition 3. |
| **`B15` places the check after `async_playwright().start()`**, costing a browser launch for a knowable condition. | B15 | The ordering proof is a required test: the driver start is asserted never called. §5.1b. |
| **`B15` is downgraded to a warning**, or the requirement is given a flag. | B15 | Prohibition 1 and 3. `D4` is unconditional; a flag for a hard requirement is a way of not having one. |
| **`B15`'s check is placed after `async_playwright().start()`**, costing a browser launch for a knowable condition. | The ordering proof is a required test: the driver start is asserted **never called**. §5.1b. `D5` makes it conditional, which raises the stakes — the user who opted in is the one for whom failing fast matters. |
| **`B15` is downgraded to a warning** on the enabled path, or the flag gains a second "warn and proceed" switch. | Prohibition 4 and 6. `D5` is a boolean with three behaviours and no fourth. |
| **`B13` over-applies `D6` into a hard failure**, or under-applies it into "warn and carry on" without using the probe's answer. | Prohibition 1 (no branch may raise or change an exit code) and requirement 2 in the block (the answer is USED at the single call site). `D6`'s four requirements and one prohibition are tabulated at the block. |
| **`B11` and `B15` each satisfy the three-place rule independently and inconsistently** — a documented variable the model has never heard of, or an `.env.example` value it rejects. | **`C19`/`E20`**: `B11` lands first and `B15` copies the established pattern. Phase 02 found this exact bug class. |
| **A test-pinned assertion is weakened instead of the code fixed.** | B10, B13 | §5.1. |
| **A structlog / stdlib-`logging` slip.** | all | §5.6. |
| **A new constant as a bare literal instead of a `StrEnum` member or a frozen dataclass.** | B4, B6, B11, B13, B15 | Rule 10; the reviewer's first question on any new value. `B15`'s `ErrorCode` member is the canonical case. |
| **A stop-state `Event` leaked between tests** via a test that sets `_shutdown_event_ctx` without resetting its token. | B2, B4, B5, B6, B11 | §2.3's token-idiom requirement. |

### §5.4 Rollout risks

| Risk | Detail |
|---|---|
| **The untracked `tmp/` and the eight tracked `.ai/plans/` deletions ride along into a commit.** | §2.5's landing rule. This plan's largest **process** risk, because it can contaminate every block at once. `tmp/` is not gitignored and will appear in `git status`. |
| **The `VAL-` namespace.** An unqualified `VAL-501` makes a reader validate the wrong documents — in this case phase 07's pipeline-document range rather than phase 05's cross-phase conflict. | Mitigated by the convention at the top of this plan, which is a **naming decision taken before any block is written**, not a review step. |
| **`phase05/VAL-502` chain 1, which this plan ordered around, is gone** — so the ordering that satisfied it is no longer load-bearing, and a reader following Revision 1's graph would be sequencing work for no reason. | `D2` discharges both chains structurally: chain 2 by the owner's decision, chain 1 by the deletion. §1.3 `S1b`/`S1e`, and `E1` in §4.1 is marked **retired**. |
| **A decision-gated block is scheduled before its question is answered.** | **Down from five gates to one.** `B10`, `B11`, `B12` and `B14` are decided; only `B13` (`Q4`) and `B16` (`Q6`) remain. §3's preamble carries the gate-status table so the count cannot be misremembered. |
| **`B10`'s deletion is treated as a bug and reverted**, because "we might need it back". | The owner's words are quoted in `B10`'s heading and §9: *"If it will be needed we will add it in future."* Re-adding the transport **re-filers `TRN-005`** — `B3`'s deleted block says so explicitly, so a future Implementor who reinstates the transport is told what returns with it. |
| **A withdrawn claim reintroduced in prose.** The source report `.ai/audit/05-subprocess-browser/findings.md` still contains every withdrawn and severity-corrected sub-claim, and now also describes a transport that `D2` deleted. | **Every block cites the validated artifact only.** A block report that implements a withdrawn recommendation is wrong on its face; one that re-implements a deleted transport is worse. |
| **A block edits a file another phase or engagement owns.** | `B9` <-> `.ai/audit/**` (read-only); `B11` <-> `docs/11-guides/configuration.md`'s existing `download_timeout` row (plan 07 `C12`) and <-> `NET-007`; `B1` <-> phase 07's `ART-008`; `B14` <-> phase 06's `SEC-005`/`SEC-006` (now a decided split, and `B14` takes only the unowned sinks); `B10` <-> phase 06's `SEC-004`; `B8`/`B15` <-> plan 08 `B4`'s `__aexit__`. Each is a **stated boundary with a negative acceptance criterion**. |

### §5.5 Compatibility risks

**`D2` converts this from a section about behaviour changes into a section about two deliberate
breaking changes.** Both are authorised; neither is an accident.

| Risk | Detail |
|---|---|
| **`HLSDownloader` and six `downloader.py` re-exports disappear from the public API.** | `vkdownloader/__init__.py` publishes `__all__ = ["HLSDownloader", "QualitySelector"]`, and `downloader.py` is an explicit backward-compatibility facade whose own comment says downstream code "still imports from here". `D2` removes `HLSDownloader` from the package root and `HLSDownloader`, `_temp_argfile`, `_format_argfile`, `FfmpegProgress`, `ProgressParser` and `read_progress` from the facade, plus `__all__` and the symbol-ownership comment lines. **This is a breaking import-level change** and the commit body must say so plainly. It is authorised by `D2` and it is the *point* of the deletion, not a side effect to be minimised — a kept alias would be exactly the tombstone the owner ruled out. |
| **`--method ffmpeg` becomes a usage error (exit `2`).** | Typer validates the choice against the enum before `perform_download` is reached, so an installed script carrying `--method ffmpeg` gets the parser's invalid-choice error and the already-documented usage-error code. **`test_cli.py`'s `--method invalid_method` case proves this path and must stay green unchanged** — it becomes the proof that the breaking change is clean. |
| **`--method auto` and `--method yt-dlp` become the same transport.** | Both resolve to `download_with_ytdlp_with_resume_fallback`; the only difference is that `auto` skips `_resolve_cookies` when `cookie_source == NONE`. That is a **behaviour change for `--method auto` scripts that expected a second transport to be tried**: there is no longer a fallback *from ffmpeg* because there is no ffmpeg download. D-12 cases 1-3 already assert `auto`'s cookie semantics and must survive the deletion unchanged. |
| **`DownloadMethod.AUTO` is kept even though it is now nearly redundant with `YTDLP`.** | Deliberate. Removing it would change the CLI's **default value** for `--method`, which is a larger breaking change than `D2` authorised — the owner removed `--method ffmpeg`, not `--method` or its default. `AUTO` is not a tombstone: it is the live default, and its distinct cookie semantics are load-bearing. Its **arm comment** is the thing that must change. |
| **The `--method` help text changes at two sites.** | `cli.py` declares `--method` on both `download` and `batch`, each with the help string "Download method: yt-dlp, ffmpeg, or auto". Both must drop `ffmpeg, `. Missing the second is the single most likely miss in this block, because it is a copy of the first and grep finds only one instance at a time. |
| **`iter_process_lines`'s contract changes** (`B2`). | Two consumers remain, both in `ytdlp_downloader.py`. The **signature must be unchanged**; only the read's behaviour tightens. |
| **`_await_first_and_cancel_others`'s contract may change** (`B4`). | Two call sites remain, both discarding the return. If the contract changes, both are reviewed in the same change and plan 08's decision record is not silently reversed. |
| **`cancel_subprocess`'s behaviour changes** (`B12`). | Two boolean-reading call sites plus one return-ignoring site. Option (B) adds a `killpg` branch **on POSIX only** — a behavioural change there, and a **partial** closure on Windows, which must be stated rather than implied. |
| **A new `Settings` field** (`B11`, and only there). | `download_stall_timeout` is a new bounded field with a default, so existing settings keep their meaning. But `model_config`'s `extra="forbid"` makes an unrecognised `VKDOWNLOADER_*` an error, so the three-place rule is a correctness requirement, not a courtesy: field description, `.env.example`, and the configuration guide. |
| **A download is killed after a silent period** (`B11`). | Behavioural and **correct per `D3`**. A download that has produced no output for the configured period is terminated through the existing ladder. This is not a total budget: `NET-007` is preserved and the liveness test proves it. |
| **`echo=False` diagnostics get quieter** (`B6` option (d)). | Batch mode's `download_failed` record would lose its `error` field in exactly the mode that already cannot see the console. Acceptable only if the report says so. |
| **Stealth is removed from every existing user's default run** (`D5`). | `stealth_enabled` defaults to `False`, and the two anti-detection measures were previously unconditional. A user on a bot-protected origin must now set `VKDOWNLOADER_STEALTH_ENABLED=true`. **This is what the owner asked for and it is the second-largest behaviour change in this plan after `B10`'s deletion.** It is disclosed in `B15`'s commit body, recorded here, and in §10. It interacts with the reason `D4` was raised — on a bot-protected origin the new default is the setting least likely to work — and that tension is **recorded, not resolved**, because resolving it would re-open `D5`. |
| **A missing `stealth.min.js` becomes fatal only for users who opted in** (`D5`). | Previously the asset's absence was always silent (`BRW-003`); under `D5` it is fatal **only** when `stealth_enabled` is `True`. For a default run it is now **never consulted**, so a build without the asset is unaffected — a strict improvement over both `D4`'s unconditional failure and the original silence. |
| **`B7`, `B9`, `B14` and `B16` change no product behaviour** (or, for `B14`, only what reaches a log record). | Recorded so a reader does not mistake their absence from the behavioural summary for an omission. `B14` *does* change what two log records contain; that is its whole content. |

### §5.6 The `structlog` trap — a doc-vs-code divergence flagged, not fixed

`.kilo/rules/project.md` rule 12 literally prescribes `logger = logging.getLogger(__name__)`. The
**codebase universally uses `structlog`**: every module does `from structlog import get_logger` then
`logger = get_logger(__name__)`, and `config.setup_logging` wires `structlog.stdlib.LoggerFactory`
over `logging.basicConfig` with a `JSONRenderer`/`ConsoleRenderer` split. Two deliberate exceptions
exist and are not to be touched: `config.py`'s `import logging`, which configures the stdlib handler
structlog wraps, and `progress_display.py`'s re-pointing of that handler's stream.

**Decision, identical to plans 07, 08 and 09 and binding here: follow the code, not the rule text, and
do not "fix" the rule file as part of phase 05.** Changing `.kilo/rules/project.md` is an
audit-pipeline change, not a product change.

**`B8` is where this bites hardest.** Its remedy must be written against **structlog's** API. A remedy
written against stdlib `logging` semantics would not behave as described, and the encoding mechanism
it interacts with (`B16`) lives in a stdlib handler that structlog wraps. **Binding on `B8`, `B15` and
`B16`.**

### §5.7 Documentation risks

| Risk | Detail |
|---|---|
| **`TRN-001` leaves seven sites asserting a non-working mechanism** (§2.4), **one of them a duplicate** of another. | Editing `cli-reference.md` without `cli-reference-clean.md` leaves the copy lying, and the two have already drifted in other ways. `B10`'s prohibition names the duplicate. |
| **A behaviour change leaves its justifying comment lying.** | `_temp_argfile`'s docstring and `download_with_ffmpeg`'s INT-001/SEC-001 block assert the `@file` mechanism works (`B10`). `sanitize_text_for_log`'s docstring and two `SEC-002:` comments assert a redaction capability the regex lacks (`B7`). `_download_with_ytdlp`'s no-timeout decision (`B11`). `download_with_ffmpeg`'s `finally:` guarantee (`B1`). `check_ffmpeg_available`'s hint text predicts an outcome its own code does not deliver (`B13`). `iter_process_lines`' docstring (`B2`). `create_stealth_page`'s `Returns:` line (`B15`). |
| **`docs/STRUCT.md` omits `ytdlp_downloader.py`.** | Phase 09's subject by R-E, recorded upstream and not re-filed. **No block may edit it**, and no block's report may present the omission as newly discovered. |
| **Documentation noise for self-evident changes.** | `B9` is a documentation block and needs no doc edit — its edit **is** documentation. No block adds a new doc page. |
| **A block writes a configuration value that the model rejects.** | No block in this plan adds a `Settings` field, so the three-place rule does not bind — except `B11`'s possible edit to `download_timeout`'s **field description**, which must construct against `Settings` and be recorded in the report. |

### §5.8 The boundary no block may cross

**No finding in this corpus asserts what a real VK origin does.** Every live claim is structural: a
measured exit code, a measured `output_created`, a measured RSS growth, a read of a return
annotation, a control-flow argument, an interpreter constant. The artifact that produced this plan
had no network access.

**Therefore, binding on every block and every verification step:**

1. **No block may be justified by** "a real VK origin would 403 the part", "a real CDN would serve
   `*.m3u8` from this host", "a real Chromium would hang on `browser.close()`", or any equivalent.
   Those are the assumptions the audit explicitly declined to make.
2. **No verification step may require network access.** `tests/test_packaging.py` is the only test
   that may touch the network and it skips off-CI. This plan adds none.
3. **Every new test uses a local stand-in**, a `MagicMock`, an `AsyncMock` process, or a real
   `asyncio.StreamReader` fed by `feed_data`. There is no `aiohttp` fixture, no ffmpeg-subprocess
   fixture and no fake clock; **none may be added for these blocks.** The suite's zero-`aiohttp`
   property is a fact about the codebase, not a gap to close here.
4. **`B9`'s verification record must not contain a verdict on `SEC-004`, `SEC-005` or `SEC-006`.** It
   records what is claimed and by whom. Writing what the finding "should become" is the over-claim the
   validator warned against.
5. **`B1`'s and `B10`'s subprocess behaviour is verified against real children only where the artifact
   did** — and `B10`'s control experiment re-runs the real muxer **before** it starts, because the
   whole option analysis depends on the muxer still lacking `@file`.
6. **No block may claim a route into the wedge is closed on the strength of another block's fix.**
   "The reader cannot die now that `B2` landed" is not a claim any block may make on its own; each
   block's report states what **it** closed.

---

## §6 Agent usage per block

**Which of Auditor / Researcher / Planner / Validator each block requires, and why.** The rule applied:
risk and **real uncertainty** buy agents; a mechanical change with a determined remedy needs none.
Low-risk mechanical work is **Implementor only**.

**`D2`–`D4` moved five blocks out of the "gated, unknown remedy" column into the "decided, now
implement" column, and that is exactly what the agent counts below record.** A decided block keeps its
Planner if the *implementation* still has a fork; it loses its Researcher if there is nothing left to
research.

| Block | Auditor | Researcher | Planner | Validator | Risk | The question that earns each agent |
|---|---|---|---|---|---|---|
| **B1** | — | — | — | **YES** | MEDIUM | **No Planner.** The re-scoped remedy is determined: catch `OSError` around the cookie unlink, record it, do not replace the return value. One site, one line, no fork. *Validator:* the re-graded priority must be justified in the report (the orphan half is closed by `D2`), and the block must not have propagated itself into a helper `B10` deleted. |
| **B2** | **YES** | — | **YES** | **YES** | HIGH | *Auditor:* **the reader's interaction with `f6ed0cf`'s rewrite** — the watcher task, the `fire()` exactly-once invariant and the `finally:` that awaits the watcher must all be re-derived against the landed code, because the artifact was composed before that rewrite. *Planner:* which oversized-line shape (§3.18) survives a measurement. *Validator:* **mandatory** — a partial fix here is worse than no fix, and the gate is the full suite against the **yt-dlp** net `D2` left behind. |
| ~~**B3**~~ | — | — | — | — | — | **DELETED.** Moot by `D2`; no agents, no work. §1.3 `S1a`. |
| **B4** | — | — | **YES** | **YES** | HIGH | *Planner:* how "visible" is expressed without reversing plan 08's cancellation contract (§3.20) — and the block is now **one** half in **one** module, so the fork is smaller but the consequence is larger: this helper observes the only reader the product has. *Validator:* the discrimination case is what stops the fix being satisfied by logging every finished task. |
| **B5** | — | — | — | **YES** | MEDIUM | **No Planner.** The remedy is determined and got *smaller*: two sites, guarded on `process.returncode is None`. *Validator only* — and the specific job is proving **no warning was deleted**, which is the one way this block can pass trivially and wrongly. |
| **B6** | — | — | **YES** | **YES** | MEDIUM | *Planner:* the bounded-buffer shape (§3.21) and the head-vs-tail decision. Unchanged by `D1`–`D4`. *Validator:* the four `echo=False` tests must stay green **with no edits at all**. |
| **B7** | — | — | — | **YES** | LOW | **No Planner.** Two false claims, one mechanical remedy, no behaviour change. *Validator only* — to confirm no behaviour changed, the accurate first sentence survived, and the block did not extend the matcher (phase 06's `SEC-006`). |
| **B8** | — | — | **YES** | **YES** | HIGH | *Planner:* how much of the cause is carried and in what shape (§3.22). *Validator:* a **confirmed test pin** is re-scoped, and the re-scoped test must keep asserting that the application's own exception type reaches the caller. Unchanged by `D1`–`D4`, except that `D4` puts a second hardened path in the same method (`C15`). |
| **B9** | — | — | **YES** | **YES** | LOW/MEDIUM (process) | *Planner:* the record's content is now the **outcome** of both chains plus the sharpened `phase05/VAL-501` statement — a judgement about what a reader six months out must be able to see, not a copy. *Validator:* proving `.ai/audit/**` untouched, that **no verdict** was written about phase 06's findings, and that every `VAL-` id is qualified. |
| **B10** | — | — | **YES** | **YES** | CRITICAL (breadth) | **No Auditor and no Researcher — and that is the change.** Revision 1 needed both: the Auditor to re-derive the muxer fact and the Researcher to investigate option (C)'s alternative mechanisms. `D2` deleted every option, so there is **no muxer fact left to re-derive and no mechanism left to research.** *Planner:* **retained**, because a deletion of this breadth still has a genuine fork — where exactly the `async with` block's lifetime, the `__all__` pruning and the ownership-comment rewrite land — and because the `auto`-semantics statement must be written rather than assumed. *Validator:* **mandatory**, and its job is the one §5.1a exists for: proving no live symbol was deleted, that the preservation list survived, and that **no shim, flag or tombstone** was left behind. |
| **B11** | — | — | **YES** | **YES** | MEDIUM | *Planner:* the **inactivity** semantics — what counts as liveness, and where the clock is reset — is a real implementation fork and the one place `D3` left open. Also the field description, which is the only place an operator learns the difference from `download_timeout`. *Validator:* the liveness test must genuinely prove `NET-007` was preserved, and the commit must not claim the decision sentence was left alone when it was amended. |
| **B12** | — | **YES** | **YES** | **YES** | HIGH | **Auditor dropped** — the descendant behaviour no longer needs re-deriving against a decision that is made, and the reproduction stands. **Researcher retained**: whether a POSIX session plus `killpg` is equivalent to what a Windows job object provides, and what the residual actually costs, is a platform question no one in this plan has answered, and the block must state the residual honestly. *Planner:* the concrete per-platform shape and the POSIX-only guard. *Validator:* **the block that most needs one** — a boundary that only *partly* closes a HIGH finding must not be reported as closing it. |
| **B13** | — | — | **YES** | **YES** | MEDIUM | *Planner:* **retained after `D6`.** The remedy shape is fixed (option B), but three call sites change and there is a real fork: **whether the cache gains an invalidation path or is left write-once**, and where the single warning is emitted so arm (b), arm (c) and arm (d) all reconcile with it. *Validator:* arm (b) is **untested today** and is now the sharpest arm, and `D6`'s "no exit-code change" instruction is exactly the kind a well-meaning Implementor over-applies — the Validator must confirm no branch raises and no exit code moves. |
| **B14** | — | — | **YES** | **YES** | MEDIUM | **Researcher dropped** — Revision 1 needed one to design a path-matching regex. That is **phase 06's `SEC-006`** under the `Q5` split, and this block no longer designs anything: it applies an existing transform at two call sites. The duplicate-ownership hazard that justified the Researcher is **retired by the split**. *Planner:* retained for the one real fork — **transform-then-truncate versus truncate-then-transform**, which the ordering test exists to catch. *Validator:* confirm the block is not editing the matcher or the console echo, i.e. that it stayed inside the unowned sinks. |
| **B15** | — | — | **YES** | **YES** | HIGH | **Planner — retained, and the reason changed.** `D4`'s block had a determined remedy and no Planner; `D5` gives it back one, because the block now decides **where the flag is read at two consumption points**, **where exactly the conditional check sits**, and **what the field description must say** — four coupled statements across two modules and eleven documentation sites, which is not mechanical. *Validator:* **mandatory and the gate is the ordering proof** — a check that sits after `async_playwright().start()` satisfies every other assertion while achieving nothing. Plus `S1i`: it must confirm `B8`'s four anchors are untouched. |
| **B16** | — | — | **YES** | **YES** | LOW-MEDIUM, unowned | *Planner:* **retained.** `D7` settles adoption, but not construction — whether the encoding-safe value is set on the handler or supplied at construction is a small real fork, and the report must state why `PYTHONIOENCODING` and `sys.stderr.reconfigure` were rejected. *Validator:* the block still has **no finding behind it**, so its job is to confirm the adoption is the Tech Lead's decision and that no per-callsite `try` was written instead. `D7`'s fourth rationale is **not borne out by the code** and the Validator must not let it into the commit body as fact. |

**Aggregate agent budget.** 15 live blocks (one deleted): **9 require a Planner**, **15 require a
Validator**, **1 requires a Researcher** (`B12`), **1 requires an Auditor** (`B2`).

**What the decisions did to the budget, stated so every change is auditable rather than just smaller:**

*From `D2`–`D4`* — Auditors 2 → 1, Researchers 3 → 1, Planners 11 → 9. Every drop is explained by a
decision removing the question that bought the agent: `B10` lost its **Auditor** (no muxer fact left to
re-derive) and its **Researcher** (no alternative mechanisms left to investigate) but kept its
**Planner**; `B12` lost its **Auditor** and kept its **Researcher**, because the POSIX/Windows
equivalence is still unanswered and the block must state the residual honestly; `B14` lost its
**Researcher**, because the matcher is phase 06's and the ownership hazard the Researcher was bought
for is retired by the `Q5` split.

*From `D5`–`D7`* — **Planners 9 → 9, but the composition changed**, and it is worth seeing why:

| Change | Effect |
|---|---|
| `D5` gave **`B15`** a Planner back | `D4`'s block had a determined remedy — "raise instead of warn" — and `S1i`'s non-merge plus two gated components, a conditional check, a new settings field and eleven documentation sites is not a mechanical edit. **+1** |
| `D5` cost **`B8`** nothing | `B8` is unchanged by `D5` — its anchors, its remedy, its tests and its Planner all stand. `S1i`'s only effect is the ordering, not the work. **0** |
| `D6` left **`B13`** with a Planner | The option is fixed but the cache shape and the single-warning placement are still real forks. **0** |
| `D7` left **`B16`** with a Planner | Adoption is settled; construction is not. **0** |
| The `Q4`/`Q6` gates closed | Two blocks that were *gated* became executable. Neither ever lacked a Planner, so the Planner count is unchanged — **what changed is that no block is blocked on a person.** |

**The headline for this revision: the agent count barely moved, and the plan went from two open questions
to none.** That is the measure of whether the decisions were worth making.

**Honesty check against the brief.** No Planner is assigned to a mechanical edit: `B1`, `B5` and `B7`
have none, and each says why in the block. **No CRITICAL block is left without a Planner**: `B10` — the
widest and the CRITICAL finding — keeps its Planner and its mandatory Validator. **Every block now has a
Validator**, including the three that are Implementor-plus-Validator only, because every block carries at
least one negative acceptance criterion that only an independent read can confirm — and after `D5` the
three highest-risk negatives are a default flip (`B15`), an ordering proof (`B15`) and a non-merge
(`S1i`).

## §7 Task specifications

One specification per block, in `.ai\tasks\templates\task_template.yaml` shape. **This is the
`{task_description}` format the block-level Planner uses at execution time.** Semantic code units only
— files, modules, classes, functions, methods, guard expressions. **Never line numbers.**

An Implementor is handed **one** of these and nothing else. Read your block in §3 first if any
question in the spec is unclear; the spec does not restate the block. **`B3` has no work item** — it is
deleted, and its spec exists only so no one schedules it.

**Revision 2.** Specs rewritten for every block the `D1`–`D4` decisions changed: `B1`, `B3` (deleted),
`B4`, `B5`, `B7`, `B10`, `B11`, `B12`, `B13`, `B14`, `B15`. `B2`'s regression net is restated after
`D2` shrank it. `B6`, `B8`, `B9` and `B16` are confirmed unaffected or carry a one-line marker; their
specs stand as written in Revision 1 except where noted.

---

### B1

```yaml
id: plan10-b1-ytdlp-cookie-destroy-cannot-replace-the-outcome
title: Make the yt-dlp transport's cookie-file destruction incapable of replacing the outcome
priority: medium
depends_on: [B10]

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B1 — Make the yt-dlp transport's cookie-file destruction incapable of replacing the
  download's outcome
source_blocks: ["B1"]
source_findings: ["TRN-002"]

description: >
  RE-SCOPED by D2. TRN-002's orphan half is moot: its only instance was `_temp_argfile`'s `finally:`,
  which D2 deletes with the transport. The SURVIVING half is at `_download_with_ytdlp`'s `finally:`,
  which carries the identical pattern — `if cookie_file is not None and cookie_file.exists():
  cookie_file.unlink(missing_ok=True)` — and `missing_ok=True` suppresses only `FileNotFoundError`. A
  `PermissionError` from an indexer or scanner holding the file propagates out of the `finally:` and
  replaces the method's return value, turning a clean `None` into a raised `OSError`.

  THE RESIDUE IS BOUNDED, and the report must say so: the child CANNOT be orphaned here, because on
  every path the `finally:` runs the child has already been reaped (both the normal and the
  non-zero-returncode paths pass `await process.wait()`) or cancelled (the `except
  asyncio.CancelledError` arm cancels then re-raises). So this is an outcome-masking defect, not a
  process leak, and the priority is re-graded HIGH -> MEDIUM with that reason.

  `phase05/VAL-502` chain 1 no longer applies: the TRN-001 <-> TRN-002 coupling evaporated with the
  argfile rather than being satisfied by ordering.

goals:
  - a destroy that raises OSError does not propagate and does not change the return value on any arm
  - the failure is recorded, naming the path, at a level a default run shows
  - the file is still removed when the destroy succeeds, and the success record is still written
  - the child's termination ladder and the `except asyncio.CancelledError` arm are untouched
  - nothing is added to a helper D2 deletes, and no shared cleanup abstraction is introduced

files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _download_with_ytdlp
    semantic_anchors:
      modify:
        - type: function_call
          value: "cookie_file.unlink(missing_ok=True)"
        - type: function_call
          value: "logger.debug(\"cookie_file_cleaned_up\", path=str(cookie_file))"
      read_only:
        - type: except_clause
          value: "except asyncio.CancelledError:"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestYtDlpSubprocessShutdown
    semantic_anchors:
      insert_after:
        type: class
        name: TestYtDlpSubprocessShutdown

changes:

  - action: modify
    description: >
      Catch `OSError` around the cookie unlink in `_download_with_ytdlp`'s `finally:`, record a warning
      naming the path, and let the `finally:` complete normally so the method's return value survives.
      Catching `OSError` is the floor (`missing_ok=True` already covers `FileNotFoundError`); catching
      `Exception` is prohibited because it would swallow the `KeyboardInterrupt`/`CancelledError` family
      this module deliberately propagates.
    code_hint: |
      finally:
          if cookie_file is not None and cookie_file.exists():
              try:
                  cookie_file.unlink(missing_ok=True)
              except OSError as exc:
                  logger.warning("cookie_file_cleanup_failed", path=str(cookie_file), error=str(exc))
              else:
                  logger.debug("cookie_file_cleaned_up", path=str(cookie_file))

  - action: add_test
    description: >
      Add cases inside `TestYtDlpSubprocessShutdown`. (1) A destroy that raises `OSError` (patch the
      unlink — do NOT hold a real handle, which makes the test machine-dependent) and the call returns
      NORMALLY on all three paths: success, non-zero returncode (`None`), and shutdown (`None`).
      (2) The negative case, so the fix cannot pass by deleting the cleanup: the file IS removed on
      success and `cookie_file_cleaned_up` is written. (3) The ordering assertion that makes the
      residue honest: on the failed-destroy path the child has already been waited or cancelled before
      the `finally:` runs — assert on the observable effect (the process is reaped), not a private
      attribute.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT mirror this fix into `_temp_argfile` or any other argfile helper — B10 DELETES them. If
      the deletion has not landed, this block waits (E2); it does not write code against code that is
      about to disappear. MUST NOT add a shared cleanup helper, a context manager, or any new
      abstraction: after B10 there is ONE site, and one site does not need a helper (rule 5). MUST NOT
      change the `except asyncio.CancelledError` arm or the termination ladder. MUST NOT swallow the
      failure silently — it must be recorded with the path. MUST NOT change the `cookie_file.exists()`
      guard beyond what the failure handling needs. No new module, no dependency, no `Settings` field.
    code_hint: |

acceptance_criteria:
  - A destroy that raises OSError does not propagate and does not change the return value on any arm
  - The failure is recorded once, naming the path, at a level a default run shows
  - The file is still removed on the success path and cookie_file_cleaned_up is still written
  - The child is reaped or cancelled BEFORE the `finally:` runs (new test)
  - The `except asyncio.CancelledError` arm and the termination ladder are byte-identical
  - TestYtDlpSubprocessShutdown and the yt-dlp drain trio are green UNCHANGED
  - >
    `_download_with_ytdlp`'s "no application-level download timeout" docstring is byte-identical —
    D3 preserved that decision and this block does not touch it
  - Nothing was added to a deleted helper and no cleanup abstraction was introduced
  - >
    The COMMIT BODY states the measured before/after, that the orphan half is closed by D2, and that the
    priority is re-graded to MEDIUM with the reaping-ordering reason
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B2

```yaml
id: plan10-b2-reader-survives-oversized-line
title: Make one oversized child line incapable of killing the reader
priority: high
depends_on: []

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B2 — Make one oversized child line incapable of killing the reader
source_blocks: ["B2"]
source_findings: ["TRN-004"]

description: >
  `iter_process_lines` calls `await stream.readline()` with no bound, and no spawn site in `src/`
  passes `limit=`, so the effective limit is `asyncio.streams._DEFAULT_LIMIT = 65536`. A single child
  line at or above that raises out of the generator into the reader task, the task dies, and nothing is
  left draining the child's stream. The reaper on this platform returns only once the returncode is
  set AND every pipe reaches EOF, so an undrained pipe means `await process.wait()` is structurally
  incapable of returning — even after `kill()`.

  ANCHOR WARNING: `iter_process_lines` was REWRITTEN by `f6ed0cf` (plan 08 `B1`). It now owns a
  generator-scoped `watch_task`, a `fire()` exactly-once helper, and a `finally:` that cancels and
  awaits the watcher. The defect survives inside that rewrite untouched. Any remedy MUST state what it
  does with `watch_task` and MUST preserve `fire()`'s exactly-once guarantee. Re-read the landed
  function before editing; do not work from the artifact's description of it.

  AFTER D2 this function has TWO consumers, both in `ytdlp_downloader.py` (`_monitor_progress` and
  `_drain_output`); `read_progress` is deleted with the transport. The hazard is fully live and the
  substance is unchanged — only the regression net shrinks.

goals:
  - a line at or above the reader's limit does not raise out of the generator
  - the caller's contract is unchanged: it still receives whole lines
  - fire() remains the single invocation site of on_shutdown
  - watch_task is still cancelled and awaited on every exit path, including the new one
  - EOF stays distinguishable from a stop
  - no new unbounded wait is introduced by the remedy
  - ffmpeg_utils.py gains no import and read_progress keeps its shutdown_event parameter

files:
  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: iter_process_lines
    semantic_anchors:
      modify:
        - type: assignment
          value: "line = await stream.readline()"
        - type: function
          name: fire
        - type: try_statement
          value: "the finally: that cancels and awaits watch_task"
        - type: docstring
          value: "iter_process_lines' termination conditions"
      insert_before:
        type: assignment
        value: "line = await stream.readline()"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestIterProcessLines
    semantic_anchors:
      insert_after:
        type: class
        name: TestIterProcessLines

changes:

  - action: modify
    description: >
      Select one oversized-line shape from plan §3.18 against a MEASUREMENT and implement it inside
      `iter_process_lines`. Whatever is chosen: the new path must not be an unbounded wait; `fire()`
      stays the only `on_shutdown` invocation site; `watch_task` is still cancelled and awaited; EOF
      and a stop stay distinguishable. Raising the spawn-time `limit=` is REJECTED unless the report
      states a measured maximum line length — it moves the threshold, it does not remove it.
    code_hint: |
      # the shape is the block Planner's; the constraints are not negotiable
      #   line = await stream.readline()      <-- replaced, or wrapped
      #   if not line: break                  <-- EOF branch, must stay an EOF branch
      #   yield line                          <-- the caller still receives WHOLE lines
      # finally:
      #   if not watch_task.done():
      #       watch_task.cancel()
      #       try: await watch_task
      #       except asyncio.CancelledError: pass

  - action: add_test
    description: >
      Add cases INSIDE the existing `TestIterProcessLines` (no new `tests/` file, so
      `tests/test_packaging.py EXPECTED_SDIST_ENTRIES` is untouched). Each drives a real
      `asyncio.StreamReader` fed by `feed_data`, then silence — no subprocess, no network. Cover, as
      separate cases: (1) one line at or above the reader's limit — the generator yields the complete
      line, does not raise, and leaves no pending task; (2) the stop set while a read on an oversized
      line is blocked — `on_shutdown` fires EXACTLY once and the generator ends, with no leftover
      `watch_task`; (3) `watch_task` is not left pending on the oversized-line path. Assert on
      behaviour, never on task identities or the implementation's shape.
    code_hint: |
      stream = asyncio.StreamReader()
      stream.feed_data(b"x" * 70000 + b"\n")   # at or above the default limit
      shutdown_event = asyncio.Event()
      calls: list[str] = []
      async def on_shutdown() -> None:
          calls.append("fired")
          stream.feed_eof()
      lines = [ln async for ln in iter_process_lines(stream, shutdown_event,
                                                     on_shutdown=on_shutdown)]
      assert len(calls) <= 1
      assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

  - action: prohibited
    description: >
      MUST NOT add an import to `ffmpeg_utils.py` — it must remain a leaf (only `..exceptions` and
      `..utils.formatting`). MUST NOT convert `read_progress`'s `shutdown_event` parameter into a
      module lookup. MUST NOT add a second `on_shutdown` invocation site. MUST NOT remove or weaken
      the `finally:` that cancels and awaits `watch_task`. MUST NOT wrap the read in a task
      (`create_task` on `readline`) or race it with `asyncio.wait` — measured upstream at ~35 us per
      line against ~1.6 us per line, and it breaks currently-green drain tests because the extra
      suspension lets `process.wait()` win the caller's `FIRST_COMPLETED` race. MUST NOT pass `limit=`
      at any spawn site (B2's own prohibition 7). MUST NOT add a bare module-level literal for a bound
      (rule 10).
    code_hint: |

acceptance_criteria:
  - A line at or above the reader's limit does not raise out of iter_process_lines
  - The caller still receives whole lines; no partial line is ever yielded
  - on_shutdown fires at most once per generator, from the ONE shared fire() helper
  - A b"" read (EOF) ends the generator WITHOUT invoking on_shutdown
  - watch_task is cancelled and awaited on every exit path, including the oversized-line path
  - All four existing TestIterProcessLines cases are green UNCHANGED, including the exactly-once
    assertion on on_shutdown
  - >
    The FULL suite is green. THE REGRESSION NET AFTER D2 IS: all of TestIterProcessLines
    (exactly-once included), plus the yt-dlp trio — test_ytdlp_stdout_progress_written_to_console,
    test_ytdlp_echo_false_suppresses_stderr_while_callback_fires,
    test_ytdlp_echo_false_progress_emits_debug_log. Revision 1 named six drain tests; B10 DELETES
    test_error_handling_ffmpeg_failure, test_error_handling_ffmpeg_failure_sanitizes_url_in_error,
    test_download_with_ffmpeg_with_progress_callback and
    test_perform_download_ffmpeg_progress_adapter_sends_unknown_total with the transport that
    exercised them. The shorter net is a consequence of the deletion, NOT a weaker gate.
  - The suite's warning count does not GROW
  - ffmpeg_utils.py has no new import; read_progress keeps its parameter
  - >
    The COMMIT BODY states what happened to watch_task and asserts fire() is still the only on_shutdown
    invocation site
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B3 — DELETED

```yaml
id: plan10-b3-DELETED
title: DELETED — moot by D2. No work item. Do not schedule.
priority: none
depends_on: []

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: ~~B3 — DELETED: moot by D2~~
source_blocks: []
source_findings: ["TRN-005"]

description: >
  NO WORK. This block is deleted and its id is retired, not reused, so that Revision 1's cross-references
  stay readable. TRN-005 is the `if value == "end": break` inside `read_progress`, which abandons the
  child at its final progress block.

  MOOT BY D2, with the code reason: only `download_with_ffmpeg` passes `-progress` to ffmpeg, and D2
  deletes that method. The merge transport never does — `_build_ffmpeg_concat_command` returns
  `["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", <list>, "-c", "copy", <out>]` with no
  `-progress`, and `_merge_batch_segments` / `_perform_final_merge` read their child with
  `process.communicate()` under `_await_ffmpeg_with_timeout`. Nothing reachable can produce the
  defect.

  IF THE FFMPEG DOWNLOAD TRANSPORT IS EVER REINSTATED, TRN-005 RETURNS WITH IT AND MUST BE RE-FILED.
  That warning belongs in the commit that reinstates the transport.

goals: []
files: []
changes: []

acceptance_criteria:
  - No block report claims to have implemented TRN-005
  - Section 8.4's trace records TRN-005 as MOOT BY D2, not as pending
```

---

### B4

```yaml
id: plan10-b4-reader-failure-visible-not-swallowed
title: Make a reader failure visible instead of swallowed
priority: high
depends_on: []

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B4 — Make a reader failure visible instead of swallowed
source_blocks: ["B4"]
source_findings: ["TRN-006"]

description: >
  RE-SCOPED BY D2 — SINK HALF ONLY. TRN-006 had two inseparable halves while both existed. The PARSE
  half (`_PROGRESS_KEY_HANDLERS`' unguarded `int()`/`float()` conversions, reached through
  `read_progress`) is DELETED, because `read_progress`, `ProgressParser`, `FfmpegProgress` and the
  table go with the ffmpeg download transport. The validator's correction that every entry already
  carried a `v != "N/A"` guard is now moot too: there is no table. The SINK half survives whole:
  `_await_first_and_cancel_others` returns a failed task in `done` without retrieving its exception,
  and all surviving call sites discard the return value, so a reader failure produces no record and no
  exception.

  WHY THE SURVIVING HALF IS MORE IMPORTANT, NOT LESS: after D2, `_await_first_and_cancel_others` is
  the observer for the ONLY reader the product has left. B2 makes that reader survive an oversized
  line; this block makes its death visible. Before the deletion there were two readers and one sink;
  now there is one reader and one sink, so this is the single point at which a yt-dlp drain failure can
  be detected at all. A silent reader death leaves the child's stdout pipe undrained, and an undrained
  pipe means `await process.wait()` can never return.

goals:
  - a reader task that raises produces exactly one record
  - a task that completes normally produces NO record
  - plan 08's cancel-and-settle contract is unchanged
  - no `Any` is added and ffmpeg_utils.py gains no import
  - no bound is added to any wait

files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _await_first_and_cancel_others
      - type: function
        name: _download_with_ytdlp
    semantic_anchors:
      modify:
        - type: except_clause
          value: "except asyncio.CancelledError: pass"
        - type: return_statement
          value: "return done, pending"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestYtDlpSubprocessShutdown
    semantic_anchors:
      insert_after:
        type: class
        name: TestYtDlpSubprocessShutdown

changes:

  - action: modify
    description: >
      Make `_await_first_and_cancel_others` retrieve and report each FAILED task's exception instead of
      returning it in `done` with the exception never retrieved. It must still cancel and await every
      pending task before returning — plan 08's contract — and must still catch
      `asyncio.CancelledError`. Per §3.20 the recommended shape is "retrieve and report": the return
      shape stays exactly as it is, so the two surviving call sites, which discard the return anyway,
      need no change at all. Add no `Any`. If the Planner chooses the alternative (a completion outcome
      callers act on), the report must name what a caller does with it that it does not do today.
    code_hint: |
      for task in pending:
          task.cancel()
          try:
              await task
          except asyncio.CancelledError:
              pass
      for task in done:
          if task.cancelled():
              continue
          exc = task.exception()          # retrieved, not left on the task
          if exc is not None:
              logger.error("subprocess_reader_failed", error=str(exc))
      return done, pending

  - action: add_test
    description: >
      Add three cases inside `TestYtDlpSubprocessShutdown`. (1) A reader task that raises produces
      exactly one log record — assert on the observable effect, not on the helper's return tuple.
      (2) THE DISCRIMINATION CASE: a task that completes normally produces NO record. Without it the
      fix is satisfiable by logging every finished task, which is noise, not visibility. (3) A pending
      task that is cancelled and settles produces NO record — this is plan 08's settlement contract and
      the block must not break it.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT touch `_PROGRESS_KEY_HANDLERS`, `ProgressParser`, `FfmpegProgress` or `read_progress` —
      they are DELETED by B10, and "extending the N/A guard" is no longer this block's work. MUST NOT
      add an import to `ffmpeg_utils.py`. MUST NOT add one to `ytdlp_downloader.py` for the reporting
      mechanism unless the report justifies it against rule 4. MUST NOT change the
      cancellation-and-settlement contract plan 08 built; if any part is reversed, the report names the
      part and the reason. MUST NOT make a NORMAL completion look like a failure. MUST NOT add `Any`.
      MUST NOT add a bound to any wait. MUST NOT re-raise the failed task's exception out of the
      helper — that turns a drain into a crash and is the specific over-correction §3.20 names.
    code_hint: |

acceptance_criteria:
  - A reader task that raises produces exactly one record (new test)
  - A normally-completing task produces NO record (new test — the discrimination case)
  - A cancelled-and-settled pending task produces NO record (new test)
  - Plan 08's cancel-and-await-the-pending-set contract is unchanged
  - TestYtDlpSubprocessShutdown and the yt-dlp drain trio are green UNCHANGED
  - >
    The obligations Revision 1 assigned here are DISCHARGED BY DELETION, not weakened:
    TestReadProgress's four cases, TestProgressParser and TestFfmpegProgress go with the transport, so
    `test_read_progress_handles_na_values` is no longer this block's regression net — there is no table
    left to extend
  - No new `Any`, no new import in ffmpeg_utils.py, no new module, no new dependency
  - >
    No bound is added to any transfer stage; the yt-dlp no-application-level-timeout docstring is
    byte-identical (D3 preserved that decision)
  - >
    The COMMIT BODY carries the measured before/after, states the parse half is disposed of by D2, and
    states that this sink is now the only observer of the only reader left
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B5

```yaml
id: plan10-b5-cancel-subprocess-return-contract-two-surviving-sites
title: Read cancel_subprocess's documented return contract correctly at its two surviving sites
priority: medium
depends_on: [B10, B1]

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B5 — Read cancel_subprocess's documented return contract correctly at its two
  surviving sites
source_blocks: ["B5"]
source_findings: ["TRN-012"]

description: >
  `cancel_subprocess` is CORRECT AS DOCUMENTED — "True if process was cancelled, False if process was
  already gone" — and `except ProcessLookupError: return False` is its only `False`. Call sites read
  `False` as "not clean" and log a `*_cancel_not_clean` warning, but a process that is already gone is
  exactly the clean outcome.

  RE-SCOPED BY D2: SIX SITES BECOME TWO. Revision 1 counted four in `download_with_ffmpeg` (its
  `_monitor_progress` and `_drain_stderr` `_on_shutdown` closures, the stop branch after the re-wait,
  and the `finally:`) and two in `_download_with_ytdlp` (its `_on_shutdown` and the `except
  asyncio.CancelledError:` arm). D2 deletes `download_with_ffmpeg`, so all four of its sites go. The
  two in `ytdlp_downloader.py` survive with the misreading.

  THE FAILURE MODE IS WEAKER BUT REAL, and the weakening is stated rather than assumed. Revision 1's
  "three spurious records per stop" was a property of `download_with_ffmpeg`'s composition — the same
  handle received `cancel_subprocess` three times. `_download_with_ytdlp` has no such composition: its
  `if shutdown_event.is_set():` arm simply returns `None` without calling the ladder. What survives is
  a TWO-call sequence: the reader's `_on_shutdown` terminates the child, and if the caller's task is
  then cancelled, the `except asyncio.CancelledError:` arm calls the ladder again on a child that is
  already gone and logs `yt_dlp_cancel_not_clean` for it. ONE spurious record, not three.

goals:
  - no warning is written for a process that is already gone
  - a process that is genuinely still running after the ladder STILL produces the warning
  - cancel_subprocess itself is unchanged — signature, keyword-only timeout, return contract
  - _await_ffmpeg_with_timeout's arm is untouched and the alias stays an alias

files:
  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: cancel_subprocess
      - type: function
        name: _await_ffmpeg_with_timeout
      - type: assignment
        name: cancel_ffmpeg_process
    semantic_anchors:
      modify:
        - type: docstring
          value: cancel_subprocess
      read_only:
        - type: except_clause
          value: "except ProcessLookupError:"
        - type: except_clause
          value: "except (TimeoutError, asyncio.CancelledError):"
        - type: assignment
          value: cancel_ffmpeg_process

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _download_with_ytdlp
    semantic_anchors:
      modify:
        - type: guard_expression
          value: "if not await cancel_subprocess(process):"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestYtDlpSubprocessShutdown
    semantic_anchors:
      insert_after:
        type: class
        name: TestYtDlpSubprocessShutdown

changes:

  - action: modify
    description: >
      At each of the TWO surviving boolean-reading sites, nest the existing warning inside
      `if process.returncode is None:` so it fires only when nothing terminated the child. Re-document
      `cancel_subprocess`'s `Returns:` section to state that `False` means "already gone, therefore
      clean". Do NOT rename any event unless the whole family goes with it and the unseparated
      `ytdlp_*` siblings in the same module are reconciled in the same change.
    code_hint: |
      if not await cancel_subprocess(process) and process.returncode is None:
          logger.warning(
              "yt_dlp_cancel_not_clean",
              pid=process.pid,
              url=_strip_auth_params(video_url),
          )

  - action: add_test
    description: >
      Add cases that assert on LOG RECORDS, not return values. (1) The composition case: the reader's
      `_on_shutdown` terminates the child, then the `CancelledError` arm runs, and NO
      `yt_dlp_cancel_not_clean` record is written for the second call. (2) THE NEGATIVE CASE,
      MANDATORY: a child that is still running after the ladder DOES produce the record. Without (2)
      the fix is trivially satisfiable by deleting the warning, and that must not be a passing outcome.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT change `cancel_subprocess`'s return contract — no tri-state, no new exception, no
      renamed return value. The function is correct. MUST NOT re-add a guard in
      `download_with_ffmpeg` or any other deleted site. MUST NOT touch `_await_ffmpeg_with_timeout`'s
      arm, and the alias stays an alias. MUST NOT delete a warning without adding the positive case.
      MUST NOT change the ladder: the `terminate()` -> `wait_for(..., 5.0)` -> `kill()` -> `wait()`
      order, or the keyword-only `timeout: float = 5.0`.
    code_hint: |

acceptance_criteria:
  - Two cancel_subprocess calls on one handle write zero yt_dlp_cancel_not_clean records (new test)
  - A child still running after the ladder DOES write the record (new test — mandatory)
  - >
    tests/test_ffmpeg_utils.py::TestCancelSubprocess is green UNCHANGED, including
    test_returns_false_on_process_lookup_error, test_terminate_on_success, test_kill_on_timeout and
    test_backward_compatible_alias
  - cancel_subprocess's signature, keyword-only timeout and return type are byte-identical
  - _await_ffmpeg_with_timeout is byte-identical; cancel_ffmpeg_process is still an alias
  - No guard was re-added in any deleted site
  - >
    The COMMIT BODY carries the measured before/after (two calls on one handle: before -> the second
    logs; after -> it does not) and states that the four-site composition was deleted with the transport
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B6 — unchanged by `D1`–`D4`

```yaml
id: plan10-b6-bound-child-output-accumulation
title: Stop accumulating a child's entire transcript, including the transcript nobody asked for
priority: medium
depends_on: []
UNCHANGED: confirmed unaffected by D1-D4. Its subject is the yt-dlp transcript buffer, which the
  transport deletion does not touch.

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B6 — Stop accumulating a child's entire transcript
source_blocks: ["B6"]
source_findings: ["TRN-011"]

description: >
  `_download_with_ytdlp` declares `output_chunks: list[bytes] = []` and appends every line the child
  emits, from both `_monitor_progress` and `_drain_output`, then joins the whole list on the failure
  path. Nothing bounds it. At BOTH append sites the ordering is `_echo_ytdlp_line(decoded, echo=echo)`
  THEN `output_chunks.append(line)` — and `_echo_ytdlp_line` returns without writing anything when
  `echo=False`, so in batch mode every line is deliberately discarded for display and then stored
  anyway. Measured growth: 108.6 MiB of working set for 50 MiB of child output, which multiplies
  across a batch of up to 16. Bound the accumulator.

  REVISION 2: no change. Re-verified against the live tree — `output_chunks` and both append sites are
  inside `_monitor_progress` and `_drain_output`, and neither symbol is named by anything B10 removes.

goals:
  - the accumulated buffer stays within its declared bound
  - with echo=False the buffer does not grow for output nobody asked for (if the chosen shape says so)
  - the failure path still produces a usable error message
  - echo=False still writes NOTHING to stderr
  - no Settings field, no environment variable, no CLI option
  - the bound lives in services/ytdlp_downloader.py as a module-level constant

files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _download_with_ytdlp
      - type: function
        name: _echo_ytdlp_line
    semantic_anchors:
      modify:
        - type: assignment
          value: "output_chunks: list[bytes] = []"
        - type: function_call
          value: "output_chunks.append(line)"
        - type: assignment
          value: "output_data = b\"\".join(output_chunks) if output_chunks else b\"\""
      insert_before:
        type: function
        name: _download_with_ytdlp
      read_only:
        - type: guard_expression
          value: "if not echo:"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestEchoYtdlpLine
    semantic_anchors:
      insert_after:
        type: class
        name: TestEchoYtdlpLine

changes:

  - action: modify
    description: >
      Bound `output_chunks`. Select a shape from plan §3.21 and record the choice and its cost in the
      report: a capped tail (recommended), a capped head (rejected — the tail is the informative part),
      accumulate-only-on-failure, or skip accumulation entirely when `echo=False` (real improvement,
      real diagnostic cost — the report must state the cost if chosen). Declare the bound as a
      module-level private constant, sized against the 200-character merge-error truncation already in
      `ffmpeg_utils.py` and against the 64 KiB the reader can hold per line. If accumulation becomes
      conditional on `echo`, both append sites must behave identically and the method docstring's
      `echo` description must say so.
    code_hint: |
      _MAX_CHILD_OUTPUT_BYTES = 64 * 1024   # module-private; mirrors ffmpeg_utils' 200-char cut
      ...
      total = 0
      async for line in iter_process_lines(process.stdout, shutdown_event,
                                           on_shutdown=_on_shutdown):
          decoded = line.decode(errors="replace")
          _echo_ytdlp_line(decoded, echo=echo)
          if accumulate:
              output_chunks.append(line)   # bounded append
              total += len(line)
              if total > _MAX_CHILD_OUTPUT_BYTES:
                  ...  # trim from the head of the list

  - action: add_test
    description: >
      Add cases in `tests/test_hls_downloader.py`, inside or beside `TestEchoYtdlpLine`. (1) A child
      that writes far more than the bound: assert the accumulated buffer stays at or under the bound
      AND the call still returns normally on the success path. Assert through the observable effect —
      the failure message's length — not on a private attribute. (2) With `echo=False`: assert a chatty
      child leaves the buffer as the chosen shape requires AND that nothing was written to stderr.
      (3) The failure path still produces a usable error message containing the child's most relevant
      output, which for a capped tail is the END of the transcript.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT add a `Settings` field, an environment variable, a CLI option, a `.env.example` row or
      a configuration-guide row — `TRN-013` was rejected upstream for exactly that shape, and D3's
      `download_stall_timeout` is unrelated and belongs to B11. MUST NOT give `_echo_ytdlp_line` a
      parameter, and MUST NOT make `echo=False` write anything to stderr. MUST NOT add a new module or
      a new import for the bound. MUST NOT enforce the bound by dropping lines SILENTLY. MUST NOT
      change `max_concurrent_downloads`, the segment fan-out, or the batch permit.
    code_hint: |

acceptance_criteria:
  - The accumulated buffer stays at or under the declared bound for a child writing far more
  - The success path still returns normally for such a child (new test)
  - The failure path still produces a usable error message containing the relevant output (new test)
  - All four TestEchoYtdlpLine::test_ytdlp_echo_false_* cases are green UNCHANGED, with NO edits
  - TestYtDlpSubprocessShutdown is green UNCHANGED
  - The bound is a module-level private constant; no Settings field exists
  - >
    The COMMIT BODY carries the measured before/after peak growth and states explicitly that NO setting
    was added
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B7

```yaml
id: plan10-b7-sanitizer-documented-capability-two-sites
title: Stop the sanitizer's docstring and the yt-dlp comment claiming a capability its regex lacks
priority: medium
depends_on: []

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B7 — Stop the sanitizer's docstring and the yt-dlp comment claiming a capability
source_blocks: ["B7"]
source_findings: ["TRN-009"]

description: >
  `sanitize_text_for_log` is a single `_URL_REGEX.sub(lambda m: _strip_auth_params(m.group(0)),
  text)` over `https?://[^\s'"<>]+`. A filesystem path contains neither prefix, so it can never match,
  and `_strip_auth_params` — reached only from a match — can never be reached for one. TWO artifacts
  still claim otherwise.

  RE-SCOPED BY D2: THREE SITES BECOME TWO. Revision 1 named the function's own docstring, the
  `# SEC-002:` comment in `_download_with_ytdlp`, and the `# SEC-002:` comment in
  `download_with_ffmpeg`. The third is DELETED with the method. The first two survive — and the yt-dlp
  comment is now the one that most needs to stop over-claiming, because the yt-dlp transport is the one
  that still writes `--cookies <path>` and the media URL into argv.

  WHY THIS HALF IS UNCONDITIONAL: a false claim is false today under every resolution. Phase 06 may
  later add path redaction; until it does, the claim lies. Rule 14 makes correcting it mandatory.
  WHY IT STAYS SPLIT FROM B14: different modules, different owners, different verification, and — above
  all — B14 now APPLIES a transform while this block changes no behaviour at all.

goals:
  - no artifact in the repository claims the transform redacts filesystem paths
  - the docstring's ACCURATE first sentence survives
  - the transform's behaviour is byte-identical
  - a test pins the capability boundary so the docstring cannot drift back
  - the matcher is NOT extended — that is phase 06's SEC-006

files:
  - path: src/vkdownloader/utils/url_sanitizer.py
    targets:
      - type: function
        name: sanitize_text_for_log
    semantic_anchors:
      modify:
        - type: docstring
          value: sanitize_text_for_log
      read_only:
        - type: assignment
          value: _URL_REGEX
        - type: return_statement
          value: "return _URL_REGEX.sub(...)"

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _download_with_ytdlp
    semantic_anchors:
      modify:
        - type: comment
          value: "the SEC-002 comment above sanitize_text_for_log(error_msg)"
      read_only:
        - type: function
          name: _echo_ytdlp_line

  - path: tests/test_url_sanitizer.py
    targets:
      - type: class
        name: TestSanitizeTextForLog
    semantic_anchors:
      insert_after:
        type: class
        name: TestSanitizeTextForLog

changes:

  - action: modify
    description: >
      Correct the two false claims and nothing else. In `sanitize_text_for_log`'s docstring, keep the
      accurate first sentence ("Scans `text` for `http(s)://` URLs and replaces each match with only
      its scheme and host via `_strip_auth_params`") and replace the third sentence's false clause about
      cookie file paths with what the function actually does — including that it does NOT match a
      filesystem path or an argument fragment carrying one. In the yt-dlp `# SEC-002:` comment, keep the
      true half (signed CDN URLs are redacted) and drop the false one, keeping the `SEC-002`
      cross-reference to the phase that owns the exposure judgement.
    code_hint: |
      """Redact all URLs found in arbitrary text (e.g. subprocess output).

      Scans ``text`` for ``http(s)://`` URLs and replaces each match
      with only its scheme and host via :func:`_strip_auth_params`.
      This prevents signed CDN tokens in subprocess output from leaking
      into log files.

      It does NOT match, and therefore does not redact, a filesystem
      path or an argument fragment that carries one (SEC-002/SEC-006).
      """

  - action: add_test
    description: >
      Add ONE case inside the existing `TestSanitizeTextForLog` that pins the capability boundary: pass
      both a signed URL and a filesystem path (a temp cookie-file path and a temp argfile path) and
      assert the URL is redacted and the path is returned UNCHANGED. Today no test passes a path at
      all, which is exactly why the false claim survived.
    code_hint: |
      text = r"Error: @C:\Users\op\AppData\Local\Temp\vk_ffmpeg_ab.args " \
             r"and https://cdn.vkvideo.ru/stream.m3u8?sig=SECRET"
      out = sanitize_text_for_log(text)
      assert "SECRET" not in out
      assert r"vk_ffmpeg_ab.args" in out        # the path is NOT matchable — pinned on purpose

  - action: prohibited
    description: >
      MUST NOT change `sanitize_text_for_log`'s behaviour — no regex is edited, no branch is added.
      Extending the matcher is PHASE 06's `SEC-006` under the `Q5` split; this block must not pre-empt
      it. MUST NOT touch `_strip_auth_params` or `sanitize_url_for_log`. MUST NOT delete the `SEC-002:`
      comment entirely; only the false clause goes. No new test file. No change to any log record's
      fields, level or event name. MUST NOT edit `_echo_ytdlp_line` or the two merge sinks — those are
      B14's or phase 06's.
    code_hint: |

acceptance_criteria:
  - No docstring or comment in src/ claims the transform redacts filesystem paths
  - sanitize_text_for_log's behaviour is byte-identical before and after
  - Its docstring's accurate first sentence survives
  - The new case pins the boundary: a signed URL is redacted, a temp path is returned unchanged
  - TestStripAuthParams and TestSanitizeTextForLog's four existing cases are green UNCHANGED
  - `_URL_REGEX` is byte-identical — the matcher was NOT extended
  - >
    The COMMIT BODY cites TRN-009 (not SEC-005/SEC-006, which this plan does not claim), states that no
    behaviour changed, notes that the third site was deleted with the transport by B10, and records the
    matcher as phase 06's under the Q5 split
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B8 — unchanged by `D1`–`D4`

```yaml
id: plan10-b8-browser-launch-failure-carries-its-cause
title: Carry the launch failure's actionable cause into the ExtractionError
priority: high
depends_on: []
UNCHANGED: confirmed unaffected by D1-D4. One interaction: D4 puts a SECOND hardened failure path into
  __aenter__ (B15's asset check), which must not be conflated with this block's browser-unavailable arm.

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B8 — Carry the launch failure's actionable cause into the ExtractionError
source_blocks: ["B8"]
source_findings: ["BRW-001"]

description: >
  `BrowserManager.__aenter__`'s `except Exception:` arm does
  `logger.error("browser_launch_failed", exc_info=True)` then
  `raise ExtractionError("Failed to launch browser for video extraction") from None`. `from None` sets
  `__cause__ = None` and `__suppress_context__ = True` while `__context__` STAYS populated — so the
  Playwright error, whose message carries the missing executable path AND the `playwright install`
  remedy, is removed from the displayed traceback. The caller learns neither the binary nor how to
  obtain it. THIS HALF FIRES UNCONDITIONALLY on every launch failure on every machine. Carry the
  actionable content into the `ExtractionError`'s TEXT; keep `from None`, because it is what keeps the
  Playwright banner's box-drawing characters out of the displayed traceback.

  DO NOT FIX THE ENCODING MECHANISM. A second, CONDITIONAL mechanism exists — the same
  `logger.error(..., exc_info=True)` raises `UnicodeEncodeError` on a strict-encoded stderr — but it is
  owned by NO finding in any phase and is B16, CONDITIONAL on §9 Q6, which D1-D4 did not answer.

  REVISION 2: no change to the remedy. The recorded interaction is that `D4` gives `__aenter__` a
  second hardened failure path — B15's asset check — and the two must not be merged or confused.

goals:
  - the caller learns which browser binary is missing and how to obtain it
  - `from None` is kept, so the banner's box-drawing characters never reach the displayed traceback
  - the application's own ExtractionError still reaches the caller
  - exc_info=True is not removed and the logger.error statement is not wrapped in a try
  - __aexit__ is untouched
  - the encoding mechanism is recorded as open and unowned, not fixed and not claimed

files:
  - path: src/vkdownloader/infrastructure/browser.py
    targets:
      - type: method
        name: __aenter__
        owner: BrowserManager
    semantic_anchors:
      modify:
        - type: raise_statement
          value: "raise ExtractionError(\"Failed to launch browser for video extraction\") from None"
      read_only:
        - type: function_call
          value: "logger.error(\"browser_launch_failed\", exc_info=True)"
        - type: function_call
          value: "await playwright_instance.stop()"

  - path: tests/test_browser_infrastructure.py
    targets:
      - type: class
        name: TestBrowserManager
    semantic_anchors:
      modify:
        - type: function
          name: test_browser_manager_launch_failure_raises_extraction_error
      insert_after:
        type: class
        name: TestBrowserManager

changes:

  - action: modify
    description: >
      Derive the actionable content from the caught exception and append it to the
      `ExtractionError`'s message. Select a shape from plan §3.22 and record it: appending the
      exception's message verbatim is REJECTED because the Playwright message is the multi-line banner
      and it reintroduces the box-drawing characters. Extract the missing-executable path and the install
      command as single-line fields instead, with an explicit fallback for the case where neither is
      present. Any helper lives in `browser.py` and is module-private.
    code_hint: |
      except Exception as exc:
          logger.error("browser_launch_failed", exc_info=True)
          await playwright_instance.stop()
          raise ExtractionError(_describe_launch_failure(exc)) from None

      def _describe_launch_failure(exc: Exception) -> str:
          """Carry the actionable part of a launch failure into the raised error's text."""
          executable = ...   # the "Executable doesn't exist at <path>" element, if present
          remedy = ...       # the "playwright install" element, if present
          parts = ["Failed to launch browser for video extraction"]
          if executable:
              parts.append(f"browser binary not found: {executable}")
          if remedy:
              parts.append(f"to obtain it: {remedy}")
          return "; ".join(parts)

  - action: add_test
    description: >
      Re-scope `test_browser_manager_launch_failure_raises_extraction_error`: widen the `match` to the
      new text while KEEPING the assertion that the application's own `ExtractionError` reaches the
      caller — that assertion is the finding's real content and must not be weakened away. Add:
      (1) the cause-content case — a stand-in raising an error whose message carries both the missing
      executable and the remedy; assert both appear in the raised text; (2) the suppression case —
      assert the displayed traceback does NOT contain the banner, so a future "fix" that drops
      `from None` is caught; (3) the uninformative-message case — assert what the text looks like when
      the caught exception carries neither element, because an empty string is worse than today's text.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT drop `from None`. MUST NOT remove `exc_info=True` and MUST NOT wrap the `logger.error`
      statement in a `try`/`except`. MUST NOT fix, claim, or close the encoding mechanism — record it
      and point at B16. MUST NOT touch `__aexit__`, and MUST NOT touch B15's asset check or its new
      `ErrorCode` member — those are B15's. MUST NOT add a stdlib `logging` import; this module is
      structlog and following rule 12's text literally would break the renderer split in
      `config.setup_logging`. MUST NOT add a release path for the context BRW-002 names (rejected).
    code_hint: |

acceptance_criteria:
  - The surfaced ExtractionError names the missing binary and how to obtain it (new test)
  - The surfaced type is still ExtractionError, not a Playwright error (re-scoped test)
  - The displayed traceback does NOT contain the box-drawing banner (new test) — `from None` is kept
  - The uninformative-message case produces a non-empty, still-actionable text (new test)
  - The six plan-08 B4 tests for __aexit__ are green UNCHANGED, as are the other TestBrowserManager cases
  - __aexit__ is byte-identical; no `# type: ignore` is widened
  - No stdlib logging import anywhere in the diff
  - B15's asset check and its ErrorCode member are untouched by this block
  - >
    The COMMIT BODY carries the measured before/after (__cause__, __suppress_context__, whether
    `playwright install` appears in the surfaced text) and states that the encoding mechanism remains
    OPEN AND UNOWNED
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B9

```yaml
id: plan10-b9-record-the-closed-audit-chains
title: Record that both chains are closed, and that phase 06's SEC-004 is now doubly wrong
priority: high
depends_on: []

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B9 — Record that both chains are closed
source_blocks: ["B9"]
source_findings: ["phase05/VAL-501", "phase05/VAL-502"]

description: >
  RE-SCOPED BY D2. Revision 1 recorded two chains as OPEN and wrote a durable record under
  `.ai/decisions/`. Both are now settled, in opposite directions:

    phase05/VAL-502 chain 2 (the shape of the TRN-001 fix is a decision SEC-004 owns) — CLOSED by
    D2. The transport is deleted, not repaired. Recorded verbatim in §9.
    phase05/VAL-502 chain 1 (TRN-001 and TRN-002 must land together) — EVAPORATES. The coupling
    existed because repairing one made the other worse. There is nothing left to couple: TRN-001's
    subject is deleted, and TRN-002 has been re-scoped to a different statement in a different module.
    The ordering obligation is discharged by the deletion itself, not by ordering.
    phase05/VAL-501 (phase 06's SEC-004 records MET (argfile) in two cells and its subject line claims
    the transport satisfies the stated intent) — MORE clearly stale. Before D2 the cells asserted a
    concealment that never worked; after D2 they assert it ABOUT A TRANSPORT THAT NO LONGER EXISTS.

  WHERE THE RECORD LIVES: `.ai/audit/**` is READ-ONLY for this engagement, so the correction still
  cannot be performed here. `.ai/decisions/` exists and is EMPTY, so nothing is overwritten. §9 in
  this plan is the companion record. A decision that lives only in a commit message is a decision
  that gets lost.

goals:
  - both chains are recorded as closed, with the dates and the owner's words
  - phase 06's SEC-004 is named as the owner of the outstanding correction, with no verdict written
  - D1's retirement of the exposure argument is recorded
  - TRN-010's disposition and its SEC-006 cross-reference are recorded
  - the console-encoding ownership gap is recorded, and Q6 is recorded as still open
  - no file under .ai/audit/** is created, edited, moved or deleted
  - no product code is touched

files:
  - path: .ai/decisions/05-subprocess-browser-decision-record.md
    targets:
      - type: document
        name: phase 05 decision record
    semantic_anchors:
      create:
        type: document
        name: phase 05 decision record

changes:

  - action: add_document
    description: >
      Write ONE new file under `.ai/decisions/`. It must contain, as discrete statements: (1) that both
      chains are closed, with the dates and the owner's words for D2, and that chain 1 evaporated with
      the argfile rather than being satisfied by ordering; (2) that D2 DELETES the transport rather
      than repairing it, and that the deletion is authorised as a breaking change — a script passing
      `--method ffmpeg` receives a usage error and a non-zero exit; (3) that phase05/VAL-501's
      correction is OUTSTANDING and belongs to phase 06, stated precisely — replace both `MET
      (argfile)` cells, rewrite the subject line so it does not name a deleted transport, record D1 as
      the reason the exposure argument no longer distinguishes the transports — and that the record
      must NOT state what SEC-004 should become; (4) that D1 retires the exposure argument, because on
      a single-user desktop the user can already read their own process list; (5) TRN-010's disposition
      — moot with one transport, residue cross-referenced to SEC-006 and moot for this deployment by
      D1; (6) the console-encoding ownership gap and that Q6 remains open; (7) every correction this
      plan entered against the code context (§1.7) plus the mojibake observation (§1.8).
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT create, edit, move or delete ANY file under `.ai/audit/**` — phase 05's own artifacts
      included. MUST NOT write any file under `.ai/plans/**` other than the plan file itself. MUST NOT
      write more than one new file. MUST NOT contain a verdict on SEC-004, SEC-005 or SEC-006: no
      "should be", no severity, no replacement wording — only what is claimed, by whom, and who owns
      it. Every `VAL-` id must be written `phase05/VAL-NNN`. MUST NOT fix the `cli-reference-clean.md`
      mojibake — it is recorded, not fixed (§1.8). MUST NOT touch src/, tests/ or pyproject.toml.
    code_hint: |

acceptance_criteria:
  - Exactly one new file exists, under .ai/decisions/
  - >
    `git diff --exit-code -- .ai/audit` and `git status --short -- .ai/audit` are both empty, for
    EVERY phase's findings and validation files
  - `git diff --exit-code -- src tests pyproject.toml` is empty
  - The record contains all seven required statements and NO verdict on any SEC- row
  - Every VAL- id in the record is written `phase05/VAL-NNN`
  - The record names phase 06 as the owner of phase05/VAL-501's correction and states this plan does
    not perform it
  - The record states that chain 1 evaporated with the argfile, not that it was satisfied by ordering
  - The record states that the console-encoding defect is owned by no finding in any phase and that Q6
    is open
  - The COMMIT BODY names phase 06 as the owner and states that `.ai/audit/**` was not modified
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's single file (plan §2.5)
```

---

### B10

```yaml
id: plan10-b10-delete-the-ffmpeg-download-transport
title: DELETE the ffmpeg download transport and everything that exists only to serve it
priority: critical
depends_on: []
DECIDED: D2 — the owner's words are "No you can delete it for now. If it will be needed we will add it
  in future." This closes phase05/VAL-502 chain 2.

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B10 — DELETE the ffmpeg download transport
source_blocks: ["B10"]
source_findings: ["TRN-001", "TRN-010", "phase05/VAL-502"]

description: >
  `--method ffmpeg` is a shipped, documented CLI option that executes NONE of the transport the
  operator selected: the product writes every argument into a temporary file and invokes
  `ffmpeg "@<path>"`, and the installed muxer documents NEITHER `@file` NOR `-/opt`, so it takes the
  token as a literal output filename, produces nothing, exits non-zero, and `perform_download`
  silently substitutes segment download behind one INFO record naming the FALLBACK, not the failure. D2
  resolves TRN-001 by REMOVING the feature. That is the only repair that needs no unmeasured mechanism.

  THIS IS A DELETION, AND THE RULE FOR A DELETION IS SUBTRACTION. The owner authorised a breaking
  change. Therefore: no deprecation shim, no feature flag, no tombstone enum member, no alias kept for
  compatibility, no "coming back soon" note. `DownloadMethod.FFMPEG` is REMOVED OUTRIGHT — a dead enum
  member violates project rule 10, which requires every fixed value to be a live `StrEnum` member.
  The `--method` flag itself stays; a script passing `--method ffmpeg` now receives Typer's own
  invalid-choice error and exit `2`, already the documented usage-error code.

  DELETE: the `DownloadMethod.FFMPEG` member; `HLSDownloader` (whole class); `_temp_argfile`;
  `_format_argfile`; the `case DownloadMethod.FFMPEG:` arm including `_ffmpeg_progress_adapter`; the
  `FfmpegProgress` / `ProgressParser` / `read_progress` re-exports and their `__all__` entries and
  ownership-comment lines; `HLSDownloader` from `vkdownloader/__init__.py`'s `__all__`; the word
  `ffmpeg, ` from the `--method` help text at TWO sites; and in `ffmpeg_utils.py`: `read_progress`,
  `ProgressParser`, `FfmpegProgress`, `_ProgressHandler`, `_PROGRESS_KEY_HANDLERS`.

  PRESERVE — binding: `--method` / `-m`, `DownloadMethod.YTDLP`, `DownloadMethod.AUTO`; the `case _:`
  arm with its `unknown_download_method` record; `check_ffmpeg_available` AND its single bare call in
  `perform_download` (still live — a download can reach the merge, and segment merging still needs the
  muxer); `iter_process_lines`, `cancel_subprocess` / `cancel_ffmpeg_process`,
  `_await_ffmpeg_with_timeout`, `_check_merge_space`, `_merge_segments_batched`,
  `_merge_batch_segments`, `_perform_final_merge`, `_build_ffmpeg_concat_command`,
  `_required_merge_bytes`; `sanitize_text_for_log` / `_strip_auth_params` / `sanitize_url_for_log`;
  EVERY dependency in `pyproject.toml`; and `artifacts = ["src/vkdownloader/stealth.min.js"]`.

goals:
  - --method ffmpeg does not exist, and no shim, flag, alias or tombstone remains
  - no live symbol is deleted and no deleted symbol keeps a reference anywhere, including prose
  - --method auto's new semantics are stated and its arm comment corrected
  - all seven documentation sites are corrected, including the mojibake duplicate
  - the deletion's test fallout is removed in the SAME change as the code it tests
  - check_ffmpeg_available and the whole merge transport are untouched

files:
  - path: src/vkdownloader/models/enums.py
    targets:
      - type: class
        name: DownloadMethod
    semantic_anchors:
      modify:
        - type: class
          name: DownloadMethod

  - path: src/vkdownloader/services/downloader.py
    targets:
      - type: class
        name: HLSDownloader
      - type: function
        name: _temp_argfile
      - type: function
        name: _format_argfile
      - type: function
        name: perform_download
      - type: comment
        name: the backward-compatibility re-export facade comment
    semantic_anchors:
      modify:
        - type: function_call
          value: "case DownloadMethod.FFMPEG:"
        - type: docstring
          value: _temp_argfile
      read_only:
        - type: expression_statement
          value: "check_ffmpeg_available()"

  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: read_progress
      - type: class
        name: ProgressParser
      - type: class
        name: FfmpegProgress
      - type: assignment
        name: _PROGRESS_KEY_HANDLERS
      - type: assignment
        name: _ProgressHandler
    semantic_anchors:
      delete:
        - type: function
          name: read_progress
        - type: class
          name: ProgressParser
        - type: class
          name: FfmpegProgress
        - type: assignment
          name: _PROGRESS_KEY_HANDLERS
        - type: assignment
          name: _ProgressHandler
      read_only:
        - type: function
          name: iter_process_lines
        - type: function
          name: cancel_subprocess
        - type: function
          name: check_ffmpeg_available
        - type: function
          name: _await_ffmpeg_with_timeout

  - path: src/vkdownloader/__init__.py
    targets:
      - type: module_attribute
        name: "__all__"
    semantic_anchors:
      modify:
        - type: module_attribute
          value: "__all__"

  - path: src/vkdownloader/cli.py
    targets:
      - type: function
        name: download
      - type: function
        name: batch_download
    semantic_anchors:
      modify:
        - type: option
          name: "--method"

  - path: tests/test_downloader.py
    targets:
      - type: class
        name: TestPerformDownload
    semantic_anchors:
      modify:
        - type: function
          name: "D-12 case 5"
        - type: function
          name: "D-12 case 6"
        - type: function
          name: "D-12 case 7"
      read_only:
        - type: function
          name: "D-12 case 10"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestHLSDownloaderDownload
      - type: class
        name: TestTempArgfile
      - type: class
        name: TestFfmpegCookiePassing
      - type: class
        name: TestReadProgress
      - type: class
        name: TestProgressParser
      - type: class
        name: TestFfmpegProgress
      - type: class
        name: TestDownloadMethodLogging
    semantic_anchors:
      delete:
        - type: class
          name: TestHLSDownloaderDownload
        - type: class
          name: TestTempArgfile
        - type: class
          name: TestFfmpegCookiePassing
        - type: class
          name: TestReadProgress
        - type: class
          name: TestProgressParser
        - type: class
          name: TestFfmpegProgress

  - path: README.md
    targets:
      - type: document
        name: the --method ffmpeg worked example
  - path: docs/99-reference/cli-reference.md
    targets:
      - type: document
        name: the --method option row and the worked ffmpeg example
  - path: docs/99-reference/cli-reference-clean.md
    targets:
      - type: document
        name: the mojibake duplicate of the above — --method rows ONLY
  - path: docs/01-tools/api-reference.md
    targets:
      - type: document
        name: the argv-is-only-@argfile claim and the download_with_ffmpeg prose
  - path: docs/01-tools/quality-selection.md
    targets:
      - type: document
        name: the transport table and its two ffmpeg examples
  - path: docs/01-tools/vkdownloader-overview.md
    targets:
      - type: document
        name: the Secret-safe ffmpeg argument passing claim
  - path: docs/11-guides/vkdownloader-limitations.md
    targets:
      - type: document
        name: the same claim plus the --method ffmpeg workaround row

changes:

  - action: delete_code
    description: >
      Delete the enumerated symbols. Then re-derive BOTH lists by grep and report them: every deleted
      symbol must have zero remaining references, and every preserved symbol must still be referenced.
      Pay particular attention to the facade's SYMBOL-OWNERSHIP COMMENT and its `__all__` — they are
      prose and an attribute list about code, and `mypy` and `ruff` check neither.
    code_hint: |

  - action: modify
    description: >
      Correct `perform_download`'s AUTO arm comment. It reads "Auto: try yt-dlp first (more reliable),
      segment download for resume" — a TWO-transport sentence that D2 makes false, because there is no
      "first" any more. The corrected statement, which must appear verbatim in the commit body, is:
      "--method auto means: resolve cookies according to cookie_source — skipping browser resolution
      when it is `none` — then download via yt-dlp with segment-level resume as the fallback."
    code_hint: |

  - action: edit_tests
    description: >
      In the SAME change, delete: eight `DownloadMethod.FFMPEG` references across two files —
      `test_downloader.py`'s D-12 cases 5, 6 and 7 (success; failure-falls-back;
      failure-with-shutdown-set) and `test_hls_downloader.py`'s `TestDownloadMethodLogging` cases —
      plus every class exercising a deleted symbol: `TestHLSDownloaderDownload`, `TestTempArgfile`
      (including its three `test_format_argfile_*` cases), `TestFfmpegCookiePassing`, `TestReadProgress`,
      `TestProgressParser`, `TestFfmpegProgress`. MUST STAY GREEN UNCHANGED: `test_cli.py`'s
      `--method invalid_method` case (now the PROOF the breaking change is clean); `test_downloader.py`'s
      D-12 case 10 (the only unrecognised-method handler, which keeps `case _:` honest); D-12 cases
      1-4, 8, 9 and 11; and `TestFfmpegAvailabilityCheck` in full.
    code_hint: |

  - action: add_test
    description: >
      Add two cases. (1) `--method ffmpeg` is rejected by the parser with a non-zero exit and a message
      that does not offer ffmpeg as a choice — assert the exit code and the ABSENCE of `ffmpeg` in the
      help text, not the exact message wording. (2) `--method auto` reaches
      `download_with_ytdlp_with_resume_fallback` and skips `_resolve_cookies` when
      `cookie_source == NONE`. D-12 cases 1-3 already cover this; do NOT add a duplicate — state in the
      report that the existing coverage survived the deletion unchanged.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT add a deprecation shim, a feature flag, a tombstone enum member, an alias, or any
      "coming back soon" note. MUST NOT keep `DownloadMethod.FFMPEG` "for one release". MUST NOT touch
      anything in the PRESERVE list — in particular `check_ffmpeg_available`, its bare call,
      `iter_process_lines`, `cancel_subprocess`, or any merge helper; and MUST NOT branch on
      `check_ffmpeg_available`'s answer (that is B13's). MUST NOT leave the AUTO arm's "try yt-dlp
      first" comment in place. MUST NOT fix the `cli-reference-clean.md` mojibake — only its `--method`
      rows are in scope. MUST NOT edit any dependency in `pyproject.toml`, and MUST NOT remove the
      `stealth.min.js` artefact declaration. MUST NOT delete a test in a separate commit from the code it
      tests. MUST NOT leave a re-export line in `downloader.py`'s `__all__` or ownership comment
      pointing at a deleted symbol. Exit codes stay 130 / 1 / 2.
    code_hint: |

acceptance_criteria:
  - DownloadMethod.FFMPEG is gone from the enum, with no shim, alias or tombstone anywhere
  - >
    The enumerated deletion list is re-derived by grep and reported; every deleted symbol has zero
    remaining references, INCLUDING in the facade comment and `__all__`
  - The PRESERVE list is re-derived by grep and reported; every preserved symbol is still referenced
  - check_ffmpeg_available and its single bare call are byte-identical
  - `--method` help text corrected at BOTH cli.py sites, with both diffs shown
  - The AUTO arm comment is corrected and the new semantics statement appears verbatim in the commit body
  - All seven documentation sites corrected, including cli-reference-clean.md's --method rows
  - The mojibake in cli-reference-clean.md is NOT fixed
  - pyproject.toml is byte-identical, including the stealth.min.js artefact declaration
  - >
    The DELETED tests are gone: D-12 cases 5/6/7, TestHLSDownloaderDownload, TestTempArgfile,
    TestFfmpegCookiePassing, TestReadProgress, TestProgressParser, TestFfmpegProgress, and the
    TestDownloadMethodLogging ffmpeg cases
  - >
    The RETAINED tests are green UNCHANGED: test_cli.py's --method invalid_method; D-12 cases 1-4, 8, 9,
    10 and 11; TestFfmpegAvailabilityCheck; TestCancelSubprocess
  - `--method ffmpeg` now produces a non-zero usage exit (new test)
  - No new src/ or tests/ file, so EXPECTED_SDIST_ENTRIES is untouched
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B11

```yaml
id: plan10-b11-download-stall-timeout
title: Bound the stall at the transport's surviving re-wait
priority: medium
depends_on: []
DECIDED: D3 — the bound exists, the default is 300.0, it is configurable, and it is an INACTIVITY
  bound. NET-007's withdrawn whole-operation budget is therefore PRESERVED.

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B11 — Bound the stall at the transport's surviving re-wait
source_blocks: ["B11"]
source_findings: ["TRN-007"]

description: >
  `if process.returncode is None: await process.wait()` carries no bound, and it is the only thing that
  can release a child once the reader has stopped. After D2 there is ONE such site: the one in
  `_download_with_ytdlp` (`download_with_ffmpeg`'s is deleted with the method).

  D3 SETTLES THE POLICY QUESTION REVISION 1 ESCALATED — in the way that PRESERVES the documented
  decision. The bound is an INACTIVITY bound: no output for N seconds. So NET-007's withdrawn
  whole-operation budget stays withdrawn, and `_download_with_ytdlp`'s "no application-level download
  timeout is imposed, avoiding premature kill of legitimate long downloads" sentence is STILL TRUE — a
  download that keeps producing output is never killed, however long it runs. The sentence needs an
  AMENDMENT naming the new setting and its inactivity semantics, not a reversal. (Revision 1 assumed
  otherwise and gated this block on Q2; that was wrong and D3 corrected it.)

  THE SETTING, fixed by D3: name `download_stall_timeout`; default `300.0`; `ge=30`, `le=3600` mirroring
  `download_timeout`; type `float` — the deliberate asymmetry with `download_timeout`'s `int` is
  recorded so no block "corrects" it; home `Settings` in `config.py` adjacent to `download_timeout`. Its
  field description must state, in its own words: it bounds the INACTIVITY of a download's output
  stream — the wait after the child's output has been consumed; on expiry the child is TERMINATED
  THROUGH THE EXISTING LADDER and the exception is RE-RAISED; it is NOT a whole-operation budget and a
  download that keeps producing output is never killed; and it does NOT apply to the merge subprocesses,
  which `download_timeout` already bounds. Three-place rule: field description + a commented
  `.env.example` row + a new row beside `download_timeout` in
  `docs/11-guides/configuration.md`.

  THE PATTERN TO COPY: `_await_ffmpeg_with_timeout`, signature `(process, timeout: float)` with NO
  DEFAULT so the bound cannot be forgotten, wrapping `process.communicate()` in
  `asyncio.wait_for(..., timeout=timeout)`, with an `except (TimeoutError, asyncio.CancelledError):`
  arm that re-enters `cancel_ffmpeg_process` and RE-RAISES. A new helper must have the same shape. A
  bare `asyncio.wait_for` around `process.wait()` is PROHIBITED — it would leave the child unreaped,
  which is the defect class B1 and B5 exist to close.

  WHY AN INACTIVITY BOUND RATHER THAN communicate(): the template drains both pipes in one call, but
  this bound is on the RE-WAIT — the wait after the reader consumed the stream — not on the drain. The
  reader is a separate task (B2, B4); folding it into `communicate()` would collapse the progress
  reporting and cancellation structure the reader owns. So the bound wraps the WAIT, and the inactivity
  semantics are implemented by the reader's continued liveness resetting the clock — which the block
  must state precisely, because "inactivity" has no meaning unless something measures it.

goals:
  - the post-drain wait is bounded by an inactivity limit read from Settings
  - a timeout re-enters the termination ladder and RE-RAISES
  - a child that keeps producing output is NEVER killed, however long it runs
  - the yt-dlp no-application-level-timeout sentence is AMENDED, never reversed
  - the new setting satisfies the three-place rule, and its .env.example value constructs against Settings
  - no whole-operation budget is introduced anywhere
  - ffmpeg_utils.py gains no import and the merge subprocesses are not re-bounded

files:
  - path: src/vkdownloader/config.py
    targets:
      - type: class
        name: Settings
    semantic_anchors:
      modify:
        - type: field
          name: download_stall_timeout
        - type: field
          name: download_timeout
      insert_after:
        type: field
        name: download_timeout

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _download_with_ytdlp
    semantic_anchors:
      modify:
        - type: guard_expression
          value: "if process.returncode is None:"
        - type: docstring
          value: "the no-application-level-download-timeout sentence"

  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: _await_ffmpeg_with_timeout
    semantic_anchors:
      read_only:
        type: function
        name: _await_ffmpeg_with_timeout

  - path: .env.example
    targets:
      - type: document
        name: the commented VKDOWNLOADER_DOWNLOAD_TIMEOUT row
    semantic_anchors:
      insert_after:
        type: document
        name: the commented VKDOWNLOADER_DOWNLOAD_TIMEOUT row

  - path: docs/11-guides/configuration.md
    targets:
      - type: document
        name: the download_timeout row — ADD BESIDE, DO NOT EDIT
    semantic_anchors:
      insert_after:
        type: document
        name: the download_timeout row

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestYtDlpSubprocessShutdown
    semantic_anchors:
      insert_after:
        type: class
        name: TestYtDlpSubprocessShutdown

changes:

  - action: modify
    description: >
      Add `download_stall_timeout: float = Field(default=300.0, ge=30, le=3600, description=...)` to
      `Settings` immediately after `download_timeout`, with the description specified at the block.
      Amend `download_timeout`'s own description ONLY to cross-reference the new field; its claimed
      boundary is unchanged. Then bound `_download_with_ytdlp`'s re-wait with a helper that copies
      `_await_ffmpeg_with_timeout`'s shape: a mandatory `timeout: float` with no default, an
      `asyncio.wait_for` around the wait, and an `except (TimeoutError, asyncio.CancelledError)` arm
      that re-enters `cancel_subprocess` and re-raises. Implement the inactivity semantics against the
      reader's liveness and state in the report exactly what counts as liveness.
    code_hint: |
      try:
          await asyncio.wait_for(process.wait(), timeout=timeout)
      except (TimeoutError, asyncio.CancelledError):
          await cancel_subprocess(process)
          raise

  - action: add_test
    description: >
      Add four cases. (1) THE STALL CASE: a child that emits its output and then goes silent — the call
      RETURNS within the bound AND the child is REAPED; assert both halves, because a timeout that
      leaves the child running is the failure this block must not ship. (2) THE LIVENESS CASE, which
      makes "inactivity" real and proves NET-007 was preserved: a child that keeps emitting output does
      NOT trip the bound, however long it runs. Without this a total-time bound would pass the whole
      suite. (3) The cancellation arm: cancelling the holder still propagates `CancelledError` AND the
      ladder still runs. (4) The setting: the default constructs against `Settings`; the documented
      `.env.example` value constructs against `Settings`; `ge=30` and `le=3600` reject out-of-range
      values.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT introduce a whole-operation budget — NET-007's withdrawal stands and D3 preserved it.
      MUST NOT reverse `_download_with_ytdlp`'s no-timeout sentence — only amend it. A bound MUST use
      `_await_ffmpeg_with_timeout`'s shape: a mandatory timeout with NO default, and the
      `except (TimeoutError, asyncio.CancelledError)` arm that re-enters the ladder and re-raises. A
      bare `asyncio.wait_for` around `process.wait()` is PROHIBITED. MUST NOT re-bound the merge
      subprocesses. MUST NOT edit the existing `download_timeout` row in
      `docs/11-guides/configuration.md` (plan 07 `C12`) — ADD a row beside it. `ffmpeg_utils.py` gains
      NO import. The new field is the ONLY `Settings` field this plan adds: no second knob, no alias.
      MUST NOT change the `--method` surface or touch B10's deletion.
    code_hint: |

acceptance_criteria:
  - >
    A child that emits then stalls: the call returns within the configured bound AND the child is reaped
    (new test, both halves asserted)
  - >
    A child that keeps emitting output is NEVER killed, however long it runs (new test) — the proof
    that NET-007's decision is preserved and not quietly reversed
  - A cancellation still propagates CancelledError and still reaps the child (new test)
  - The timeout arm re-enters the ladder and re-raises; no bare asyncio.wait_for around process.wait()
  - The default constructs against Settings; the .env.example value constructs against Settings;
    ge=30 / le=3600 reject out-of-range values (new tests)
  - >
    download_stall_timeout appears in exactly THREE places: field description, .env.example, and a new
    row in docs/11-guides/configuration.md
  - The existing download_timeout row in the configuration guide is byte-identical (plan 07 `C12`)
  - >
    `_download_with_ytdlp`'s docstring is AMENDED to name the setting and its inactivity semantics, and
    the "no application-level download timeout is imposed" claim is RETAINED, not reversed
  - download_timeout's own field description keeps its claimed boundary and gains only a cross-reference
  - TestYtDlpSubprocessShutdown and the yt-dlp drain trio are green UNCHANGED
  - ffmpeg_utils.py has no new import; the merge subprocesses are not re-bounded
  - >
    The COMMIT BODY carries the measured before/after, the liveness measurement, the amended sentence
    quoted before and after, and the explicit statement that NET-007 is PRESERVED, not reinstated
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B12

```yaml
id: plan10-b12-process-boundary-minimum-platform-keyword
title: Establish a process boundary: the minimum platform keyword, with the Windows residual documented
priority: high
depends_on: [B5]
DECIDED: D1 plus the standing Tech Lead decision. No gate.

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B12 — Establish a process boundary: the minimum platform keyword
source_blocks: ["B12"]
source_findings: ["TRN-003"]

description: >
  A search of `src/` for `start_new_session`, `setsid`, `process_group`, `creationflags`,
  `startupinfo`, `CREATE_NEW_PROCESS_GROUP`, `CREATE_BREAKAWAY_FROM_JOB`, `JobObject`,
  `AssignProcessToJobObject` and `taskkill` returns NO API USAGE ANYWHERE. `env=` and `cwd=` are
  absent from every spawn. The termination ladder addresses `process.pid` and nothing else — no
  `pgid`, no `killpg`, no tree walk — so a process the child creates for itself outlives the command.
  Reproduced: a stub child that spawns a process of its own, then the product's own
  `cancel_subprocess` on the direct child, gives `direct_alive=False grandchild_alive=True` with the
  call reporting success.

  THE SCOPE IS DECIDED: the minimum platform-appropriate keyword per spawn — `start_new_session=True` on
  POSIX (which creates a session and makes `killpg` possible, so descendants are reachable) and
  `creationflags=CREATE_NEW_PROCESS_GROUP` on Windows, with a matching `os.killpg` branch in
  `cancel_subprocess`. A WINDOWS JOB OBJECT IS REJECTED: it is the only option that fully closes the
  finding on Windows, and it costs a `ctypes`/pywin32 wrapper, a platform guard, a handle lifecycle
  that is not a small thing to get wrong, and a packaging-gate relaxation for a new `src/` module —
  against project rule 5 at this project's scale. A descendant sweep is rejected outright.

  D1 IS THE REASON THE WINDOWS RESIDUAL IS ACCEPTABLE, and the block must state this honestly: on a
  single-user desktop a surviving orphan holds a file open on the user's own machine, where the user can
  see it, and the direct child — which holds the credential material — is killed either way.
  `CREATE_NEW_PROCESS_GROUP` gives a new process group, but a new process group is NOT a killable tree
  by pid, so on Windows a grandchild can still outlive the command. That residual is DOCUMENTED, not
  hidden: the limitations guide states it, the commit body states it, and the test asserts it.

  RE-SCOPED BY D2: four spawn sites become THREE (`download_with_ffmpeg`'s is deleted). The yt-dlp child
  is now the ONLY transport, so a boundary gap there has no sibling transport to hide behind — D2 makes
  the structural point sharper, not weaker.

  The commit body must state the failure scenario's CONDITIONAL form (`--hls-prefer-native` steers
  yt-dlp to its own HLS downloader), not the unconditional one the source report used.

goals:
  - a descendant does not outlive the command on POSIX, to the extent the chosen mechanism delivers
  - the Windows outcome is asserted honestly as a PARTIAL closure, not presented as a fix
  - the residual is documented in the limitations guide, with D1 as its justification
  - cancel_subprocess's signature, keyword-only timeout and return contract are untouched
  - the two Playwright-mediated launches are not modified and are not claimed to be bounded
  - no env=, cwd= or limit= is introduced anywhere

files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _download_with_ytdlp
    semantic_anchors:
      modify:
        type: function_call
        value: "asyncio.create_subprocess_exec("

  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: cancel_subprocess
      - type: function
        name: _merge_batch_segments
      - type: function
        name: _perform_final_merge
    semantic_anchors:
      modify:
        - type: function
          name: cancel_subprocess
        - type: function_call
          value: "asyncio.create_subprocess_exec("

  - path: src/vkdownloader/infrastructure/browser.py
    targets:
      - type: method
        name: __aenter__
        owner: BrowserManager
    semantic_anchors:
      read_only:
        - type: function_call
          value: "async_playwright().start()"
        - type: function_call
          value: "self.playwright.chromium.launch("

  - path: docs/11-guides/vkdownloader-limitations.md
    targets:
      - type: document
        name: the limitations entry — the Windows residual is documented here
    semantic_anchors:
      insert_after:
        type: document
        name: the existing limitations entries

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestYtDlpSubprocessShutdown
    semantic_anchors:
      insert_after:
        type: class
        name: TestYtDlpSubprocessShutdown

changes:

  - action: modify
    description: >
      Add the platform keyword to all THREE asyncio-mediated spawn sites (`_download_with_ytdlp`,
      `_merge_batch_segments`, `_perform_final_merge`) and make `cancel_subprocess` able to signal the
      tree: a guarded `os.killpg` branch for the POSIX session, and the new process group on Windows. The
      platform guard must be explicit and stated, not assumed. Do NOT modify the two Playwright-mediated
      launches; record that they cannot be bounded here.
    code_hint: |
      if sys.platform != "win32" and hasattr(process, "pid"):
          try:
              os.killpg(os.getpgid(process.pid), signal.SIGTERM)
          except (ProcessLookupError, PermissionError):
              process.terminate()

  - action: add_test
    description: >
      Add three cases. (1) THE DESCENDANT CASE: a stand-in child that spawns a process of its own;
      after the ladder runs, assert the descendant is GONE. The test must FIRST assert the stand-in
      really did spawn something — a test that passes because the child never spawned is not a test.
      (2) THE PLATFORM-ASYMMETRY CASE: assert what happens on Windows specifically. On Windows this
      test asserts the grandchild SURVIVES; that is the honest outcome under this decision, and a test
      that quietly asserted otherwise would be a lie. (3) MUST STAY GREEN UNCHANGED: `TestCancelSubprocess`
      in full, `TestYtDlpSubprocessShutdown`, and the yt-dlp drain trio.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT introduce a Job Object, `CREATE_BREAKAWAY_FROM_JOB`, a descendant sweep, or a `taskkill`
      shell-out — all three were considered and rejected. MUST NOT touch `cancel_subprocess`'s
      signature, keyword-only `timeout` or return contract (B5's). MUST NOT modify the two
      Playwright-mediated launches, and no test may assert they are bounded. MUST NOT introduce `env=`
      or `cwd=` (`TRN-010`'s measured-closed half). MUST NOT pass `limit=` at any spawn site (B2's
      prohibition 7). `ffmpeg_utils.py` gains NO import beyond the platform-guarded `os.killpg` path,
      which needs only the already-imported `os`. MUST NOT present the Windows outcome as a closure.
    code_hint: |

acceptance_criteria:
  - >
    Descendant alive after the ladder: before True; after — gone on POSIX, STILL ALIVE on Windows, and
    the Windows test asserts that honestly
  - The stand-in is asserted to have spawned its own child before the descendant is probed
  - The limitations guide documents the Windows residual with D1 as its justification
  - >
    tests/test_ffmpeg_utils.py::TestCancelSubprocess is green UNCHANGED, including
    test_returns_false_on_process_lookup_error, test_terminate_on_success and test_kill_on_timeout
  - cancel_subprocess's signature, keyword-only timeout and return type are byte-identical
  - browser.py is not modified and no test claims the Playwright launches are bounded
  - No env=, cwd= or limit= appears anywhere in the diff; no Job Object and no taskkill
  - >
    The COMMIT BODY names the mechanism per platform, the rejected options and why, the measured
    before/after, the explicit Windows residual with D1 as its justification, and the conditional form
    of the failure scenario
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B13

```yaml
id: plan10-b13-availability-answer-three-arms
title: Stop discarding the availability answer, and stop one absence surfacing three ways
priority: medium
depends_on: [B10]
DECIDED: D6 (Tech Lead) — option (B), better degradation. No gate.

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B13 — Stop discarding the availability answer, and stop one absence surfacing three ways
source_blocks: ["B13"]
source_findings: ["TRN-008"]

description: >
  `check_ffmpeg_available` has exactly ONE call site in src/ — the bare expression statement in
  perform_download — and its return value is dropped; no branch anywhere depends on it. The answer is
  cached write-once with no re-derivation and no invalidation hook, so a machine that loses the muxer
  mid-session keeps the cached True and emits nothing.

  RE-DERIVED AFTER D2: FOUR ARMS BECOME THREE, re-read against the post-deletion tree:
    (a) muxer download path's `except OSError` recording ffmpeg_download_failed — DELETED with
        download_with_ffmpeg.
    (b) merge — `_merge_batch_segments` and `_perform_final_merge` still have NO `OSError` arm around
        `await _await_ffmpeg_with_timeout(...)`, so the merge's raw FileNotFoundError escapes uncaught
        and produces NO product record. Now the sharpest arm, and the least tested.
    (c) downloader — `_download_with_ytdlp`'s `except FileNotFoundError:` arm logs
        `ytdlp_not_found`, NOT `download_failed`. There is NO `ModuleNotFoundError` arm in the module;
        a missing module surfaces as the child's non-zero exit through the ordinary returncode != 0 arm.
    (d) resume — `_attempt_segment_resume`'s `except (ExtractionError, OSError)` catches the merge's
        FileNotFoundError and logs it as `failed_to_refresh_token`.

  check_ffmpeg_available IS STILL LIVE: a yt-dlp or auto download reaches
  download_with_ytdlp_with_resume_fallback -> download_hls_with_resume -> _merge_segments_batched ->
  the merge helpers, and SEGMENT MERGING STILL NEEDS THE MUXER. D2 deletes a consumer of the probe, not
  the probe's reason to exist.

  D6 SETTLES THE REMEDY — option (B), better degradation. The reason is D2: with the explicit ffmpeg
  transport deleted there is no longer a user-selected transport to violate, so a hard failure would
  break EVERY HLS download on a muxer-less machine for no user benefit.

  FOUR REQUIREMENTS, ONE PROHIBITION:
    1. Emit ONE actionable warning naming the install step, following the `check_ffmpeg_available`
       convention — a single `logger.warning(<event>, hint=...)` whose `hint` names what is missing and
       what will fail. The probe already emits such a warning on first derivation; the finding is that
       it is a warning AND NOTHING ELSE.
    2. USE the probe's answer at its single call site instead of discarding it. This is the finding's
       structural core: the bare expression statement becomes a bound value the warning path consults.
    3. Narrow `_attempt_segment_resume`'s `except (ExtractionError, OSError)` so a FileNotFoundError
       is reported as the missing dependency it is. MANDATORY under any option.
    4. Give arm (b) a product record.
    PROHIBITED: any exit-code change, and any branch on the probe's answer that raises or returns early.

goals:
  - no branch depends on a discarded value: the probe's answer is used at its single call site
  - one missing muxer produces ONE actionable warning naming the install step
  - arm (b) produces a product record instead of an escaping exception
  - arm (d) never reports a missing binary as a token problem
  - no exit-code change anywhere: a missing muxer does not fail the download
  - no Settings field, no environment variable, no CLI option

files:
  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: check_ffmpeg_available
      - type: function
        name: _merge_batch_segments
      - type: function
        name: _perform_final_merge
    semantic_anchors:
      modify:
        - type: assignment
          value: _ffmpeg_available
        - type: guard_expression
          value: "if _ffmpeg_available is None:"
        - type: try_statement
          value: "the await _await_ffmpeg_with_timeout(...) in each merge"
        - type: function_call
          value: "logger.warning(\"ffmpeg_not_found\", hint=...)"

  - path: src/vkdownloader/services/downloader.py
    targets:
      - type: method
        name: perform_download
        owner: HLSDownloader
    semantic_anchors:
      modify:
        - type: expression_statement
          value: "check_ffmpeg_available()"

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _attempt_segment_resume
      - type: function
        name: _download_with_ytdlp
    semantic_anchors:
      modify:
        - type: except_clause
          value: "except (ExtractionError, OSError) as e:"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestFfmpegAvailabilityCheck
    semantic_anchors:
      insert_after:
        type: class
        name: TestFfmpegAvailabilityCheck

changes:

  - action: modify
    description: >
      (Req 1, 2) Bind the probe's answer where it is called and emit ONE actionable warning when it is
      False. REUSE the convention already in `check_ffmpeg_available` — `logger.warning(<event>,
      hint=(<what is missing>; <what will fail>))` — rather than inventing a message shape. Decide and
      RECORD whether the write-once cache gains an invalidation path; the report must say which, and
      the caches test is re-scoped only in the invalidation case.
      (Req 3) Narrow `_attempt_segment_resume`'s except clause so a `FileNotFoundError` is reported as
      the missing dependency it is, while a genuine `ExtractionError` still reaches
      `failed_to_refresh_token`.
      (Req 4) Add the missing `OSError` arm to both merge paths, carrying the same actionable text.
      Note `_check_merge_space` already has its own `except OSError` arms: the merge SPACE probe is
      handled, the merge SPAWN is not.
    code_hint: |
      # (Req 2) the discarded answer, now used
      if not check_ffmpeg_available():
          logger.warning("ffmpeg_missing_for_merge", hint=_MERGE_HINT)

  - action: add_test
    description: >
      Add five cases. (1) ARM (B), which NO test covers today and which is the most valuable single test
      in the block: the merge path with no muxer produces ONE actionable record naming the install
      step, instead of an escaping exception. (2) Arm (d): a `FileNotFoundError` from the merge is NOT
      logged as `failed_to_refresh_token`, and a genuine `ExtractionError` STILL IS. (3) Arm (c): the
      `FileNotFoundError` arm's record names the missing binary. (4) THE PROBE'S ANSWER IS USED: with the
      probe forced to False, the call site emits exactly ONE warning, and does NOT raise and does NOT
      change the exit code — the "does not change the exit code" half is D6's explicit instruction and
      must be ASSERTED, not assumed. (5) The cache: the chosen behaviour, and that a SECOND absence is
      not silent. RE-SCOPE `test_check_ffmpeg_available_caches_result` ONLY in the invalidation case;
      otherwise it stays green UNCHANGED and the report says so.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT hard-fail. No branch on the probe's answer may raise, return early, or change an exit
      code — D6 is explicit that this would break every HLS download on a muxer-less machine. The
      `_attempt_segment_resume` narrowing is MANDATORY and is not optional under any reading. MUST NOT
      emit more than one warning for one absence. MUST NOT edit `download_with_ffmpeg` or add an
      arm-(a) test — that transport is deleted. MUST NOT add a `Settings` field, an environment
      variable or a CLI option; D3's `download_stall_timeout` and D5's `stealth_enabled` are unrelated
      and belong to B11 and B15. MUST NOT replace `shutil.which` and MUST NOT introduce an executable
      allow-list. Arm (d)'s `QualityParseError` arm stays reachable; the two arms may not be merged.
    code_hint: |

acceptance_criteria:
  - Arm (b) produces exactly one actionable record naming the install step instead of an escaping
    FileNotFoundError (new test)
  - A FileNotFoundError is never logged as failed_to_refresh_token; a real ExtractionError still is
    (new test)
  - Arm (c)'s record names the missing binary (new test)
  - >
    With the probe forced to False: exactly ONE warning, NO raise, NO exit-code change (new test —
    this is D6's instruction, asserted rather than assumed)
  - The probe's answer is USED at its single call site — the bare expression statement is gone
  - The cache behaves as the chosen shape specifies and a second absence is not silent
  - >
    TestFfmpegAvailabilityCheck is green: test_check_ffmpeg_available_returns_bool UNCHANGED always,
    and test_check_ffmpeg_available_caches_result UNCHANGED unless explicitly re-scoped (the report
    says which)
  - >
    The obligation Revision 1 assigned here — an arm-(a) test — is DISCHARGED BY DELETION, not
    weakened: the method it drove is gone
  - No Settings field, no environment variable, no CLI option exists
  - No test claims the deleted transport's arms are reachable
  - >
    The COMMIT BODY names D6, states that arm (a) was DELETED with the transport, that
    check_ffmpeg_available remains live for the merge path, that the probe's answer is now USED, and
    that NO exit code changes
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B14

```yaml
id: plan10-b14-redact-the-two-untransformed-merge-sinks
title: Apply the redaction transform at the two untransformed merge sinks
priority: medium
depends_on: [B7, B10]
DECIDED: the Q5 ownership split. This plan takes the two UNOWNED merge sinks; phase 06 keeps the
  yt-dlp terminal echo and the path-matching capability. No gate.

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B14 — Apply the redaction transform at the two untransformed merge sinks
source_blocks: ["B14"]
source_findings: ["TRN-009"]

description: >
  SHRUNK BY THE Q5 DECISION. Revision 1's block was gated on an unresolved ownership question and
  contemplated extending the matcher. Both are gone. Phase 06's own R5(d) table records TRN-009's two
  halves under phase-06 ids — "a bare path is not matchable at all (filed as SEC-006); the stderr echo
  applies nothing (SEC-005)" — so TRN-009 is a DUPLICATE of SEC-005 + SEC-006, not a novel finding. The
  split is by sink, and it loses no coverage because the two sinks this block takes are in NEITHER
  phase's set:

    _merge_batch_segments' batch_merge_failed   -> THIS PLAN   (unowned)
    _perform_final_merge's final_merge_failed    -> THIS PLAN   (unowned)
    _echo_ytdlp_line's sys.stderr.write          -> PHASE 06    (SEC-005)
    the path-matching capability in _URL_REGEX   -> PHASE 06    (SEC-006)

  So this block does two things and explicitly not two others. It applies sanitize_text_for_log at two
  call sites. It does NOT extend the matcher and does NOT touch the console echo.

  WHAT D2 CHANGED: nothing in this block's subject — all three sinks are in the merge and yt-dlp paths,
  and D2 deletes neither. It changed the sibling claim: sanitize_text_for_log's docstring and one
  SEC-002 comment die with the transport (B7), so after B10 these two sinks are the clearest evidence
  that a claim about the transform's reach has drifted from what the transform does.

  D1 IS RECORDED HERE AND CHANGES NOTHING IN THIS BLOCK: on a single-user desktop the operator can
  already read their own process list, so a cookie path in argv is moot for this deployment. This block
  is worth doing on CORRECTNESS grounds — a log file is not a process listing, and a log file persists —
  not on exposure grounds.

goals:
  - both merge sinks apply the transform, BEFORE truncating
  - _URL_REGEX, sanitize_text_for_log's body and _strip_auth_params are byte-identical
  - _echo_ytdlp_line is byte-identical
  - the two already-transformed records keep transforming
  - no shared sink abstraction is introduced

files:
  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: _merge_batch_segments
      - type: function
        name: _perform_final_merge
      - type: import_block
        name: the module's imports
    semantic_anchors:
      modify:
        - type: function_call
          value: "logger.error(\"batch_merge_failed\", error=error[:200])"
        - type: function_call
          value: "logger.error(\"final_merge_failed\", error=stderr.decode()[:200] ...)"
        - type: import_block
          value: the module's imports — add sanitize_text_for_log
      read_only:
        - type: function
          name: _await_ffmpeg_with_timeout
        - type: function
          name: cancel_subprocess

  - path: src/vkdownloader/utils/url_sanitizer.py
    targets:
      - type: assignment
        name: _URL_REGEX
      - type: function
        name: sanitize_text_for_log
      - type: function
        name: _strip_auth_params
    semantic_anchors:
      read_only:
        - type: assignment
          value: _URL_REGEX
        - type: function
          name: sanitize_text_for_log
        - type: function
          name: _strip_auth_params

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _echo_ytdlp_line
    semantic_anchors:
      read_only:
        - type: function_call
          value: "sys.stderr.write("

  - path: tests/test_url_sanitizer.py
    targets:
      - type: class
        name: TestSanitizeTextForLog
    semantic_anchors:
      insert_after:
        type: class
        name: TestSanitizeTextForLog

changes:

  - action: modify
    description: >
      Apply sanitize_text_for_log at both merge sinks, TRANSFORMING FIRST AND TRUNCATING SECOND. The
      order is the whole point: both records currently truncate to 200 characters, so truncating first
      can cut a URL in half and defeat the redaction. Add the import. This is the FIRST import this plan
      adds to ffmpeg_utils.py and the only place §5.2's leaf constraint is knowingly relaxed — it is
      justified because the transform lives in `utils`, a layer the module is already permitted to
      import from, and the alternative would route a security-relevant operation away from the sink
      that emits it. The report MUST say this explicitly so the new import does not look incidental.
    code_hint: |
      from ..utils.url_sanitizer import sanitize_text_for_log
      ...
      logger.error(
          "batch_merge_failed",
          error=sanitize_text_for_log(error)[:200],   # transform, THEN truncate
      )

  - action: add_test
    description: >
      Add four cases. (1) The merge sinks: `batch_merge_failed` and `final_merge_failed` now carry
      TRANSFORMED text — drive each with a muxer error line naming a signed CDN URL and assert the
      token is absent from the record. (2) THE ORDERING PROOF, which is the subtle one: a URL whose
      redacted form would be CUT IN HALF by the 200-character truncation must still be fully redacted.
      This distinguishes transform-then-truncate from truncate-then-transform, and only the wrong order
      passes a naive test. (3) THE CAPABILITY BOUNDARY, so phase 06's later matcher work cannot silently
      break these two sites: a bare path is asserted UNCHANGED after this block — honest about what the
      transform does today, and it fails loudly the day someone extends the matcher. (4) MUST STAY GREEN
      UNCHANGED: `TestStripAuthParams` in full, `TestSanitizeTextForLog`'s four existing cases, and all
      four `TestEchoYtdlpLine::test_ytdlp_echo_false_*` cases.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT extend `_URL_REGEX` or add any path-matching capability — that is phase 06's `SEC-006`.
      MUST NOT touch `_echo_ytdlp_line` or apply any transform on the console write path — that is
      phase 06's `SEC-005`. MUST NOT remove the 200-character truncation; it bounds the record and
      removing it is a separate concern. MUST NOT change `sanitize_text_for_log`'s behaviour or
      `_strip_auth_params`'s URL contract. MUST NOT remove the transform from the two already-transformed
      records. MUST NOT generalise into a shared sink helper: two call sites do not need an abstraction
      (rule 5), and a helper is exactly the new surface the Q5 split was meant to avoid.
    code_hint: |

acceptance_criteria:
  - batch_merge_failed and final_merge_failed carry transformed text (new test)
  - >
    A URL whose redacted form would be cut in half by the 200-character truncation is still fully
    redacted (new test — this is what pins transform-then-truncate)
  - A bare path is asserted UNCHANGED by both sinks (new test — the capability boundary)
  - _URL_REGEX, sanitize_text_for_log's body and _strip_auth_params are byte-identical
  - _echo_ytdlp_line is byte-identical; no transform reaches the console write path
  - The 200-character truncation is intact at both sinks
  - >
    TestStripAuthParams, TestSanitizeTextForLog's four existing cases and all four
    test_ytdlp_echo_false_* cases are green UNCHANGED
  - No shared sink abstraction was introduced
  - >
    The COMMIT BODY carries the Q5 split table, the measured before/after for a signed URL in a merge
    error (changed: before False, after True), the transform-then-truncate ordering proof, and the
    explicit statement that the matcher and the console echo belong to phase 06 and are untouched. It
    must also state why the new import into ffmpeg_utils.py is justified against the leaf constraint.
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B15

```yaml
id: plan10-b15-stealth-opt-in-setting
title: Gate the stealth posture behind stealth_enabled, and hard-fail only when explicitly enabled
priority: medium
depends_on: [B5, B8, B11]
DECIDED: D5 (Product Owner) — stealth is opt-in, default OFF. Supersedes D4's unconditional hard
  failure. The owner, verbatim: "я бы хотел, чтобы скачивающий сам решал нужен stealth или нет. Т.е.
  это должно быть configurable по умолчанию отключено." — "I would like the downloader itself to decide
  whether stealth is needed. That is, it should be configurable, disabled by default."

source_reference: .ai/plans/10-subprocess-browser-audit-fixes.md
source_section: B15 — Gate the stealth posture behind stealth_enabled
source_blocks: ["B15"]
source_findings: ["BRW-003"]

description: >
  BRW-003 was "the asset's absence is silent at every log level". D5 splits it in two:

    stealth_enabled False (the default) -> nothing consults the asset at all. No check, no warning, no
      failure. THE FINDING'S ORIGINAL FORM DISSOLVES: silence about an asset that was never asked for
      is not a defect.
    stealth_enabled True, asset present -> injection proceeds as today.
    stealth_enabled True, asset missing -> HARD FAILURE before the driver starts, message naming the
      path and the remedy. The user asked for stealth and cannot have it; extraction would fail
      downstream anyway, so failing fast at the cheapest point is strictly better than a confusing late
      failure — and because D5 makes it conditional on an explicit opt-in, the user who gets it is one
      who asked for it.

  THE STEALTH POSTURE IS FOUR COMPONENTS, NOT ONE — established from the code:
    GATED:    (1) the `--disable-blink-features=AutomationControlled` launch argument in __aenter__;
              (2) the `add_init_script(path=stealth.min.js)` injection in create_stealth_page.
              Both exist solely to defeat automated-browser fingerprinting, and both are suppressed when
              stealth is off — suppressing them while claiming stealth would make detection harder to
              diagnose.
    NOT GATED:(3) the context identity triple `viewport` / `user_agent` / `locale` / `timezone_id`;
              (4) the two DEBUG records.
              (3) is ordinary browser configuration, NOT evasion: `settings.user_agent` is consumed by
              FOUR call sites — the browser context, segment_downloader's HTTP User-Agent header,
              yt-dlp's --user-agent, and the ffmpeg transport's -headers value (deleted by B10) — so
              it is request identity for the whole download path and gating it at the Settings level
              would break the other three. `viewport` is a hard-coded literal, not a setting at all.
              `locale` and `timezone` are consumed ONLY by the browser context, so gating them would
              be technically safe — but they SHOULD NOT be: a Russian locale and a Moscow timezone are
              what a real user's browser looks like, so applying them is CORRECTNESS, not evasion, and
              suppressing them would make extraction less likely to succeed for a user in that region
              for no gain. Their field DESCRIPTIONS are corrected rather than acted on, because
              "for browser stealth configuration" is what made them look like stealth at all.
              `user_agent`'s description is already accurate and is UNCHANGED.

  THE NEW SETTING:
    name     stealth_enabled
    type     bool — D5 says configuration, not policy. NOT an enum, NOT a tri-state: "no preference" is
              answered by the user's answer.
    default  False — "по умолчанию отключено".
    home     Settings, in the existing "# Browser Automation settings" group, IMMEDIATELY AFTER
              `locale`.
    form     `stealth_enabled: bool = Field(default=False, description=...)` — matching the sibling
              convention exactly: `headless: bool = Field(default=False, description=...)`. A bool field
              carries NO `ge`/`le` and NO `@field_validator`, because it has no out-of-range value; the
              existing validator on user_agent/timezone/locale exists only to reject empty STRINGS,
              which cannot happen to a bool. A validator here would be overengineering (rule 5).
    descr    Must state: it gates the anti-detection measures (the automation-suppression launch
              argument and the stealth.min.js init script); it does NOT gate the context's viewport,
              user agent, locale or timezone; when enabled the asset is REQUIRED and its absence is a
              hard error; and it is OFF by default.
    3 places field description + a commented `.env.example` row + a new row in
             docs/11-guides/configuration.md. `model_config`'s extra="forbid" makes an unrecognised
             VKDOWNLOADER_* an error, so this is a correctness requirement, not a courtesy — phase 02
             found exactly that bug class.
    env pos  appended as the LAST row of the existing Browser Automation block (after
             VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT), so the block's order is untouched.

  WHERE THE GATE LIVES: in BrowserManager, read from `self.settings.stealth_enabled` at the two
  consumption points. NOT a computed property on Settings, and nothing in Settings beyond the field:
  Settings holds data, BrowserManager owns the posture. No policy object, no profile list, no
  heuristic, no CLI subcommand — D5 is a flag.

  WHERE THE ASSET CHECK BELONGS: `__aenter__`, BEFORE `async_playwright().start()`. Verified this
  actually works. `__init__` assigns `self._stealth_path` before any I/O, so the value is available at
  the first statement of `__aenter__`. And because Python's `async with` does NOT call `__aexit__`
  when `__aenter__` raises, placing the check before the driver start means nothing needs releasing —
  whereas the existing `except Exception` arm's explicit `await playwright_instance.stop()` exists
  precisely BECAUSE it runs after the driver started. The single call site, extractor.py's
  `async with BrowserManager(self.settings) as browser:` followed by
  `page = await browser.create_stealth_page()`, has NO try/except around either, so a raise propagates
  out of the extraction — exactly the fail-fast behaviour D5 asks for.
  Rejected: `create_stealth_page` (Chromium already launched, must be torn down for nothing, and the
  raise comes from inside the caller's async with body). Rejected: `__init__` (synchronous; turns a
  typed extraction failure into a construction-time exception at every site, outside the context
  manager).

  EXCEPTION TYPE: ExtractionError. Unchanged from D4's analysis. No new exception class. The caller does
  NOT need to distinguish "asset missing" from "browser unavailable": both mean extraction cannot run,
  the single call site has no handler to distinguish in, and the MESSAGE carries it. One ErrorCode
  StrEnum member IS added, because ErrorCode exists for stable machine-readable log filtering and a
  missing asset is a different operational cause from a browser that will not launch.

  MESSAGE SHAPE: reuse check_ffmpeg_available's convention —
  `logger.warning(<event>, hint=("<what is missing>; <what will fail>"))` — with the SAME text in the
  raised ExtractionError. Must name (a) the missing path, (b) that the asset is a declared build
  artefact so a missing file means a broken build or partial deployment, and (c) that stealth was
  explicitly enabled and cannot be satisfied.

  THE BEHAVIOUR CHANGE, LOUDLY: stealth was ALWAYS ON. Defaulting the flag to False REMOVES stealth
  from every existing user's default run. That is what D5 asks for, and it interacts with the reason D4
  was raised — on a bot-protected origin the new default is the setting least likely to work. Recorded,
  not resolved; the block makes it visible, it does not soften it.

goals:
  - stealth is the user's choice, off by default, and the default is stated in three places
  - exactly two of the four stealth components are gated; the context identity triple is not
  - with the flag false, nothing consults the asset: no check, no warning, no failure
  - with the flag true and the asset missing, ExtractionError is raised BEFORE the driver starts
  - one ErrorCode StrEnum member, no new exception class
  - eleven documentation claims and docstrings that assumed always-on stealth are corrected
  - __exit__ and B8's four anchors are untouched

files:
  - path: src/vkdownloader/config.py
    targets:
      - type: class
        name: Settings
    semantic_anchors:
      modify:
        - type: field
          name: stealth_enabled
        - type: field
          name: timezone
          note: "description only — corrected, NOT gated"
        - type: field
          name: locale
          note: "description only — corrected, NOT gated"
      insert_after:
        type: field
        name: locale

  - path: src/vkdownloader/infrastructure/browser.py
    targets:
      - type: class
        name: BrowserManager
      - type: method
        name: __aenter__
        owner: BrowserManager
      - type: method
        name: create_stealth_page
        owner: BrowserManager
    semantic_anchors:
      modify:
        - type: function_call
          value: "args=[\"--disable-blink-features=AutomationControlled\"]"
        - type: guard_expression
          value: "if self._stealth_path.exists():"
        - type: docstring
          name: "BrowserManager's class docstring"
        - type: docstring
          name: "__aenter__'s docstring"
        - type: docstring
          name: "create_stealth_page's docstring and Returns: line"
      insert_before:
        type: function_call
        value: "async_playwright().start()"
      read_only:
        - type: assignment
          value: "self._stealth_path = Path(__file__).parent.parent / \"stealth.min.js\""
        - type: except_clause
          value: "except Exception:"
        - type: function_call
          value: "await playwright_instance.stop()"
        - type: method
          name: __aexit__
        - type: function_call
          value: "await self.browser.new_context("
        - type: function_call
          value: "logger.debug(\"creating_stealth_page\")"
        - type: function_call
          value: "logger.debug(\"stealth_script_applied\")"

  - path: src/vkdownloader/models/enums.py
    targets:
      - type: class
        name: ErrorCode
    semantic_anchors:
      modify:
        type: class
        name: ErrorCode

  - path: .env.example
    targets:
      - type: document
        name: the Browser Automation block
    semantic_anchors:
      insert_after:
        type: document
        name: the VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT row

  - path: docs/11-guides/configuration.md
    targets:
      - type: document
        name: the browser settings table
    semantic_anchors:
      insert_after:
        type: document
        name: the locale row

  - path: docs/01-tools/vkdownloader-overview.md
    targets:
      - type: document
        name: the Secure-by-default stealth claim; the Browser settings bullet; the module table row
  - path: docs/01-tools/api-reference.md
    targets:
      - type: document
        name: the BrowserManager and create_stealth_page() entries
  - path: docs/01-tools/quality-selection.md
    targets:
      - type: document
        name: the Opens video page in stealth browser step
  - path: docs/11-guides/vkdownloader-limitations.md
    targets:
      - type: document
        name: the navigator.webdriver masked-by-stealth.min.js note

  - path: tests/test_browser_infrastructure.py
    targets:
      - type: class
        name: TestBrowserManager
    semantic_anchors:
      insert_after:
        type: class
        name: TestBrowserManager

  - path: tests/test_config.py
    targets:
      - type: function
        name: test_settings_defaults
    semantic_anchors:
      insert_after:
        type: function
        name: test_settings_defaults

changes:

  - action: add_setting
    description: >
      Add `stealth_enabled: bool = Field(default=False, description=...)` to Settings immediately after
      `locale` in the Browser Automation group, with the description specified at the block. Correct
      the `timezone` and `locale` field descriptions (they say "for browser stealth configuration",
      which is misleading — they are ordinary context configuration). Leave `user_agent`'s description
      alone; it is already accurate. Add the `.env.example` row and the configuration-guide row, and
      construct the `.env.example` value against `Settings` and record the construction in the report.
    code_hint: |
      stealth_enabled: bool = Field(
          default=False,
          description="Enable browser anti-detection measures: the automation-suppression "
                      "launch argument and the stealth.min.js init script. Does not affect the "
                      "browser context's viewport, user agent, locale or timezone. When enabled, "
                      "stealth.min.js is required and its absence is a hard error. Disabled by default.",
      )

  - action: gate_components
    description: >
      Gate component 1 at the launch call and component 2 at the injection, both on
      `self.settings.stealth_enabled`. Place the conditional asset check in `__aenter__` BEFORE
      `async_playwright().start()`: when the flag is true and the asset is absent, emit one record in
      `check_ffmpeg_available`'s `hint` shape and raise `ExtractionError` carrying the SAME text. Add
      ONE `ErrorCode` StrEnum member. Leave `create_stealth_page`'s `if self._stealth_path.exists():`
      guard in place as defence in depth — it is the last line before a page is handed out — and
      update the docstrings to say the page carries the injected script iff the flag is on.
    code_hint: |
      # __aenter__, before the driver
      if self.settings.stealth_enabled and not self._stealth_path.exists():
          hint = (
              f"stealth.min.js not found at {self._stealth_path}; it is a declared build artefact, "
              f"so this indicates a broken build or a partial deployment, and stealth was "
              f"explicitly enabled and cannot be satisfied"
          )
          logger.error("stealth_script_missing", hint=hint)
          raise ExtractionError(hint)
      playwright_instance = await async_playwright().start()

      # create_stealth_page
      if self.settings.stealth_enabled and self._stealth_path.exists():
          await page.add_init_script(path=str(self._stealth_path))
          logger.debug("stealth_script_applied")

  - action: edit_tests
    description: >
      Add nine cases. (1) The flag default: `Settings()` has `stealth_enabled is False`; the
      `.env.example` value constructs; `VKDOWNLOADER_STEALTH_ENABLED=true` constructs. (2) Stealth OFF,
      asset present: the launch `args` does NOT contain the automation-suppression argument and
      `add_init_script` is NOT called; the page is still returned. (3) Stealth OFF, asset ABSENT: no
      error, no warning, and NO check — nothing consults `self._stealth_path`. This case dissolves
      BRW-003 and must exist, because a block that "helpfully" checks regardless of the flag would
      reintroduce the always-on posture in a different shape. (4) Stealth ON, asset present: the launch
      `args` DOES contain the argument and `add_init_script` IS called. (5) Stealth ON, asset missing:
      `__aenter__` raises `ExtractionError`; the message names the path, the broken-build consequence
      and the remedy. (6) THE ORDERING PROOF — THE GATE: on that path,
      `async_playwright().start()` is NEVER called. (7) `ErrorCode`: the raised exception's
      `error_code` is the new member, not `EXTRACTION_ERROR`. (8) COMPONENT 3 IS NOT GATED: with the
      flag false, `new_context` is still called with the configured `user_agent`, `locale`,
      `timezone_id` and the 1920x1080 viewport — this pins `S1h` so a later consistency argument cannot
      quietly gate them. (9) MUST STAY GREEN UNCHANGED: the six plan-08 `B4` tests for `__aexit__` and
      `B8`'s re-scoped launch-failure case.
    code_hint: |
      # the ordering proof
      with patch.object(BrowserManager, "_stealth_path", tmp_path / "absent.js"), \
           patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw, \
           patch("vkdownloader.infrastructure.browser.logger") as mock_logger:
          with pytest.raises(ExtractionError):
              async with BrowserManager(settings_with_stealth_on):
                  pass
      mock_pw.return_value.start.assert_not_called()      # never reached the driver

  - action: edit_documentation
    description: >
      Correct the eleven claims and docstrings listed in §3 `B15` that assume always-on stealth. The
      load-bearing one is `docs/01-tools/vkdownloader-overview.md`'s "Secure-by-default browser
      stealth configuration" — D5 reverses that claim outright. `docs/STRUCT.md`'s entry is a FILE
      LISTING, not a claim about when the asset is applied, and stays correct.
    code_hint: |

  - action: prohibited
    description: >
      NO heuristic, NO policy engine, NO profile list, NO CLI subcommand, NO per-site configuration.
      D5 is a flag; the owner's sentence says configurable and disabled by default, which is not a
      request for an automatic decision. MUST NOT gate the context identity triple (`viewport`,
      `user_agent`, `locale`, `timezone_id`) — their DESCRIPTIONS are corrected, their BEHAVIOUR is
      untouched. MUST NOT check the asset when the flag is false. MUST NOT add a warning-level else as
      the enabled-path remedy: enabled plus missing is a hard failure, not a warning. MUST NOT introduce
      a new exception class. MUST NOT add a "warn and proceed" mode or any second switch. MUST NOT move
      the check into `__init__` or after `async_playwright().start()`. MUST NOT remove
      `create_stealth_page`'s existence guard entirely. MUST NOT touch B8's anchors — the `except
      Exception:` arm, its `exc_info=True`, its `from None`, or the `await playwright_instance.stop()`
      before the raise. MUST NOT touch `__aexit__`, the `# type: ignore[union-attr]`, or add a context
      release path (BRW-002 is rejected). MUST NOT edit `pyproject.toml`. MUST NOT rename
      `BrowserManager` or `create_stealth_page`: renaming a public API for a default flip is
      disproportionate and the names still describe the capability that exists when the flag is on.
      MUST NOT invent a missing-dependency message convention.
    code_hint: |

acceptance_criteria:
  - >
    A missing asset with the flag TRUE raises ExtractionError from __aenter__ AND
    async_playwright().start() is asserted NEVER CALLED (new tests, both halves) — the ordering proof
    is the gate
  - With the flag FALSE and the asset absent: no error, no warning, and no check (new test)
  - With the flag FALSE, the launch args omit the automation-suppression argument and add_init_script
    is not called; the page is still returned (new test)
  - With the flag TRUE, both gated components are applied (new test)
  - >
    With the flag FALSE, new_context is STILL called with the configured user_agent, locale,
    timezone_id and viewport (new test — pins S1h)
  - The raised exception's error_code is the new ErrorCode member, not EXTRACTION_ERROR (new test)
  - The message names the path, the broken-build-or-partial-deployment consequence, and the remedy;
    the log record carries the SAME text
  - Exactly ONE new ErrorCode StrEnum member and NO new exception class
  - stealth_enabled is bool, defaults to False, and appears in exactly THREE places (field description,
    .env.example, configuration guide); the .env.example value constructs against Settings
  - create_stealth_page's existence guard is not removed; __aexit__ is byte-identical
  - __aexit__'s six plan-08 B4 tests are green UNCHANGED, as is B8's re-scoped launch-failure case
  - pyproject.toml is byte-identical; B8's four anchors are untouched; no rename occurred
  - All eleven documentation claims and docstrings corrected; docs/STRUCT.md unchanged
  - >
    The COMMIT BODY carries the owner's D5 words verbatim with an English rendering, the four-component
    gated/ungated table, the placement decision with both rejected candidates, the reused
    check_ffmpeg_available message shape, the measured before/after, and — IN ITS FIRST PARAGRAPH —
    the behaviour-change warning that every existing user's default run loses stealth
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---

### B16

```yaml
id: plan10-b16-console-sink-encoding
title: Give the console sink an encoding-safe error handler
priority: low
depends_on: [B8]
DECIDED: D7 (Tech Lead) — option (A), ADOPTED HERE. No gate.

source_reference: .ai/plans/10-subplans/10-subprocess-browser-audit-fixes.md
source_section: B16 — Give the console sink an encoding-safe error handler
source_blocks: ["B16"]
source_findings: []

description: >
  `setup_logging` gives the console sink a bare `logging.StreamHandler()` with no `errors=` value, so
  the handler inherits whatever error handler `sys.stderr` carries. A structlog record containing
  characters that encoding cannot represent propagates out of `logging.StreamHandler.emit` as a
  `UnicodeEncodeError`, through `handleError` — whose own write of "--- Logging error ---" then fails
  again, because `handleError` catches only `OSError`. This is the mechanism that makes BRW-001 a
  RUNTIME-ERROR: `logger.error("browser_launch_failed", exc_info=True)` renders a Playwright traceback
  containing box-drawing characters.

  NO FINDING IN ANY PHASE OWNS IT. Phase 01's ENT-001/ENT-002 are sink-ROUTING findings and deferred
  encoding to phase 08; phase 08 never filed it; a corpus search for cp1251 finds it only as EVIDENCE
  inside ENT-001, ENT-002 and OUT-002. That absence of an owner is precisely why it survived two audits
  — and why adopting it is an audit-pipeline decision rather than a routing one. D7 makes it.

  MEASURED, and conditional by environment rather than by theory: with this machine's real default
  stderr (cp1251, errors="backslashreplace") the statement RETURNS NORMALLY. Re-wrapped as cp1251
  with errors="strict" it RAISES and ExtractionError is never constructed. With log_file set it
  RETURNS NORMALLY — the JSONRenderer ASCII-escapes the traceback, so the FileHandler writes only
  7-bit characters. A search of src/ for reconfigure, PYTHONIOENCODING, errors= and encode( returns
  nothing.

  D7'S FOUR REASONS — three hold, one does NOT, and the fourth is recorded as not borne out:
    (1) it is a small config.py change plus a test — HOLDS.
    (2) it is the mechanism behind BRW-001's HIGH reclassification — HOLDS.
    (3) it has no owning phase, which is why it survived 01 and 08 — HOLDS.
    (4) with D5 the browser path is now reached on ordinary runs, so the exposure is more common —
        DOES NOT HOLD. Verified: `Settings.cookie_source` defaults to `CookieSource.NONE`, so
        BrowserManager is NOT entered on an ordinary default run at all; it is reached only when
        VKDOWNLOADER_COOKIE_SOURCE=browser. D5 does not change that default — stealth is an axis
        ORTHOGONAL to whether the browser is used for cookie extraction, and turning stealth off does
        not stop the browser from launching. The decision stands on (1)-(3); the fourth rationale is
        recorded so no future reader cites it as a fact about the code.

  WHY THE REMEDY BELONGS IN config.py, NOT browser.py: the defect is in the SINK, not the call site.
  A StreamHandler constructed with no errors= inherits the stream's error handler, and a record that
  cannot be encoded propagates out of emit. Fixing it at the call site would be a per-callsite try,
  which is the anti-pattern plan 08 B4 named. That is why this stays a separate block from B8 and B15,
  both of which land in browser.py.

goals:
  - a record containing non-encodable characters does not raise out of the console sink
  - the record is ESCAPED, not suppressed or dropped
  - the log-file sink is unchanged
  - browser.py is not edited by this block
  - no PYTHONIOENCODING manipulation and no sys.stderr.reconfigure

files:
  - path: src/vkdownloader/config.py
    targets:
      - type: function
        name: setup_logging
    semantic_anchors:
      modify:
        - type: function_call
          value: "logging.StreamHandler()"
      read_only:
        - type: function_call
          value: "logging.FileHandler("

  - path: src/vkdownloader/cli.py
    targets:
      - type: function
        name: _run_command_preamble
    semantic_anchors:
      read_only:
        type: function
        name: _run_command_preamble

  - path: src/vkdownloader/infrastructure/browser.py
    targets:
      - type: method
        name: __aenter__
        owner: BrowserManager
    semantic_anchors:
      read_only:
        - type: except_clause
          value: "except Exception:"

  - path: tests/test_config.py
    targets:
      - type: function
        name: setup_logging
    semantic_anchors:
      insert_after:
        type: function
        name: setup_logging

changes:

  - action: modify
    description: >
      Construct the console `StreamHandler` with an encoding-safe `errors=` value so a non-encodable
      record is escaped rather than raised. The block's Planner chooses between setting the value on
      the constructed handler and supplying it at construction, and records which — that choice is the
      whole of the block's remaining fork. Do NOT touch the log-file branch: the measured behaviour
      confirms it does not raise, because the JSONRenderer ASCII-escapes. Do NOT reconfigure
      `sys.stderr` and do NOT set `PYTHONIOENCODING` — reconfiguration is a side effect on the user's
      process that this project has no precedent for and did not ask for, and the commit body must say
      why both were rejected.
    code_hint: |
      console_handler = logging.StreamHandler()
      console_handler.errors = "backslashreplace"   # or supply errors= at construction

  - action: add_test
    description: >
      Add two cases. (1) THE STRICT-STREAM CASE, which does not exist today: re-wrap `sys.stderr` as a
      STRICT-encoded stream, emit a record carrying non-encodable characters through the configured
      console sink, and assert NO exception escapes. This is the case that does not exist and the whole
      point of the block. (2) THE NEGATIVE CASE: the record is still emitted and still CONTAINS the
      information, escaped rather than dropped — a fix that suppresses the record is not a fix. MUST
      STAY GREEN UNCHANGED: every tests/test_config.py case, the six plan-08 B4 tests, and B8's and
      B15's browser.py cases.
    code_hint: |
      class _StrictStream(io.TextIOWrapper):
          def __init__(self, buf): super().__init__(buf, encoding="cp1251", errors="strict")

      # non-encodable characters reach the sink; nothing raises; the record still carries the text

  - action: prohibited
    description: >
      MUST NOT edit `browser.py` — no per-callsite try, no removal of `exc_info=True`, no touching of
      B8's arm or B15's flag or asset check. MUST NOT change `setup_logging`'s file branch. MUST NOT
      use `PYTHONIOENCODING` and MUST NOT call `sys.stderr.reconfigure(...)`. MUST NOT claim or close
      `BRW-001` — that is B8's, and only half (a) of it. No `Settings` field: `B11`'s
      `download_stall_timeout` and `B15`'s `stealth_enabled` are the plan's only two. MUST NOT cite
      D7's fourth rationale as a fact about the code — it is not borne out (§ description).
    code_hint: |

acceptance_criteria:
  - A strict-encoded stderr plus a non-encodable record produces NO exception (new test)
  - The record is still emitted and still contains the information, escaped (new test)
  - setup_logging's file branch is byte-identical
  - browser.py is byte-identical; no per-callsite try appears anywhere in the diff
  - No PYTHONIOENCODING and no sys.stderr.reconfigure in the diff
  - Every tests/test_config.py case and the six plan-08 B4 tests are green UNCHANGED
  - >
    The COMMIT BODY names D7 as the adoption authority, states that the defect had NO owning finding
    in any phase, and lists D7's four reasons WITH THE FOURTH MARKED AS NOT BORNE OUT BY THE CODE
    (cookie_source defaults to NONE; stealth and browser use are orthogonal)
  - pytest, ruff check, ruff format --check, mypy src and the mypy src tests delta all pass (§2.6)
  - git diff --cached --stat shows only this block's files (plan §2.5)
```

---
## §8 Verification strategy

### §8.1 The per-block gate — every block runs all four

No block is complete until all four of these pass, in this order, from the repository root.

| # | Command | Pass criterion |
|---|---|---|
| 1 | `uv run pytest tests -q` | exit 0; the passed count has **risen** by the block's new tests and no test has been deleted or skipped to get there. |
| 2 | `uv run ruff check src tests` | exit 0 · `All checks passed!` |
| 3 | `uv run ruff format --check src tests` | exit 0 · all files formatted |
| 4 | `uv run mypy src` | exit 0 · `Success: no issues found` |

**And, for any block that touches `tests/` — which is every block except `B9`:**

| 5 | `uv run mypy src tests` | **NOT a clean gate.** The suite is **79 errors in 8 files** before this plan and must be **the same 79 errors in the same 8 files** after, with **no error in any file the block edited**. A block that *reduces* the 79 must call that out; a block that *adds* one is a defect. §1.6. |

**Plus the block's own gate**, run by name:

```powershell
uv run pytest tests/test_hls_downloader.py -k "IterProcessLines" -q                        # B2
uv run pytest tests/test_hls_downloader.py -k "YtDlpSubprocessShutdown" -q                # B1, B4, B5, B11, B12, B14
uv run pytest tests/test_ffmpeg_utils.py -q                                              # B5, B12, B14
uv run pytest tests/test_hls_downloader.py -k "EchoYtdlpLine" -q                          # B6
uv run pytest tests/test_url_sanitizer.py -q                                             # B7, B14
uv run pytest tests/test_browser_infrastructure.py -q                                    # B8, B15
uv run pytest tests/test_hls_downloader.py -k "FfmpegAvailabilityCheck" -q               # B13
uv run pytest tests/test_downloader.py -k "PerformDownload" -q                           # B10 (D-12 series)
uv run pytest tests/test_cli.py -q                                                       # B10 (--method rejection)
uv run pytest tests/test_config.py -q                                                    # B16
uv run pytest tests/test_packaging.py -q                                                 # only if a file was added
```

**The gates `D2` retired.** Revision 1's list ran `TestTempArgfile` / `TestHLSDownloaderDownload` for
`B1` and `B10`, `ReadProgress` for `B3` and `B4`, and `D-12 cases 5-7` for `B1`. **Every one of those is
deleted with the transport.** The replacements are the yt-dlp drain trio (inside `TestEchoYtdlpLine` and
`TestYtDlpSubprocessShutdown`), `test_downloader.py -k PerformDownload` for the retained `D-12` cases, and
`test_cli.py` for the `--method` rejection proof.

**The full suite is the gate for `B2` and `B4`** — not the class-level runs. The drain tests a
task-wrapped or raced read breaks are not in the reader's own test class, and a class-level gate is
exactly what would let that regression through. **After `D2` the net is the yt-dlp trio plus
`TestIterProcessLines`' exactly-once assertion**; Revision 1 named six, and four are deleted with the
transport that exercised them.

**Rules for a block report.**

1. Quote the **exact output** of all four commands. "Tests pass" without output is not a report.
2. **The passed count must not decrease.** A drop means a test was deleted, renamed without
   replacement, or skipped. **The four `D-11` Windows-confinement skips must remain exactly four.**
3. **List every test file and test name you edited**, with one line on why the edit was required by a
   behaviour change rather than by convenience. **Only the re-scopes named in §2.6 are authorised:**
   `B1` (one), `B3` (one), `B8` (one), `B10` (one, plus option-dependent removals),
   `B13` (one, conditionally).
4. **Confirm no network was contacted.** `tests/test_packaging.py` is the only test that may, and it
   skips off-CI.
5. **Confirm the block's negative acceptance criteria** — the "byte-identical", "MUST NOT" and "no new
   file" items — with a `git diff --stat` on the named paths, not with an assurance.
6. **Record every deferred decision the block's Planner resolved**, with the option rejected and why.
7. **`git diff --cached --stat` before committing** (§2.5's landing rule). Every staged path belongs
   to this block. **Never `git add -A`, never `git add .`, never `git commit -a`.**
8. **Qualify every `VAL-` id** as `phase05/VAL-NNN` in the report and in the commit message.
9. **A block that closes a wedge must state which routes it closed** — not which routes it believes
   another block closed. §5.8 item 6.
10. **`mypy src tests`** must be run and reported by every block that touches `tests/` (§1.6).

### §8.2 The end-of-plan gate — after `B14`, or after the last block that runs

| # | Gate | Pass criterion |
|---|---|---|
| 1 | All four baseline commands, in order | exit 0. Expected floor: **>= 772 passed, 4 skipped** — the count may only rise. |
| 2 | `ruff check` · `ruff format --check` · `mypy src` | exit 0, all three. |
| 3 | `mypy src tests` | **79 errors in 8 files or fewer.** Never more. |
| 4 | Every re-scoped test group, re-run individually | `B8`'s widened `match` (with the `ExtractionError` assertion intact), `B10`'s `--method` rejection proof, `B13`'s cache test if re-scoped — each asserts its **new** contract, not a weakened one. **Read the diff, not the exit code.** `B1`'s re-scoped test is `B10`'s to replace, since `TestTempArgfile` goes with the transport; `B3`'s tail assertion is **gone with `B3`**. |
| 5 | Every "must stay green unchanged" group, re-run | §2.6's rows: `TestCancelSubprocess` (4), `TestEchoYtdlpLine`'s four `echo=False` cases, `TestStripAuthParams`, `TestReadProgress`'s four cases, plan 08's six `__aexit__` tests, the four `D-11` skips. Green **and unedited**. |
| 6 | The six drain tests, re-run by name | Green and unedited. This is the regression net for `B2`. |
| 7 | **No new file under `src/` or `tests/` outside `EXPECTED_SDIST_ENTRIES`** | `tests/test_packaging.py` green. If `B12` option (C) added a module, the frozenset was edited in the same change with the reason stated. |
| 8 | **No new `Settings` field anywhere** | Grep `config.py` for a diff. It must be empty. |
| 9 | **Read-only paths unchanged** | `.ai/audit/**` byte-identical (`B9`); `docs/11-guides/configuration.md`'s `download_timeout` row unchanged (`B11`); `pyproject.toml`'s `artifacts` declaration unchanged (`B15`); `docs/STRUCT.md` unchanged (phase 09's); `.kilo/rules/**` and `.kilo/agents/**` unchanged (all blocks); the validated artifacts unchanged (every block); the yt-dlp no-application-level-timeout docstring unchanged (`B1`, `B2`, `B3`, `B4`, `B5`, `B6`, `B10`); `read_progress`'s `shutdown_event` parameter unchanged (`B2`, `B3`, `B4`); signal-handler registration placement unchanged (all blocks). |
| 10 | **No block implemented a withdrawn recommendation** | Grep every report for: a permanent-leak claim; `__cause__`/`__context__` cleared rather than carried; the `N/A` guard replaced; `TRN-013`'s configuration knob resurrected; the unconditional yt-dlp-merge-child scenario; "three surfacings"; `ModuleNotFoundError`; `TestDownloadWithFFmpeg` / `TestFormatArgfile` / `TestCheckFFmpegAvailable` as class names; the unconditional "this plan repairs `TRN-001`" claim under `B10` option (D). **All twelve must be absent.** |
| 11 | **Acronym hygiene** | No unqualified `VAL-` id in any commit message, block report or task id. |
| 12 | **`SEC-004` re-adjudication recorded** | If `B10` option (A) or (C) landed, some report states that `SEC-004` must be re-derived, not merely cross-referenced. `B9`'s record is in the tree. |
| 13 | **The decision record is honest** | Every block that was `AWAITING DECISION` names the option its commit implements, and it is the option the Product Owner answered. |

### §8.3 Oracles for the documentation-only and conditional blocks

`B7` and `B9` have no behavioural oracle, so the **independent read is the gate**:

| Block | What the Validator proves instead |
|---|---|
| **B7** | `git diff -- src/vkdownloader/utils/url_sanitizer.py` touches **only** docstrings and comments; the function body is byte-identical; the new test asserts the boundary the docstring now describes; `TestStripAuthParams` and the four existing `TestSanitizeTextForLog` cases are unedited and green. |
| **B9** | `git diff --exit-code -- .ai/audit` **and** `git status --short -- .ai/audit` are both empty; `git diff --exit-code -- src tests pyproject.toml` is empty; exactly one new file under `.ai/decisions/`; every `VAL-` id is qualified; and the record contains **no verdict** on any `SEC-` row — grep it for "should be", "must be replaced", and any severity word applied to a phase-06 finding. |
| **B16** | — | — | **YES** | **YES** | LOW-MEDIUM, unowned | *Planner:* **retained.** `D7` settles adoption, but not construction — whether the encoding-safe value is set on the handler or supplied at construction is a small real fork, and the report must state why `PYTHONIOENCODING` and `sys.stderr.reconfigure` were rejected. *Validator:* the block still has **no finding behind it**, so its job is to confirm the adoption is the Tech Lead's decision and that no per-callsite `try` was written instead. `D7`'s fourth rationale is **not borne out by the code** and the Validator must not let it into the commit body as fact. |

### §8.4 Per-finding verification trace

Every accepted finding, mapped to its disposition, the block that carries it, and the test that
proves it. **Rows marked MOOT or DISPOSED have no pending test by design** — a finding whose subject no
longer exists must not carry a live obligation, and a finding quietly left pending after its subject is
removed is a defect in the plan.

| Finding | Disposition | Block | Proving test / gate | Notes |
|---|---|---|---|---|
| `TRN-001` | **DISPOSED by `D2`** | **B10** | The deletion's own tests: `--method ffmpeg` now produces a non-zero usage exit; the enumerated deletion list re-derived by grep with zero residual references | `D2` **is** the answer to this finding. It is not left open and not carried forward. The commit body must state that phase 06's `SEC-004` must be re-adjudicated because it now describes a transport that no longer exists. |
| `TRN-002` | **HALF MOOT, half carried** | **B1** | Re-scoped: a destroy that raises `OSError` leaves the file behind and the call returns normally on all three paths (new); the negative case (cleanup still happens); the reaping-ordering assertion | The orphan half is closed by `D2`. The outcome half survives at `_download_with_ytdlp`'s cookie `finally:`, a different statement in a different module. Priority re-graded HIGH → MEDIUM with the reason in the commit body. |
| `TRN-003` | **CARRIED, decided** | **B12** *(decided by `D1`)* | The descendant case (new): a stand-in that spawns its own child, probed after the ladder; the platform-asymmetry case asserting the grandchild **survives** on Windows | Both three spawn sites; the fourth was deleted by `B10`. The Windows residual is asserted honestly, not glossed. |
| `TRN-004` | **CARRIED** | **B2** | The oversized-line case (new); the stop-during-oversized-read case (new, asserting exactly-once); the `watch_task` cleanup assertion | **Full suite is the gate.** After `D2` the net is `TestIterProcessLines` plus the yt-dlp trio; four of Revision 1's six are deleted with the transport that exercised them. |
| `TRN-005` | **MOOT by `D2`** | ~~**B3**~~ — **DELETED** | **None, by design.** | `read_progress` and its `progress=end` marker are deleted with the transport, and `_build_ffmpeg_concat_command` passes **no** `-progress` — so no reachable code can produce the defect. `B3`'s spec carries the warning that the finding **returns** if the transport is reinstated. |
| `TRN-006` | **HALF MOOT, half carried** | **B4** | The swallowed-failure-now-reported case (new); the discrimination case — a normal completion produces **no** record (new); the cancelled-and-settled case (new) | The parse half is deleted with `_PROGRESS_KEY_HANDLERS`. Revision 1's `test_read_progress_handles_na_values` regression net is **discharged by deletion**, not weakened. |
| `TRN-007` | **CARRIED, decided** | **B11** *(decided by `D3`)* | The emits-then-stalls case (new): returns within the bound **and** reaps the child; **the liveness case** (new): a child that keeps emitting is never killed; the cancellation arm (new); the setting's construction and bounds (new) | One site after `D2`. `NET-007` is **preserved** — the liveness test is the proof. |
| `TRN-008` | **CARRIED, settled** | **B13** *(decided by `D6`)* | Arm (b) (new — **untested today** and now the sharpest arm); arm (d) (new); arm (c) (new); the probe's answer USED at its single call site; and **the exit code provably unchanged** | Arm (a) is **DELETED** with the transport — the obligation is discharged, not weakened. `D6` forbids any branch that raises or changes an exit code, so the "does not change the exit code" half is asserted, not assumed. `test_check_ffmpeg_available_returns_bool` green unchanged; the caches test green unchanged unless explicitly re-scoped. |
| `TRN-009` *(claim half)* | **CARRIED, re-scoped** | **B7** | The new capability-boundary case (URL redacted, temp path unchanged) | Two sites, not three: the `download_with_ffmpeg` `SEC-002:` comment is deleted by `B10`. No behaviour change; `TestStripAuthParams` green unchanged. |
| `TRN-009` *(capability half)* | **CARRIED, scoped** | **B14** *(decided by `Q5`)* | Both merge sinks carry transformed text (new); the transform-then-truncate ordering proof (new); the bare-path boundary assertion (new) | **Two sinks, not three.** The matcher and the console echo are phase 06's and are asserted **byte-identical**. The block is no longer gated. |
| `TRN-010` | **MOOT by `D2`** | **None — cross-reference** | **None, by design.** | An asymmetry *between two transports* cannot survive one transport's deletion. The residue — yt-dlp still passes `--cookies <path>` and the media URL in argv, and `sanitize_text_for_log` still cannot match a path — is **phase 06's `SEC-006`**, and `D1` makes the exposure moot for a single-user desktop. Recorded in `B9`'s decision record. |
| `TRN-011` | **CARRIED, unchanged** | **B6** | The far-over-the-bound case (new); the `echo=False` case (new); the usable-failure-message case (new) | Unaffected by `D1`–`D4`. The four `test_ytdlp_echo_false_*` cases green **unchanged with no edits**. |
| `TRN-012` | **CARRIED, re-scoped** | **B5** | The composition case (new: two calls, zero records) **and** the mandatory negative case (new: still running ⇒ the record is written) | **Two sites, not six.** `TestCancelSubprocess` green unchanged in full. |
| `BRW-001` *(half a)* | **CARRIED, unchanged** | **B8** | Re-scoped `test_browser_manager_launch_failure_raises_extraction_error` (widened `match`, `ExtractionError` assertion **intact**) + the cause-content, suppression and uninformative cases (all new) | `from None` kept and asserted. Unaffected by `D1`–`D4`, except that `D4` puts a second hardened path in the same method (`C15`). |
| `BRW-003` | **RE-SCOPED by `D5`** | **B15** | The **flag default** (new); stealth-off/asset-present (new); **stealth-off/asset-absent — no error, no warning, no check** (new); stealth-on/asset-present (new); stealth-on/asset-missing (new); **the ordering proof — the gate** (new); `ErrorCode` (new); **component 3 is not gated** (new) | Two halves now diverge: with stealth **off** the asset is not consulted and **the finding's original form dissolves**; with stealth **explicitly on**, absence is a hard failure **before the driver starts**. The ordering proof is the gate — a check sitting after the launch would satisfy every other assertion while achieving nothing. The `component 3 is not gated` test pins `S1h` against a later consistency argument. |
| `phase05/VAL-501` | **CARRIED, sharpened** | **B9** | *(no test — prose)* Validator gate: `git diff --exit-code -- .ai/audit` empty; the record names phase 06 as the owner and contains no verdict on `SEC-004` | Now **doubly** wrong: the cells assert a concealment that never worked **and** they describe a transport that no longer exists. The correction is **not performed** — §1.5. |
| `phase05/VAL-502` | **BOTH CHAINS CLOSED** | **B9** + §9 | *(enforced as a decision record and a gate, not a test)* Chain 2 = `D2`, quoted verbatim in §9. Chain 1 = **evaporated** with the argfile, not satisfied by ordering | Neither chain is a test's subject; each is a recorded decision, and both are traceable. `E1` in §4.1 is marked **retired**. |
| *(the console-encoding gap)* | **CARRIED, adopted** | **B16** *(decided by `D7`)* | The strict-stream case (new) and the record-still-emitted case (new) | **No longer conditional and no longer gated.** `D7` adopts it here as option (A). The block still has **no finding behind it**, which is why its Validator's job includes confirming the adoption is the Tech Lead's decision — and why `D7`'s fourth rationale is recorded as **not borne out by the code** rather than repeated as fact. |

**Findings whose verification is a negative assertion** (no test can see them — the Validator's read
is the gate): `phase05/VAL-501` (`B9`), `TRN-010`'s cross-reference, and every block's byte-identical /
`MUST NOT` / no-new-file criterion. Each is written as an explicit acceptance criterion for that reason.

**Findings with no pending verification at all** (their subject is gone): `TRN-005` (moot by `D2`) and
`TRN-010` (moot by `D2`). Neither may be reported as pending, and `B3`'s deleted spec plus `B9`'s
record are where a reader looks to learn why.

## §9 Decisions taken

**This section was "decisions escalated" in Revision 1, then `D1`–`D4` recorded in Revision 2. It now
records seven binding decisions.** Six questions were put to the Product Owner; **four are answered and
binding** (`D1`–`D5`, of which `D4` is superseded by `D5`), two are **Tech Lead decisions** that close
the last open questions (`D6` closes `Q4`, `D7` closes `Q6`), and **one ownership question** (`Q5`) is
closed by a split already decided.

**Dates.** `D1`–`D5`: **2026-10-03** (Product Owner). `D6`, `D7`: **2026-10-03** (Tech Lead).

**ZERO GATES REMAIN.** All fifteen blocks are executable without a further decision. There is no open
question in this plan.

| | Decision | Owner | Supersedes / closes | Blocks changed |
|---|---|---|---|---|
| `D1` | single-user desktop deployment | Product Owner | — | `B12`, `B14`, `B9` |
| `D2` | `--method ffmpeg` **deleted** | Product Owner | — | **inverts `B10`**; `B1`, `B2`, **`B3` deleted**, `B4`, `B5`, `B7`, `B9`, `B11`, `B12`, `B13` re-scoped |
| `D3` | stall bound, default 300 s, configurable, **inactivity** | Product Owner | — | `B11` |
| `D4` | stealth is a hard requirement | Product Owner | **SUPERSEDED BY `D5`** | `B15`, `B8`, `B16` |
| `D5` | stealth is **opt-in, default OFF** | Product Owner | **supersedes `D4`** | **`B15` re-scoped**, `B8` (ordering only), new edge `E20` |
| `D6` | `TRN-008`: better degradation, **no exit-code change** | Tech Lead | **closes `Q4`** | `B13` |
| `D7` | console-encoding defect **adopted here** | Tech Lead | **closes `Q6`** | `B16` |

---

### D1 — Deployment: single-user desktop only

> **The owner's decision, in their framing:** no shared servers, no Docker, no CI, no multi-user host.

**Consequence, stated plainly: command-line token exposure is moot.** A user running a desktop tool can
already read their own process list. This **retires the entire `SEC-004` exposure argument as a reason to
prefer indirection** — the argument that a signed m3u8 URL or a cookie path in argv is a security
problem. For this deployment it is not.

- **Blocks changed:** `B12` (`TRN-003`) — decided. The remedy was already the minimum platform keyword;
  `D1` changes the *cost/benefit*, not the remedy, and supplies the justification for accepting the
  Windows residual. A surviving orphan now holds a file open **on the user's own desktop**, where the
  user can see it, and the direct child — which holds the credential material — is killed either way.
  `B14` — `D1` recorded; it changes nothing in the block, which is justified on **correctness** grounds
  (a log file persists; a process listing is not a log) rather than exposure grounds. `B9` — recorded as
  the reason the `SEC-004` argument no longer distinguishes the transports.
- **Findings mooted:** **none directly.** `D1` retires a *reason*, not a defect. The nearest is
  `TRN-010`, whose exposure half becomes moot — but `TRN-010` was already moot by `D2` for the stronger
  reason that one transport remains.
- **What it does NOT do:** it does not make `TRN-001` moot — that is `D2`. It does not close `TRN-008`,
  whose worst arm is a missing binary surfacing three different ways, none of which is an exposure
  argument.

---

### D2 — `--method ffmpeg` is DELETED, not repaired

> **The owner's words, verbatim:** *"No you can delete it for now. If it will be needed we will add it in
> future."*

**This inverts `B10`.** It is no longer "make the transport work"; it is **remove the transport**, and
with it every symbol that exists only to serve it. It is a deletion, so the rule for it is subtraction:
no deprecation shim, no feature flag, no tombstone enum member, no alias, no "coming back soon" note.
`DownloadMethod.FFMPEG` is **removed outright** — a dead enum member violates project rule 10.

**What a script passing `--method ffmpeg` now receives.** Typer validates the choice against the enum
before `perform_download` is reached, so it gets the parser's own invalid-choice error and exit `2`,
already the documented usage-error code. The owner authorised a breaking change; `B10` records it as
one.

**`--method auto` after the deletion, established against the code.** `DownloadMethod.AUTO` and
`DownloadMethod.YTDLP` now resolve to the **same transport**, `download_with_ytdlp_with_resume_fallback`.
The single difference is that `AUTO` skips `_resolve_cookies` when
`settings.cookie_source == CookieSource.NONE`, while `YTDLP` always resolves. So precisely:

> **`--method auto` means: resolve cookies according to `cookie_source` — skipping browser resolution
> when it is `none` — then download via yt-dlp with segment-level resume as the fallback.**

`AUTO` **stays**: removing it would change the CLI's default value, a larger breaking change than was
authorised, and it is a live member with load-bearing cookie semantics rather than a tombstone. But its
arm comment — *"Auto: try yt-dlp first (more reliable), segment download for resume"* — is now a
**false two-transport sentence**, and correcting it is a named obligation inside `B10`.

- **Findings disposed:** **`TRN-001`** — disposed. Its subject is the `@argfile` invocation and the
  `--method ffmpeg` transport; both are deleted. `D2` **is** the answer.
- **Findings moot:** **`TRN-005`** — fully moot (`read_progress` deleted; the merge transport never
  emitted `-progress`). **`TRN-010`** — moot (an asymmetry between two transports cannot survive one
  transport's deletion; residue cross-referenced to phase 06's `SEC-006` and moot for this deployment by
  `D1`). **`TRN-006`'s parse half** and **`TRN-002`'s orphan half** — moot. **`TRN-009`'s claim half's
  third site** and **`TRN-008`'s arm (a)** — moot. **`phase05/VAL-502` chain 1** — evaporates.
- **Findings partially carried:** `TRN-002` (outcome half only), `TRN-006` (sink half only), `TRN-009`
  claim (two sites), `TRN-008` (three arms), `TRN-012` (two sites), `TRN-007` (one site).
- **The chain `D2` closed:** **`phase05/VAL-502` chain 2** — "the shape of the `TRN-001` fix is a
  decision phase 06's `SEC-004` already owns" — **answered**. **Chain 1** — "`TRN-001` and `TRN-002` must
  land together" — **evaporated**: the coupling existed because repairing one made the other worse, and
  there is nothing left to couple. Discharged by the deletion itself, not by ordering; `E1` is marked
  **retired**.
- **What phase 06 now owes:** `phase05/VAL-501` becomes **more** clearly stale, not less — `SEC-004`
  asserts a concealment that never worked **and** now describes a transport that does not exist. Its
  R5(d) `MET (argfile)` cells and its subject line are both wrong. `.ai/audit/**` is read-only here, so
  `B9` **records** the correction and phase 06 needs a separate pass.

---

### D3 — The stall bound: default 300 s, configurable, and an inactivity bound

> **The owner's decision:** the stall bound exists, defaults to 300 seconds, and is configurable. It
> confirms the `download_stall_timeout` setting, and it is an **inactivity** bound — no output for N
> seconds.

**This corrects Revision 1, and the correction is in the finding's favour.** Revision 1 assumed the bound
would overturn `NET-007`'s withdrawn whole-operation budget and that
`_download_with_ytdlp`'s *"no application-level download timeout is imposed, avoiding premature kill of
legitimate long downloads"* sentence would have to be **reversed**, and it gated the block on `Q2` on
that basis. **Both were wrong.** An inactivity bound is not a whole-operation budget, so **`NET-007`'s
withdrawal stands** and **the docstring sentence stays true** — a download that keeps producing output
is never killed, however long it runs. `B11` **amends** it to name the setting and its inactivity
semantics.

**The setting:** `download_stall_timeout`, default `300.0`, `ge=30`/`le=3600` mirroring
`download_timeout`, type `float`, homed in `Settings` beside `download_timeout`, written in **three**
places (field description, `.env.example`, configuration guide — plan 07's `C12` owns the existing row,
so `B11` adds beside it and edits nothing).

- **Blocks changed:** `B11` — decided, no longer gated.
- **Findings mooted:** **none.** **Decided:** `TRN-007`, at **one** site after `D2`.
- **Shape constraint:** the bound copies `_await_ffmpeg_with_timeout` — a mandatory `timeout: float`
  with **no default**, and an `except (TimeoutError, asyncio.CancelledError)` arm that re-enters the
  termination ladder and **re-raises**. A bare `asyncio.wait_for` around `process.wait()` is
  prohibited; it would leave the child unreaped. And "inactivity" has no meaning unless something
  measures liveness, so the block must state what counts as liveness.

---

### D4 — Stealth extraction is a hard requirement — **SUPERSEDED BY `D5`**

> **The owner's words, verbatim:** *"bypassing detection is required for the tool to work, we need this as
> downloading from the system with high bot protection."*

**Recorded because it is the decision `D5` replaces, and because the reason it was given is still live.**
`D4` made `BRW-003` an unconditional hard failure verified before a browser launches. `D5` supersedes
the *remedy* and keeps `D4`'s **placement analysis, exception choice and message convention** — only the
*condition* changes from "always" to "when explicitly enabled".

`D4`'s placement conclusion is confirmed by `D5`'s and reused: `__aenter__`, before
`async_playwright().start()`. `B8` is affected only in ordering (`S1i`, `E10`), not in content.

- **Findings mooted:** none. **Findings escalated:** `BRW-003` — superseded by `D5`, which re-scopes it
  again and **dissolves its original form** for the default case.

---

### D5 — Stealth is an opt-in setting, default OFF

> **The owner's words, verbatim:** *"я бы хотел, чтобы скачивающий сам решал нужен stealth или нет. Т.е.
> это должно быть configurable по умолчанию отключено."*
> **In English:** *"I would like the downloader itself to decide whether stealth is needed. That is, it
> should be configurable, disabled by default."*

**A reader six months out must be able to see this and know it was deliberate.** Stealth was **always
on**: the automation-suppression launch argument and the `stealth.min.js` injection were unconditional.
`D5` makes the posture the user's choice, off by default. **That removes stealth from every existing
user's default run** — and it interacts with `D4`'s own reason: on a bot-protected origin, the new
default is the setting least likely to work. Both decisions are the owner's; `D5` supersedes `D4`; the
tension is **recorded, not resolved**, because resolving it would re-open `D5`. §5.1c, §5.5 and §10 all
carry it.

**How the plan reads the Russian.** The phrase *"чтобы скачивающий сам решал"* can be misread as a
request for an automatic decision. **It is not**, and the same sentence says so: *"это должно быть
configurable по умолчанию отключено"* — it should be **configurable** and **disabled by default**.
`B15`'s prohibition 1 forbids a heuristic, a policy engine, a profile list, a CLI subcommand and
per-site configuration, and says why.

- **Blocks changed:** **`B15` re-scoped** — the block becomes a `Settings` field, a two-component gate,
  and a *conditional* hard failure. `B8` — ordering only (`S1i`, `E10`). New edge `E20`, conflict
  `C19`. `B11` is now the **first** settings-field block and `B15` the second, which is why `E20` orders
  them.
- **Findings mooted:** **none in full.** `BRW-003`'s **original form dissolves** for the default case —
  with stealth off, nothing consults the asset, so "the asset's absence is silent at every log level" has
  no subject. What survives is the **residual**: when stealth is **explicitly enabled**, absence must be
  a hard failure.
- **The behaviour change, stated once more here because it is the plan's second largest:** every
  existing user's default run loses stealth. `B15`'s commit body must carry it in its **first**
  paragraph.

---

### D6 — `TRN-008` / `B13`: better degradation, not hard failure — **closes `Q4`**

> **The Tech Lead's decision, option (B).** The reason: `D2` removed the strongest argument for a hard
> failure — with the explicit ffmpeg transport deleted there is no longer a user-selected transport to
> violate — and a hard failure would break **every HLS download** on a muxer-less machine for no user
> benefit.

**Four requirements and one prohibition**, all carried in `B13`'s block and task spec:

1. Emit **one** actionable warning naming the install step, following the `check_ffmpeg_available`
   convention — `logger.warning(<event>, hint=(<what is missing>; <what will fail>))`.
2. **Use the probe's answer at its single call site** instead of discarding it. **This is the finding's
   structural core** — the bare expression statement becomes a bound value the warning path consults.
3. Stop `except (ExtractionError, OSError)` reporting a missing muxer as `failed_to_refresh_token` —
   **mandatory under any option**, and in scope.
4. Give the merge path a product record, so its escaping `FileNotFoundError` stops being the only
   surfacing that produces nothing.
5. **✗ No exit-code change.** No branch on the probe's answer may raise, return early, or alter an exit
   code.

- **Blocks changed:** `B13` — decided, ungated. Its **three** surviving arms (of four) are re-derived
  against the post-deletion tree in the block.
- **Findings mooted:** **none.** **Decided:** `TRN-008`.
- **Closes:** `Q4`. `Q4` is removed from the open-questions set; §3's preamble, `B13`'s heading, the
  §6 agent row and §8.4's trace all record the decision rather than the question.

---

### D7 — The console-encoding defect is adopted here — **closes `Q6`**

> **The Tech Lead's decision, option (A).** Adopt it in this plan.

**The four reasons, recorded — and the fourth is checked against the code.**

| Reason `D7` gave | Holds? |
|---|---|
| It is a small `config.py` change plus a test | **Yes.** One handler construction, one attribute, two test cases. |
| It is the mechanism behind `BRW-001`'s HIGH reclassification | **Yes.** `BRW-001`'s unconditional half is `logger.error(..., exc_info=True)` raising `UnicodeEncodeError` where an `ExtractionError` should be constructed. |
| It has no owning phase, which is why it survived phases 01 and 08 | **Yes** — and that absence of an owner is precisely why the adoption is an audit-pipeline decision rather than a routing one. |
| With `D5` the browser path is now reached on ordinary runs, so the exposure is more common | **NO — recorded rather than repeated.** Verified: `Settings.cookie_source` defaults to **`CookieSource.NONE`**, so `BrowserManager` is **not** entered on an ordinary default run at all; it is reached only when `VKDOWNLOADER_COOKIE_SOURCE=browser`. `D5` does not change that default — stealth is an axis **orthogonal** to whether the browser is used for cookie extraction, and turning stealth off does not stop the browser from launching. The decision stands on the first three; the fourth is recorded so no future reader cites it as a fact about the code. |

- **Blocks changed:** `B16` — ungated. It remains the only block in the plan with **no finding behind
  it**, which is why its Validator's job still includes confirming the adoption is the Tech Lead's
  decision — and why `D7`'s fourth rationale must not appear in the commit body as fact.
- **Findings mooted:** **none** — it never had one. **Adopted:** the console-encoding gap.
- **Closes:** `Q6`.

---

### `Q5` — closed by the split already taken

Phase 06's R5(d) table records `TRN-009`'s two halves under phase-06 ids, so `TRN-009` is a
**duplicate** of `SEC-005` + `SEC-006`, not a novel finding. The split is by sink, and it **loses no
coverage** because the two sinks this plan takes are in **neither** phase's set:

| Sink | Owner |
|---|---|
| `_merge_batch_segments`'s `batch_merge_failed` | **This plan** — unowned |
| `_perform_final_merge`'s `final_merge_failed` | **This plan** — unowned |
| `_echo_ytdlp_line`'s `sys.stderr.write` | **Phase 06** — its `SEC-005` |
| The path-matching capability in `_URL_REGEX` | **Phase 06** — its `SEC-006` |

**Consequence:** `B14` shrinks to "apply the transform at two sinks, transform-then-truncate" and is
**ungated**.

---

## §10 Disclosures

- **Nothing in `src/`, `tests/`, `pyproject.toml`, `.ai/audit/**` or the existing `.ai/plans/*.md` was
  modified in producing or revising this plan.** This file is the only write.
- **REVISION 3** applies the Product Owner's **`D5`** and the Tech Lead's **`D6`** and **`D7`**
  (2026-10-03). **Block count unchanged at 15**; `B3` remains deleted. Re-scoped: `B15` (gate + setting +
  conditional failure), `B13` (decided), `B16` (ungated). `B8` affected only in ordering (`S1i`). New:
  edge `E20`, conflict `C19`, splits `S1h`/`S1i`, risk section `§5.1c`. **Gates 2 → 0.**
- **The baseline was re-run against the live tree after this revision, not copied:**
  `uv run pytest tests -q` -> **772 passed, 4 skipped, 1 warning**; `uv run ruff check src` ->
  `All checks passed!`; `uv run ruff format --check src` -> `31 files already formatted`;
  `uv run mypy src` -> `Success: no issues found in 31 source files`; `uv run mypy src tests` ->
  **Found 79 errors in 8 files**. Unchanged, because this plan modifies no code.
- **`mypy src tests` is red before and after.** Any block that touches `tests/` **may not** write
  "mypy clean" as a gate; it writes "the same 79 errors in the same 8 files, with none in any file this
  block edited". §1.6 and §8.1.
- **THE SECOND LARGEST BEHAVIOUR CHANGE IN THIS PLAN, disclosed plainly: `D5` removes stealth from every
  existing user's default run.** Stealth was always on. `stealth_enabled` defaults to `False`, and a user
  on a bot-protected origin must now set `VKDOWNLOADER_STEALTH_ENABLED=true`. This is what the owner
  asked for. It is also in tension with `D4`'s own stated reason — high bot protection — and that
  tension is **recorded, not resolved**, because resolving it would re-open a decision the owner has made.
  §5.1c, §5.5, and `B15`'s commit body carry it; the commit body must lead with it.
- **Eleven documentation claims and three in-code docstrings are corrected by `B15`**, because `D5` makes
  them false — most sharply `docs/01-tools/vkdownloader-overview.md`'s *"Secure-by-default browser
  stealth configuration"*, which `D5` reverses outright. `docs/STRUCT.md`'s entry is a file listing and
  stays correct.
- **Two judgement calls this plan made under `D5`, recorded so a later reader can overrule them with the
  reasoning in view.** (1) The **context identity triple is not gated**: `user_agent` is request identity
  shared by four consumers, `viewport` is a hard-coded literal, and `locale`/`timezone` are correctness
  rather than evasion — their *descriptions* are corrected instead. `S1h`. (2) **`BrowserManager` and
  `create_stealth_page` are not renamed**, because renaming a public API for a default flip is
  disproportionate and the names still describe the capability that exists when the flag is on.
- **One stated rationale was checked against the code and found NOT to hold**, and is recorded as such
  rather than repeated: `D7`'s fourth reason ("with `D5` the browser path is now reached on ordinary
  runs"). `cookie_source` defaults to `NONE`; stealth and browser use are orthogonal. `B16`'s commit
  body must not cite it as fact.
- **The six corrections to the code context stand** (§1.7): `TRN-008`'s arm **(c)** is misidentified in
  both the code context and the artifact — there is **no `ModuleNotFoundError` arm**; the live arm logs
  `ytdlp_not_found`. The api-reference doc site is `docs/01-tools/`, not `docs/99-reference/`. There are
  **seven** doc sites, not six. Three test class names in the §13 inventory **do not exist**. Two listed
  "pins" **do not exist**, which is why `TRN-008`'s arm (a) was **unpinned**.
- **Two unplanned observations of this plan's own re-derivation, recorded because they change work:**
  (1) `D2` deletes the only producer of ffmpeg's `-progress` stream, which is what makes `TRN-005` moot and
  `TRN-006`'s parse half moot; a reader who reinstates the transport must be told, in the commit that
  does it, that `TRN-005` returns with it and needs re-filing (the warning is in `B3`'s deleted spec).
  (2) `docs/99-reference/cli-reference-clean.md` is the same document as `cli-reference.md` with **every
  non-ASCII character mojibake'd**, 283 lines against the original's 284, linked from exactly one
  research document, with **no `mkdocs.yml`**. It is a documentation-hygiene defect owned by no phase;
  `B10` corrects its `--method` rows and leaves its encoding alone.
- **`tmp/` is untracked and not gitignored**, and `.ai/` carries eight tracked deletions and one
  modified file. All pre-existing; §2.5 forbids absorbing any of it.
- **No decisions remain refused.** `Q4` and `Q6` are closed by `D6` and `D7`; `Q5` is closed by the
  split. Every block in this plan is executable as written.
- **The `B10` commit-message gap is recorded, not rewritten.** Commit `d572d96`'s subject
  `TRN-001: Remove FFMPEG download transport (DownloadMethod.FFMPEG)` does **not** follow the
  repository's `type(scope): description` convention used by the commits before and after it.
  Its body lists changes made but omits three statements the plan required: the **preservation
  list**, the **`--method auto` semantics statement**, and the **`SEC-004` re-adjudication
  statement**. History is not rewritten; the substance is recorded in full in
  `.ai/decisions/05-subprocess-browser-decision-record.md` §6 so the repository's record is
  complete. Phase 06 still owes the `SEC-004` correction, which lives under `.ai/audit/**`
  (read-only here) and must be performed in a separate pass.
