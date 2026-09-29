# Fix Task 01 — Confirmed Code Defects

**Project:** `vkdownloader` — a Python 3.12 Typer CLI that downloads videos from VKontakte. Single short-lived process, one `asyncio.run()` per invocation. No web server, HTTP API, database/ORM, scheduler, container, or accounts.

**Status:** draft — not started
**Source:** the audit phase catalogue rewrite under `.kilo/commands/audit/phases/`, during which each phase's evidence harness was executed against the real code. Every defect below is backed by an observation, not an inference. Evidence reports are in `.ai/reports/`.

**Scope:** production defects in this repository only. Audit-pipeline defects (in `.kilo/commands/audit/*.md` and `.ai/audit/templates/`) are a separate work item and are deliberately excluded.

**Provenance legend**
- `CODE` — re-verified by reading the source while writing this task.
- `EXEC` — observed by running a harness against the code during the audit.

---

## 1. Defect summary

| ID | Severity | Area | Defect | Provenance |
|---|---|---|---|---|
| D-01 | **CRITICAL** | Concurrency | Batch deadlocks: the same `asyncio.Semaphore` is acquired twice | CODE + EXEC |
| D-02 | **CRITICAL** | Credentials | Session cookies are written with a negative expiry and discarded by the consumer | CODE + EXEC |
| D-03 | **HIGH** | CLI error path | The batch error handler raises `UnboundLocalError`, masking every batch failure | CODE + EXEC |
| D-04 | **HIGH** | Cancellation | An interrupted batch reports failures and exits 1 instead of 130 | CODE + EXEC |
| D-05 | **HIGH** | CLI contract | The exit-code map is four-valued; the product's own recovery hint routes into an unhandled value | EXEC |
| D-06 | **HIGH** | Packaging | The source distribution ships a dependency tree, a second copy of the source, and user data | EXEC |
| D-07 | **HIGH** | Tooling | `uv sync` uninstalls the lint, type-check and test tooling the project verifies itself with | CODE + EXEC |
| D-08 | **HIGH** | Test suite | Three of four file-permission tests assert nothing and report success | EXEC |
| D-09 | **MEDIUM** | Filesystem | Merge amplification measured at 2.96× with no output-size or free-space ceiling | EXEC |
| D-10 | **MEDIUM** | Test suite | The environment file resolves from the working directory; nothing isolates it, so a documented variable changes test outcomes | EXEC |
| D-11 | **MEDIUM** | Filesystem | Requested file permissions are not honoured on the declared development platform | EXEC |
| D-12 | **MEDIUM** | Test suite | The stream-selection path has no executing oracle at all | EXEC |
| D-13 | **LOW** | Dependencies | Two declared dev tools are unused or duplicated by the configured linter | CODE |

---

## 2. Defects

### D-01 · CRITICAL · Batch deadlocks on the shared semaphore

**Location**
- `src/vkdownloader/services/batch_downloader.py:281` — `shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)`
- `src/vkdownloader/services/batch_downloader.py:153` — `tracked_semaphore = _TrackedSemaphore(shared_semaphore, peak_tracker)`
- `src/vkdownloader/services/batch_downloader.py:202` — the tracked wrapper is passed into `download_video` as `semaphore`
- `src/vkdownloader/services/batch_downloader.py:72` — `await self._semaphore.acquire()` (the wrapper's acquire)
- `src/vkdownloader/services/downloader.py:491-493` — `_semaphore_context(semaphore)` is entered around the whole download
- `src/vkdownloader/services/downloader.py:509,557,578` — the *same* `semaphore` object is forwarded down the call chain
- `src/vkdownloader/services/segment_downloader.py:679` — `async with policy.semaphore:` per segment

**Symptom**
`asyncio.Semaphore` is not reentrant. The batch layer acquires one permit per video task, and the segment layer then acquires a *second* permit from that same semaphore for each segment. Once the number of videos in flight reaches `max_concurrent_downloads`, every permit is held by an outer acquisition and no inner acquisition can be satisfied. The process stops making progress and never returns.

**Trigger condition**
Reachable whenever all of the following hold simultaneously: batch mode, `videos in flight >= max_concurrent_downloads`, and at least one video taking the segment path. This is the *default* configuration, not an edge case.

**Evidence**
The reproduction was executed offline against the production objects. Observed: units make no progress, no claim is released, a second stop changes nothing, and no kind of work observes the stop while it is running.

**Fix**
Decide and implement one ownership model for the permit, and apply it consistently:

- **Option A — one permit per video, segments bounded by a separate inner semaphore.** The batch semaphore bounds videos; the segment downloader creates and owns its own semaphore sized by `max_concurrent_downloads` and uses the shared one only for peak accounting. This preserves the existing intent: the batch limit means *videos*, and the segment fan-out is an internal detail.
- **Option B — one permit per segment.** Do not acquire the shared semaphore at the video level; acquire it only around each segment transfer. The batch limit then means *transfers*. This changes the meaning of `max_concurrent_downloads` and must be reflected in its field documentation and in the setting's user-facing description.

Whichever is chosen, `_TrackedSemaphore` must wrap the object it actually gates, and the peak figure it reports must be labelled with the unit it measures. A peak that counts videos while the limit counts segments is a third, incorrect answer.

**Acceptance criteria**
- A batch of at least `max_concurrent_downloads + 2` URLs completes without hanging, with at least one video taking the segment path.
- The regression test runs the **production** semaphore and the production batch wrapper. A test that patches the process boundary cannot observe this defect and must not be counted as coverage for it.
- The reported peak concurrency is labelled with what it counts.

---

### D-02 · CRITICAL · Session cookies are serialised with a negative expiry and dropped

**Location**
- `src/vkdownloader/services/extractor.py:273` — `raw_cookies = await page.context.cookies()`
- `src/vkdownloader/services/cookies.py:54` — `expires = int(cookie_item.get("expires", 0))`
- `src/vkdownloader/services/cookies.py:57` — the value is written into the Netscape-format line

**Symptom**
Browser storage represents a session cookie with an expiry of `-1`. The serialiser converts it to the integer `-1` and writes it into the expiry column of the Netscape cookie file. That column expects either a positive UNIX timestamp or `0` to mean "session cookie". A value of `-1` is a timestamp before the epoch, so the consumer treats the cookie as long expired and discards it without a diagnostic.

Net effect: with `--cookie-source browser`, the cookie file the product writes contains **no usable cookies**. The browser-cookie feature is a no-op and fails silently.

**Evidence**
Executed: the serialiser was driven with a synthetic session and the resulting file was loaded with the installed consumer itself. Recorded: every entry it kept, every entry it discarded, and its own diagnostics. The three-expiry comparison (absent / future / past) isolates the cause to the expiry column alone.

**Fix**
- Map a non-positive expiry to `0` (the Netscape "session cookie" sentinel) rather than writing it through unchanged.
- Keep the field's semantics explicit in a comment: a browser session cookie is not an expired cookie.
- **Verify with the consumer, not with the file's shape.** A file that *looks* correct is not evidence; load it with the real cookie parser and assert what it kept. The three-expiry comparison must become a regression test.

**Acceptance criteria**
- A synthetic session cookie serialised through the product's own writer survives a round trip through the real consumer.
- The regression test asserts on the consumer's parse result, not on the file's contents.
- A cookie with no expiry and a cookie with a future expiry both survive; a cookie with a past expiry is still dropped, as intended.

---

### D-03 · HIGH · The batch error handler raises before it can report

**Location**
- `src/vkdownloader/cli.py:242` — `valid_urls: list[str] = []` (the binding)
- `src/vkdownloader/cli.py:245` — `urls_file.read_text()` (can raise)
- `src/vkdownloader/cli.py:293` — `url_count=len(valid_urls)` inside the `except` handler

**Symptom**
The handler that is supposed to report a batch failure references a name bound 51 lines earlier. If anything between the binding and the handler raises — a `.env` or URL file containing one non-UTF-8 byte raises `UnicodeDecodeError` at line 245 — the handler itself raises `UnboundLocalError`. The designed message never prints and the intended exit code never happens; the user sees a traceback instead.

**Scope**
Batch only. The single-download command's handler is not affected.

**Evidence**
Executed with a malformed `.env`: `UnboundLocalError` reproduced.

**Fix**
Initialise the name before the first statement that can fail, or make the handler not depend on it. The two-line version is to move the initialisation above the file read. Do not paper over it with a `try`/`except` around the handler.

**Acceptance criteria**
- A batch run against a non-UTF-8 `.env` prints the designed message and exits 1.
- A regression test covers it. This is a handler that must be *tested*; a code path no test can reach is how it broke.

---

### D-04 · HIGH · An interrupted batch reports failures instead of interruption

**Location**
- `src/vkdownloader/services/batch_downloader.py` — the module does not reference the shutdown event at all (verified: no occurrence of `get_shutdown_event` in the file)
- `src/vkdownloader/services/batch_downloader.py:208` — `status = "success" if result else "failed"`
- `src/vkdownloader/services/downloader.py:674-681` — the single-download path *does* consult the shutdown event and raises `CancelledError`

**Symptom**
The shutdown event is checked throughout the codebase — and, in the single-download path, at exactly the right moment — but the batch runner never reads it. On Ctrl-C every in-flight item is recorded as `failed`, the summary reports `Failed: N`, and the command exits 1. The same interruption in single-download mode exits 130.

Two consequences beyond the wrong number: a script cannot distinguish "the user stopped this" from "these videos are broken", and the summary actively misreports work the user cancelled as work that failed. The preserved partial segments are never mentioned, so the user is not told that resumable data exists on disk.

**Evidence**
Executed with the event set: `Failed: 1`, exit 1.

**Fix**
- Consult the shutdown event at the point a result is classified, not only inside the transfer. A cancelled item is not a failed item.
- Give cancellation its own summary state and its own exit code, and make the summary say that resumable data was kept when it was.
- Do not lose the partial-file information the single path already surfaces.

**Acceptance criteria**
- An interrupted batch exits 130 and its summary does not report the cancelled items as failures.
- The regression test drives the real classification path with the event set.

---

### D-05 · HIGH · The exit-code contract is wider than the product handles

**Location**
- The product maps failures to `0` / `1` / `130`.
- The command layer additionally emits `2` for: no command, unknown command, missing argument, unknown option, invalid enum value, non-existent path. None of these are handled.
- `src/vkdownloader/cli.py:143-146` — the error text offers `Use one of: 240p, 360p, …`

**Symptom**
The value set is **four**, not three. More seriously, the product's own recovery instruction routes into it: on an invalid quality value the user is told to pass one of a set of values *with* the `p` suffix, while the parser accepts them without it. Following the instruction the product itself gives produces exit 2, a value the product never emits deliberately and never documents.

**Why it matters**
The exit code is the command's contract with every script that drives it. Every value must correspond to a distinct, documented, terminal outcome — and the documented recovery path must lead to a value the product intends.

**Fix**
- Decide whether `2` is part of the contract. If it is, document it and separate it from the failure value. If it is not, intercept the parser's usage error and map it to the value the product already uses for "you invoked me wrongly".
- **Fix the recovery hint so the value it names is the value the parser accepts.** This is the part users actually hit. Verify by running it: the exact string the product prints must be accepted when pasted.

**Acceptance criteria**
- Every value the process can emit is documented, with the terminal outcome it represents.
- The recovery hint, pasted verbatim, yields a documented value.

---

### D-06 · HIGH · The source distribution ships the wrong contents

**Location** — `pyproject.toml` has **no** `[tool.hatch.build.targets.sdist]` section.

**Symptom**
Measured by building both artifacts and enumerating their central directories:

| Artifact | Entries | Size |
|---|---|---|
| Wheel | 34 | 75,305 bytes |
| Source distribution | 1,770 | 6,125,649 bytes (**81×**) |

The source distribution contains 1,353 entries from a vendored dependency tree, 214 entries from a git worktree that holds a **complete second copy of `src/vkdownloader/`**, this audit's own findings corpus, the full audit phase catalogue, and a user's working file (`urls.txt`).

**Root cause**
There is no source-distribution section, so the builder's default applies. The default excludes what version control *ignores* — and the offending trees are untracked but **not** ignored, so they are included.

**Severity note**
This is a release blocker, not a routine finding. The artifact publishes dependency code, a duplicate of the source, and user data. It also proves that the *wheel* is correct for a reason nobody stated: it is correct by accident, because the default sweeps the whole package directory. Nothing guarantees that tomorrow.

**Fix**
- Add an explicit source-distribution section listing what belongs in the archive.
- Add a release check that builds the artifact and fails when its entry count or contents differ from the intent. A size ratio is a crude proxy, but it catches this class in seconds; an entry-set diff is better.
- Add the offending paths to the ignore file so the *reason* is documented where a developer will look.
- Separately: state explicitly in the manifest that the shipped data file is included, so it stops being a happy accident.

**Acceptance criteria**
- The source distribution contains no vendored dependency tree, no worktree content, no audit corpus and no user data.
- The release check runs in the pipeline and fails on drift.
- The shipped data file's inclusion is stated in the manifest, not implied.

---

### D-07 · HIGH · The default sync removes the project's own verification tooling

**Location**
- `pyproject.toml:31-40` — `[project.optional-dependencies] dev` holds `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `black`, `isort`, `pyyaml`
- `pyproject.toml:95-99` — `[dependency-groups] dev` holds only `basedpyright`, `pyyaml`

**Symptom**
Optional-dependency **extras** are not installed by a default sync. Dependency **groups** are. The dev tooling the project verifies itself with therefore lives in the mechanism that a plain `uv sync` does not use, and the group that *is* used holds a checker that is never run.

Measured: `uv sync --dry-run` exits 0 and reports it would uninstall 16 packages, among them `ruff`, `mypy`, `pytest` and `pytest-asyncio`. After a plain `uv sync`, **all four verification commands in `.ai/context/commands.md` fail** — `uv run pytest <path>`, `uv run ruff check <path>`, `uv run ruff format --check <path>`, `uv run mypy <path>`.

**Why it matters**
The project's documented verification workflow silently stops working on a fresh clone or after any clean sync. A developer who trusts the documented commands gets a tool-not-found error and has no reason to suspect the manifest.

**Fix**
- Move the verification tooling into the dependency group that the default sync installs.
- Decide the fate of `basedpyright` (see D-13) rather than leaving it declared and unused.

**Acceptance criteria**
- After a clean `uv sync`, all four documented commands resolve and run.
- The manifest's two dev mechanisms are not both present, or the one that is unused is removed.

---

### D-08 · HIGH · Three of four permission tests assert nothing

**Location** — the file-permission tests in the suite.

**Symptom**
Three of the four permission oracles are guarded by an inline platform check whose body is skipped on the declared development platform, and the guard **returns as passing**. The test reports success while executing no assertion. A fourth test is skipped properly and is honest about it.

This is a defect of the *verification*, not of the product: the suite advertises coverage it does not provide, and it does so silently. Any future regression in file permissions is undetected, and the suite will still be green.

**Compounding factor**
The one genuine platform guarantee — that only the owner can read an artefact — **cannot be executed on Windows at all**, because the mode-setting call there toggles only the read-only attribute. The measured mode after the call was not owner-only. So the product has no working confinement on the declared platform, and the test that would have told us is one of the three that assert nothing.

**Fix**
- Convert the three inline guards to explicit skips, so an unexecuted test reports itself as unexecuted. A platform guard that silently passes is worse than no test.
- Decide and document the confinement story for the declared platform. Either the guarantee is not offered there, and the documentation says so, or the mechanism is changed to one that holds.
- Do not delete the checks; make them honest.

**Acceptance criteria**
- On the declared platform, each of the four checks reports *skipped* with a reason. None reports *passed* while asserting nothing.
- The documented confinement behaviour matches what the code does on that platform.

---

### D-09 · MEDIUM · Merge amplification is unbounded

**Symptom**
The batched merge writes its output to disk while reading its input from disk, so peak on-disk usage is a multiple of the final artefact size. Measured by sampling the working directory's total size throughout a real merge and recording the **peak**, not the endpoints: amplification is **2.96×**.

Nothing bounds it. An exhaustive search for an output-size cap, a free-space probe or a volume query found none.

**Risk**
A single large video can exhaust a volume mid-merge, and the merge is the one operation that is not resumable — the input segments are still needed. Exceeding free space therefore converts a large download into a failed one with no partial result.

**Fix**
- State the amplification factor in the user-facing documentation, or
- probe free space before merging and fail early with an actionable message, or
- both.

Pick deliberately. The constraint is that the failure mode is currently a filesystem error at an unknown point in a non-resumable operation.

**Acceptance criteria**
- The documented behaviour matches the code for the declared platform.
- If a probe is added, a full-volume case is covered by a documented skip or a simulated test — do not fill a real volume in a test.

---

### D-10 · MEDIUM · The environment file is not isolated, so the suite is not hermetic

**Symptom**
The environment file is resolved **from the working directory**, no fixture sets it aside, and there is no autouse isolation anywhere. Consequence, measured: setting one documented product variable from outside changes a test's outcome.

```
VKDOWNLOADER_COOKIE_SOURCE=browser uv run pytest tests/test_config.py -q
→ 1 failed, 26 passed   (test_cookie_source_default asserts "none", observes "browser")
```

Three documented product variables make 2 of 416 tests fail. The suite's result therefore depends on the shell it is launched from, which is the definition of a non-hermetic suite.

**Fix**
- Add an autouse fixture that pins the environment source to *nothing* for the whole suite, so no ambient file or variable can decide a result.
- Add a test that *proves* the isolation: vary a declared input deliberately and show that a test's result does not move. A repeated green run proves nothing — an unisolated suite repeats too.

**Acceptance criteria**
- The failing invocation above passes.
- The isolation proof test exists and fails if the autouse fixture is removed.

---

### D-11 · MEDIUM · Requested file permissions are not honoured on the declared platform

**Symptom**
The product requests a restrictive mode on every file it creates. On the declared development platform the mode-setting call toggles only the read-only attribute, so the **measured** mode after the call is not the **requested** one. The product's confinement guarantee does not hold where it is developed and used.

**Severity note**
Keep this bounded. The consequence is limited to the declared platform and to the artefacts enumerated in D-09/D-06; it is not a remote-exploitable confidentiality boundary. But it is the guarantee the code appears to offer and does not deliver, and D-08 means nothing in the suite would catch a regression.

**Fix**
- Decide per artefact and per platform whether confinement is offered, and make the code and the documentation agree with the decision.
- Where it is not offered, say so in the configuration documentation rather than implying it is.

**Acceptance criteria**
- For every artefact, the documented confinement matches the measured behaviour on the declared platform.
- The permission tests report what they actually verified (D-08).

---

### D-12 · MEDIUM · The stream-selection path has no executing oracle

**Symptom**
`src/vkdownloader/services/extractor.py:191-207` — the audio-only filter, the HLS-versus-MP4 decision and the unknown-height path — is at **0 %** coverage. Every extractor test returns an empty format list, so the selection code is never entered. The degraded branch of the auto-download ladder (`downloader.py:560-589`) and the browser extraction body (`extractor.py:263-292`, 30 statements each) are likewise uncovered.

**Why it matters beyond the number**
This is the code that decides *which* stream is downloaded. D-01's deadlock sits on this path, and D-02's cookie defect is in the path that refreshes it. The two highest-severity defects in this task are in a region the suite cannot see.

**Fix**
Add tests that drive the selection function with constructed stream sets: the audio-only filter, the height comparison including the unknown-height case, and the HLS/MP4 branch. The suite is 415 passing tests at 86 % coverage; this is not a coverage problem, it is a **missing oracle** problem, and the weighting must be by the subjects the other audit phases claim, not by line count.

**Acceptance criteria**
- The selection function is entered by at least one test that can fail.
- No test asserts coverage; each asserts a selection outcome.

---

### D-13 · LOW · Declared development dependencies that are not used

**Location**
- `pyproject.toml:38-39` — `black` and `isort` are declared
- The project formats and sorts imports with the configured linter
- `pyproject.toml:97` — `basedpyright` is declared; the configured type checker is a different one

**Symptom**
Two formatters are declared beside a linter that already performs their function, and a second type checker is declared that is never run. Both are dead weight in the manifest, and `basedpyright` compounds D-07 by occupying the group that a default sync actually installs.

**Fix**
Remove `black`, `isort` and `basedpyright`, or state what each is for. An unused declaration is not free: it is resolved, installed or synced for nothing, and it misleads a reader about which checker is authoritative.

**Acceptance criteria**
- Every declared distribution is either reached by the source or the tests, or removed.

---

## 3. Suggested order

The order is dependency-driven, not severity-driven. Fixing D-01 first is correct, but it is only verifiable once D-12's oracle exists — otherwise the regression test cannot distinguish a fix from a code path that never runs.

1. **D-01, D-12** together. Add the selection oracle, then fix the permit ownership and prove it with a test that exercises the production objects. D-12 first within the pair, so D-01 has something that can fail.
2. **D-02.** Independent of the above, and the second-highest consequence: a feature that silently does nothing.
3. **D-03, D-04, D-05.** The CLI contract. Group them — they share the exit-code and reporting path, and D-05's recovery-hint fix is a one-line change that should not wait for the rest.
4. **D-07, D-13.** The manifest. Do these before adding any new test, so the tooling that runs the new tests is reliably present.
5. **D-06.** Packaging last among these: it is a release concern, and its fix should not land before the artefact it ships actually works.
6. **D-08, D-11.** The permission pair. They are one decision, not two: what confinement this product offers on its declared platform.
7. **D-09, D-10.** Independent cleanups.

---

## 4. Constraints on the fix

- **Production code is the priority.** If a test conflicts with the architecture or the business logic, fix or remove the test. Never distort production code to satisfy a test.
- **No test-only branch in production code.** A branch that exists only for the suite is a defect; the three inline platform guards in D-08 are examples.
- **A test that cannot fail is worse than no test**, because it converts an unknown into a false assurance. This is the common thread behind D-08, D-10 and D-12.
- **Silence is not evidence.** When a fix's effect cannot be observed on the declared platform, record the question as unanswered rather than as passing.
- **English only** in code, comments, log messages and documentation.

## 5. Definition of done

- Every defect above is either fixed or explicitly deferred with a recorded reason and an owner.
- Each fix is covered by a test that can fail; for D-01, D-02, D-04 and D-12, the test drives the **production** objects, not a patched boundary.
- The full suite passes, and the four documented verification commands resolve after a clean sync (D-07).
- Both build artefacts are inspected and their contents match intent (D-06).
- No defect in this document is left with a verification that reports success without executing its assertions.
