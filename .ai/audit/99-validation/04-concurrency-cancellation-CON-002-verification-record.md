# CON-002 — Verification Record

**Finding recorded:** `CON-002` — *"The shipped condition that reaches the per-part transfer from
inside the outer claim is not executed"*.
**Filed in:** `.ai/audit/04-concurrency-cancellation/findings.md` (source report) and
`.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` (validated artifact).
**Written by:** block `B10` of `.ai/plans/09-concurrency-cancellation-audit-fixes-completion.md`,
against tree state `HEAD = 3c25dda`.
**Kind:** a verification record. This file is **not** a validation artifact, **not** a finding, and
**not** a severity assignment.

**Anchoring rule for this file.** Every code reference below is **semantic** — a module, a function,
a class, a field. **No line number appears in this file, deliberately**: the register this record
discusses is itself stale in exactly that respect (section 5), and a durable record must not
reintroduce the defect it documents.

---

## What this record is, and what it is not

`CON-002` **remains filed**, **remains marked `UNVERIFIED`**, and **continues to carry no severity**.
Nothing here changes that, and nothing here should be read as a step towards changing it. Its
severity cell in the source report reads `*none — not executed*` and **remains exactly as filed**.

This record answers two questions only: what was *structurally observed* about the production
condition, and what was *not* executed. It assigns no severity, reaches no verdict on the condition,
and does not delete, merge, reclassify, close or retire the finding.

---

## 1. The structural fact, re-derived against the live code

**1.1 — The per-video permit is taken exactly once, around the whole ladder.**
`src/vkdownloader/services/downloader.py`, function `perform_download`: a single
`async with` over `_semaphore_context(semaphore)` wraps the entire method-dispatch ladder, so every
branch of that ladder runs inside one acquisition of the per-video permit. The comment above it
states the intent: one permit per video, acquired exactly once at that point, and the segment layer
does not re-acquire from it. In single-download mode `_semaphore_context` returns a no-op context
manager and **no** permit is taken at all — consistent with the condition, which requires batch mode.

**1.2 — The batch layer builds one primitive for the whole run.**
`src/vkdownloader/services/batch_downloader.py`, the batch entry point: constructs **one**
`asyncio.Semaphore(settings.max_concurrent_downloads)` per batch run, wraps it in `_TrackedSemaphore`,
and passes that wrapper into `download_video` as the `semaphore` argument. `_TrackedSemaphore`
increments `ConcurrencyTracker` on acquire and decrements it on release, so the reported peak counts
**videos**; `ConcurrencyTracker`'s own docstring says so in as many words.

**1.3 — The segment layer builds its own primitive and carries only a boolean across.**
`src/vkdownloader/services/segment_downloader.py`, function `_run_download_session`: constructs a
**fresh** `asyncio.Semaphore(settings.max_concurrent_downloads)` — the local `semaphore_to_use` — and
passes it to `DownloadPolicy.semaphore`. The batch permit enters this layer as the parameter
`video_semaphore` and is consumed for **one purpose only**, the boolean
`is_bounded_batch = video_semaphore is not None`. **No semaphore object is forwarded from the batch
layer into the segment layer.** The only claim made against any semaphore inside the segment
transfer path is `async with policy.semaphore:` in `_download_segment_concurrent`, and
`policy.semaphore` is the segment-local object. The only `.acquire()` calls anywhere in `src/` are
`_TrackedSemaphore`'s own.

**1.4 — The consequence, and its exact limit.**
The nested-claim shape the archived register's `D-01` describes — one non-reentrant primitive claimed
once per video and again per segment — **does not reproduce in this code.** That is a structural
fact read off the source and re-derived for this record. It is **not** a runtime observation, and
section 3 says why that distinction is load-bearing.

**1.5 — The setting is a third bound, and this record observed the amendment.**
Before the transport work, `Settings.max_concurrent_downloads` sized **two** mechanisms: the batch
layer's per-video semaphore with its live-task counting window, and the segment layer's per-download
semaphore with its own counting window. The transport connection pool was **not** sized by the
setting — `_create_connector` passed a constant total ceiling and no per-origin ceiling at all, so
the per-origin bound was the HTTP library's *unbounded* sentinel.

**What this record observed after that work landed**, read from the source:

- `_create_connector` now binds **both** its total ceiling and its per-origin ceiling to the same
  setting value, through a single local, on **both** of its return paths;
- the segment layer's `D-01` comment has gained a clause recording that the two connector ceilings
  carry the same value, that the per-origin term therefore cannot be the binding one, that the
  segment semaphore remains the single binding authority, and that the connector is **per download**
  with no process-wide bound;
- `Settings.max_concurrent_downloads`'s field description now names **three** levels — the batch
  gate, the segment fan-out, and the per-download connection pool — where it previously named two.

**What that means for a reader holding an older description of this setting:** the two-level picture
is superseded. There is still **no process-wide bound**; the honest aggregate is per-download
multiplied by videos in flight. This record asserts nothing about how the HTTP library enforces its
own ceilings — that is a property of an installed library, not of this repository's source, and it
is not what this record is about.

---

## 2. What was NOT executed, and why

**2.1 — The condition.** Batch mode, videos in flight at or above the ceiling, and at least one
video taking the segment path.

**2.2 — It has not been executed.** No batch was run against a live origin by the phase that filed
the finding — by that phase's own design — and none was run for this record. This engagement has no
network access, and this record neither requires nor seeks any.

**2.3 — What was executed instead.** The **route** to the per-part transfer, with the session and
the media-method result substituted. A substituted route is not the condition.

**2.4 — No inference is drawn.** This record states neither that the condition would be harmless nor
that it would fail. It offers no prediction about what a live origin or a live batch would do, in
either direction. That question is open, and this record leaves it open.

---

## 3. A structural identity comparison is not proof

The comparison that establishes section 1 is an **identity** comparison between two semaphore
objects. It shows *which object* the segment layer claims. It cannot show *what happens* when the
condition runs. The validator that decided this finding said exactly that, and this record repeats
it rather than improving on it: **the structural identity comparison is not proof of the
condition's behaviour.**

**This record's own re-derivation does not change that.** It was made by reading the source, not by
running the condition, and re-deriving a fact statically does not convert it into an observation.

**Nothing here closes the finding.** No reader may take section 1 as a clean result, and no reader
may treat the register's registered claim as confirmed against this code.

---

## 4. The register's remedy was implemented; the live-batch half of the recommendation is still outstanding

**4.1 — Option A was implemented.** The archived register's **Fix** entry offered two ownership
models for the permit. **Option A** — one permit per video, with segments bounded by a separate
inner semaphore that the segment layer creates and owns — is what the code implements. The shipped
code satisfies Option A in a stronger form than its wording requires: the shared permit is not
forwarded into the segment layer at all, so it cannot be re-claimed there, and the peak accounting
that Option A asks for is performed by the wrapper at the video level.

**4.2 — What that explains, and what it does not.** It explains **why the nested-claim shape is
absent**: Option A is the reason. It does **not** execute the condition. A remedy that is in place and
a condition that was never run are two different facts, and a record that conflates them has
over-claimed.

**4.3 — Therefore the recommendation is outstanding in both halves.**

- **First half — execute the condition once against a live batch and retire the register's claim.**
  **Not performed, and not performable here:** it requires a live origin, which this engagement's
  boundary forbids. **Owner:** the phase that owns concurrency and cancellation findings.
  **Trigger:** a run permitted to contact a live origin and to execute the condition end to end.
- **Second half — amend the register to record that the nested claim was replaced by a
  segment-layer-owned primitive.** Deferred to section 5.

**4.4 — The register's entry itself is untouched by this record.** It still stands as registered. This
record does not retire it, does not amend it, and does not claim it is wrong.

---

## 5. The register's Location list is stale, and `phase04/VAL-410` is deferred

**5.1 — The Location list fails.** The archived register's **Location** entry cites line numbers.
**Every line reference in it now fails to point at the statement it names**, and the drift is larger
than when the validation measured it: the statements are all still present in the shipped code, under
the semantic anchors named in section 1, and each has moved since. A reader following the register's
own numbers lands on unrelated statements.

**5.2 — The stale path is deliberately not reproduced here.** The finding and the register citation
point at a register location that no longer exists; the register was archived, and the directory it
was cited in holds unrelated files. A durable record must not propagate the very path defect the
correction is about, so this file names only the location that exists:
`.ai/plans/done/01-confirmed-code-defects_DONE.md`.

**5.3 — `phase04/VAL-410` is NOT claimed** by this record or by the block that wrote it. Its work
has two halves and **both are outstanding**:

- **Correcting the two path references inside `CON-002`** — in the source report and in the validated
  artifact — and recording there that `D-01` was fixed rather than merely unexecuted. **Owner:** a
  documentation plan explicitly permitted to edit `.ai/audit/**/findings.md`. **Trigger:** such a
  plan. **Blocked here** because both targets are read-only for this engagement.
- **The archived register's own stale `Location` list, and the register's wording generally**, is
  **phase `09`'s subject** by the validation's own `R-E` allocation. **Owner:** phase `09`.
  **Trigger:** phase `09`'s run.

**5.4 — This record performs neither correction** and claims neither. Recording the deferral is the
whole of its obligation here.

---

## 6. This finding's state, and the encoding that now exists for it

**6.1 — State.** `CON-002` **remains filed**, **remains `UNVERIFIED`**, and **carries no severity**.
It is not deleted, not merged, not reclassified, not closed.

**6.2 — The historical cell stays permanently, uncorrected.** `*none — not executed*` sits outside
the report format's severity vocabulary by design. It is **not** a defect awaiting repair.

**6.3 — The encoding exists and is landed, not promised.** Block `B11` of
`.ai/plans/09-concurrency-cancellation-audit-fixes-completion.md` — *"Give the report format a legal
encoding for a not-executed finding"* — shipped it in commit `3c25dda`. What it did, verified
against that commit rather than assumed:

- the authoritative report template gained a mandatory **`Verification`** field, present in both its
  finding-block field table and its field reference, with the values `observed` and `unverified`, and
  defined in its classification guide. It is required on **every** finding;
- the template's `severity` row states that when a runtime consequence was **not observed**, the band
  is **composed from the structural fact under the owning phase's own severity table**, and that the
  row prescribes no band of its own;
- phase `04`'s handbook had its four absolute "no severity" prohibitions reconciled to that rule — in
  the preamble's two-findings bullet, in the structure-only-severity bullet, in the
  documented-skips bullet, and in binding rule **W-4** of the reporting section;
- the validation task gained one matching check row, `Verification recorded`;
- **no fifth severity member and no fifth type label were added**, so the validation task's own
  prohibition against a fifth word is untouched and still true.

**6.4 — The rule is PROSPECTIVE, and that is precisely why this finding's cell is untouched.** The
template states it in terms: a severity already written is not re-read under the rule. `CON-002`'s
cell was already written. **No band is composed for it now, and none ever will be by this
mechanism.** Composing one today would be reading an already-written cell under a prospective rule,
which is forbidden.

**6.5 — Scope of the rule.** The composition rule governs **future** reports. It says nothing about
what this finding's cell should have said, and this record does not either.

---

## 7. Standing statement

The structural fact is recorded in section 1. The condition was not executed, and section 2 says so
without inferring anything about it. **No severity is assigned. No verdict is recorded. The finding
is not closed.**

Outstanding, with the owners and triggers stated above: executing the condition against a live batch
(section 4.3), and the two corrections `phase04/VAL-410` describes (section 5.3).
