# Phase 10 Audit Findings — Test Coverage and Oracles

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/10-audit-test-coverage.md`
**Status:** complete
**Validated:** yes

> **Deviation from the report format, stated once here.** The template
> (`.ai/audit/templates/audit-findings.md`) defines nine mandatory fields per finding
> (`:64-74`) and none of them carries a validation decision — its finding block runs
> from the heading straight into the field table (`:19-33`). The `Validation Note` this
> phase must attach to **every** decided finding therefore has no slot. It is written
> directly below each `### {ID}:` heading, above the field table, in every case where a
> decision changes something: a re-derived severity, a reclassification, a corrected
> anchor, or a cross-phase resolution. The absence of the slot is a defect of the format
> and is filed here as **`VAL-121`**; it has been filed before, independently, in the
> `02` validation store as `VAL-001`, in the `03` store as `VAL-001`, and again in every
> subsequent store. This is the only deviation from the format in this artifact.
>
> **How the decisions were reached.** Every one of the 16 findings was re-derived from the
> artifact it names and from a runtime measurement made in this run — not from the
> report's own wording. Five findings were reproduced end-to-end against real product
> code, the real installed consumer and the real installed muxer; the other eleven were
> confirmed against per-statement coverage output produced in this run, or against a
> direct re-measurement of the object the finding names. No source file was modified and
> no finding was deleted; every correction is recorded in place. Six findings are filed
> against the audit inputs themselves.
>
> **Scratch location.** Every probe was written to `.temp/val10/` and every coverage run
> redirected `COVERAGE_FILE` into that directory. No coverage data, cache or artefact
> landed in the tracked tree. `.temp/` was removed by a concurrent process part-way
> through this run and was recreated for the final write; that removal is a workspace
> observation, not a finding against this report.

---

## R0 — Corpus map, identifier map, decision-record map, pipeline-document map

Recorded before any check, because these four are the ways this phase manufactures a clean
bill of health. Searched with `.ai/` as the scope, excluding `.kilo/worktrees/`.

**Corpus map.** The phase range is `01`–`11` plus this file. The corpus changed shape
during this run: `.ai/audit/11-supply-chain/findings.md` did not exist when this run
started and existed when it finished. That is recorded, not re-run.

| Phase | Handbook | Findings file | Validation store | State at close |
|---|---|---|---|---|
| 01 entry/architecture | `01-audit-entry-architecture.md` | `01-entry-architecture/` | present | validated |
| 02 configuration | `02-audit-config.md` | `02-config/` | present | validated |
| 03 network/resilience | `03-audit-network-resilience.md` | `03-network-resilience/` | present | validated |
| 04 concurrency/cancellation | `04-audit-concurrency-cancellation.md` | `04-concurrency-cancellation/` | present | validated |
| 05 subprocess/browser | `05-subprocess-browser.md` | `05-subprocess-browser/` | present | validated |
| 06 credentials/secrets | `06-audit-credentials-secrets.md` | `06-credentials-secrets/` | present | validated |
| 07 filesystem/artifacts | `07-audit-filesystem-artifacts.md` | `07-filesystem-artifacts/` | present | validated |
| 08 cli/observability | `08-audit-cli-observability.md` | `08-cli-observability/` | present | validated |
| 09 code quality | `09-audit-code-quality.md` | `09-code-quality/` | present | validated |
| 10 test coverage | `10-audit-test-coverage.md` | `10-test-coverage/` | — | **the file this run validates** |
| 11 supply chain | `11-audit-supply-chain.md` | `11-supply-chain/` | **absent** | appeared during this run, `DEP-001`–`DEP-003`; not validated here |
| 99 validation | `99-audit-validate.md` | — | this file | running |

No findings file exists outside the `01`–`11` range. A stale nine-phase catalogue
(`01-audit-cli` … `09-structural-quality`) and nine stale validation artefacts exist under
`.kilo/worktrees/southern-bandana/.ai/audit/`; they are a previous catalogue, they are
excluded from every count in this artifact, and they are the subject of `VAL-124`.

**Identifier map.** Live prefixes in the corpus, by phase: `ENT` (01, 14), `CFG` (02, 8),
`NET` + `SKIP` (03, 18 + 6), `CON` (04, 10), `TRN` + `BRW` (05, 13 + 3), `SEC` (06, 10),
`ART` (07, 14), `OUT` (08, 17), `QLT` (09, 13), `TST` (10, 16), `DEP` (11, 2), `VAL` (99).
No prefix is unclaimed, and no two phases share one.

**The `VAL-` prefix is already collided eight times, and this run does not add a ninth
meaning to it.** `VAL-001` carries two unrelated subjects already (the missing decision
slot, `02-config-validated-findings.md`, and the cross-phase connection-ceiling conflict,
`03-network-resilience-validated-findings.md`) and is repeated in six further stores. The
collision is already filed as `VAL-112` in the `01` store. Runs `04`, `05`, `06`, `07` and
`09` escaped it with per-phase bands. This run continues that escape and mints
**`VAL-1xx`**, starting at **`VAL-120`** because `VAL-100`–`VAL-112` are occupied across
the stores and `VAL-105` is additionally carried in the test tree at
`tests/test_cli.py:1829, 1858`.

**Decision-record map.** The report format has no slot for a decision
(`.ai/audit/templates/audit-findings.md:19-33`, `:64-74`) — an **absent slot**, recorded
once here and filed as `VAL-121`. Every decision in this artifact is therefore readable
only in this file.

**Pipeline-document map.** The documents that state the pipeline's own execution claims
were read before the first check. Results:

| Document | Claim checked | Result |
|---|---|---|
| `audit-multi-phase.md:94` vs `:105` | validator write path vs the path whose existence is verified | identical; no defect |
| `audit-multi-phase.md:43` | reads `AGENTS.md` as mandatory base context | **no root `AGENTS.md` exists** → `VAL-122` |
| `audit-multi-phase.md:86` vs `:117-124` | the validator gate vs the coverage the run then reports | gate has no evaluable condition; the closing output claims coverage unconditionally → `VAL-123` |
| `audit-multi-phase.md:75, 98`; `audit-refine.md:50` | roles named in launches vs the roster on disk | all three exist; no defect |
| `.kilo/agents/auditor.md:257-259`; `.kilo/agents/validator.md:243-245, 356-358` | the type vocabulary the role that writes a report carries vs the four the format defines | the role carries three; `RUNTIME-ERROR` is omitted → `VAL-121` |
| `audit-refine.md`, `audit-phase-refine.md` | an instruction that deletes the record of a decision | absent; the commit `d62671b` already removed it |
| `audit-orphaned.md:30-47` | the protect-list of a reachability census vs the audit's own documents and every worktree | no exemption is written → `VAL-124` |
| `audit-tests-full.md:168` | "next available number", with a gap check | no worked example, target directory `.ai/audit/tests/` does not exist, no collision observable → not filed |

---

## Checkpoint 1 — R1 Baseline and R2 Corpus Instrumentation

- **Stage:** R1 Baseline and R2 Corpus Instrumentation
- **Findings in scope:** 16
- **Evidence anchor:** this file, self-contained — every finding's original text is
  retained below, above its decision record. The source report
  `.ai/audit/10-test-coverage/findings.md` was opened read-only and is unmodified.
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

**The baseline, re-measured in this run** (`uv run --with pytest-cov pytest tests -q -rs
--cov=vkdownloader`), and it matches the report's R1 line exactly:

```
collected 502 items
498 passed, 4 skipped in 24.62s
TOTAL   2234 statements   239 missed   89% cover
```

**The four skips are honest, and the report is right to say so.** Measured reasons, in the
order pytest prints them:

| Skipped test | Reason reported | What the probe measured |
|---|---|---|
| `test_config.py` log-file mode `0o600` | `os.name == "nt"` | `os.chmod(p, 0o600)` → measured `0o666`; `os.name == "nt"` → **True** |
| `test_config.py` log-file `touch(mode=0o600)` | `os.name == "nt"` | `p.touch(mode=0o600)` → measured `0o666`; `os.name == "nt"` → **True** |
| `test_progress_display.py` keyboard-interrupt | `stdin.isatty() == True` | measured `stdin.isatty() == True` |
| `test_hls_downloader.py` ffmpeg-timeout assertion | `stdout.isatty() == False` | measured `stdout.isatty() == False`, `stderr.isatty() == False` |

Each condition is a true statement about the platform at the moment of collection, so the
skip is a correctly declared platform limit, not a suppressed failure. That is the
distinction `TST-013` draws and this run does not disturb it.

**The R5 environment axis is genuinely isolated, and the report's claim is re-measured
here rather than accepted.** `tests/conftest.py:13-42` is an autouse fixture that deletes
every `VKDOWNLOADER_*` entry from `os.environ` and `monkeypatch.chdir(tmp_path)` for the
duration of every test. Three documented variables were set in the parent process and
`tests/test_config.py` re-run; the baseline for that file is 30 tests, 30 passed / 2
skipped, and **0 of 30 moved** under any of them:

| Variable set in the parent process | Result |
|---|---|
| `VKDOWNLOADER_COOKIE_SOURCE=browser` | 30 passed, 2 skipped |
| `VKDOWNLOADER_MAX_RETRIES=99` | 30 passed, 2 skipped |
| `VKDOWNLOADER_SSL_VERIFY=false` | 30 passed, 2 skipped |

**The declared-vs-enforced axis (R13), re-measured.** There is no `pytest.ini`, no
`tox.ini`, no `setup.cfg` and no `[tool.pytest.ini_options]` table in `pyproject.toml`;
`pyproject.toml` carries only `[tool.hatch.*]`, `[tool.ruff*]` and `[tool.mypy*]`.
`uv run pytest --no-cov` fails with `pytest: error: unrecognized arguments: --no-cov`,
which is the direct proof that `pytest-cov` is not in the `[dependency-groups] dev` list
(`pyproject.toml:111-115` carries `pytest` and `pytest-asyncio` only). Marker census
across the test tree: **174** `@pytest.mark.asyncio`, **4** `@pytest.mark.skipif`.

**The CI axis (R14), re-measured by reading both workflows.** `packaging-check.yml:53` is
the only step that invokes pytest, and it invokes `uv run pytest tests/test_packaging.py
-v` — a single module. `doc-lint.yml` runs one `grep` for NUL bytes in `docs/` and nothing
else. No job in the repository executes the suite.

---

*The source report's own R1–R14 record and its documented-skip table,
retained unchanged above the decisions. Every figure in it was
re-measured in Checkpoint 1 above and matches.*

---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 10 Audit Findings — Test Coverage

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/10-audit-test-coverage.md`
**Status:** complete
**Validated:** no

**Measurement basis.** `HEAD` = `a335b2a`. The working tree is dirty: `src/vkdownloader/cli.py` and
`src/vkdownloader/config.py` carry uncommitted edits from a concurrent agent. Every anchor in
`services/downloader.py`, `services/segment_downloader.py`, `services/cookies.py`,
`services/ffmpeg_utils.py`, `services/downloader_throttle.py`, `services/signal_handlers.py`,
`utils/security.py` and `utils/url_sanitizer.py` is **HEAD-anchored** — those files are unmodified.
Anchors in `cli.py` and `config.py` are **working-tree-anchored** and are labelled as such.

**Runtime.** Windows (`os.name == 'nt'`, `platform win32`), CPython 3.12.1, pytest 9.1.1,
pytest-asyncio 1.4.0, ffmpeg `N-117624-g9eb7e8d2a4-20241023`. All probes ran under `.temp/t10/`
(gitignored) and were deleted; the tracked tree was confirmed clean after R2 and after R12.

---

## Verification record

| Row | What was run | Result |
|---|---|---|
| R1 | `uv run pytest tests -q -p no:cacheprovider -rs` ×2 + `--collect-only -q` | 502 collected; 498 passed, 4 skipped, 0 failed, 0 warnings; 25.4 s and 28.5 s. Three runs agree. Counts the state the findings below were observed in — filed as coverage, never as evidence of isolation. |
| R2 | `uv run --with pytest-cov pytest tests --cov=vkdownloader --cov-report=term-missing` (then `json:` redirected into `.temp/t10/`) | 2234 statements, 239 missed, **89 %**. Per-module table and the complete missing-line set captured. `COVERAGE_FILE` redirected so the run left nothing in the tracked tree; `git status` confirmed clean afterwards. |
| R3 | Missing-line set ∩ statement ranges obtained by **parsing** each module with `ast` (not reading it) | Range→missing intersections produced for every body cited below. |
| R4 | Substitution-site enumeration per external boundary role | 63 distinct product-space targets / 368 sites; 5 external / 58 sites. Real crossing of any boundary is a documented skip (fixed wording below). |
| R5 | One `VKDOWNLOADER_*` variable set alone per run; whole suite re-launched from a second working directory; suite re-run with no overlay | `VKDOWNLOADER_COOKIE_SOURCE=browser`, `VKDOWNLOADER_MAX_RETRIES=99`, `VKDOWNLOADER_SSL_VERIFY=false` each moved **0** of 30 tests in `tests/test_config.py`. Second working directory (`.temp/t10/`): 498 passed / 4 skipped, identical. The `tests/conftest.py:13-42` autouse fixture neutralises both halves. |
| R6 | Each of the 19 test modules run alone; two explicit orderings of the process-global-mutating modules | Per-file results sum to exactly the whole-suite result (498 + 4). Both orderings: 250 passed / 4 skipped. Restoration probes: `test_hls_downloader.py:2655` patches `signal.signal` itself, so no real process signal state is mutated; `test_progress_display.py:283-313` asserts handlers are repointed back and `test_progress_display.py:38` provides a restoring fixture. |
| R7 | Unpatched construction search per boundary role | HTTP client: **0** references to `aiohttp` / `ClientSession` in the entire test tree. Process: 42 `patch("asyncio.create_subprocess_exec")` sites, 0 unpatched. Media tool: 6 `patch("yt_dlp.YoutubeDL")` sites, 0 unpatched. Browser driver: 2 `patch(...async_playwright)` sites, 0 unpatched. Real child processes in the whole suite: 2, both harness (`test_packaging.py:309` `uv build`; `test_config.py:427` the `.env` positive-control probe) — neither is a product subprocess. |
| R8 | Every `patch()` first argument resolved to a dotted name by AST; assigned one of four classes | 426 sites classified. Disqualifying classes: the subject (7 sites on `download_hls_with_resume`, 7 on `HLSDownloader.download_with_ffmpeg`); scheduling primitives (4 on `asyncio.wait_for`, 1 on `asyncio.get_running_loop`); production models whose validation is the point (24 on `vkdownloader.cli.Settings`). |
| R9 | Per test, `patch()` targets intersected with symbols imported from the product; compared-value provenance classified | No exact leaf-name self-substitution. Two self-confirming classes present: read-backs of a stand-in's own call record (e.g. `test_security.py:75` `call_kwargs = mock_logger.warning.call_args[1]`) and values the test configured into a stand-in (the `MagicMock` settings at 24 `cli.Settings` sites). |
| R10 | Every conditional and skip guard enumerated; real terminal-attachment state and real access-control state read by a throwaway probe test | 4 skip guards, 0 conditionals, all 4 reported as **skips** under `-rs`. Probe output: `sys.stdin.isatty()=True`, `sys.stdout.isatty()=False`, `sys.stderr.isatty()=False`; a file created and `os.chmod(p, 0o600)` measured `st_mode & 0o777 == 0o666`, `st_file_attributes == 32`. The guards are honest; the *form* is a reported skip, not a reported pass. |
| R11 | `pyproject.toml`, `pytest.ini`, `tox.ini`, `setup.cfg` inspected at the root and in the test tree; markers enumerated against `--markers` | **No pytest configuration file exists anywhere.** Markers used: `asyncio` ×174, `skipif` ×4 — both registered. Difference: empty. |
| R12 | One undecorated `async def` test in a scratch file outside the tracked tree, run with `--rootdir=<repo>` | **Failed**: `Failed: async def functions are not natively supported` … `You need to install a suitable plugin`. pytest-asyncio 1.4.0 defaults to `asyncio_mode=strict`; omitting the decorator is a hard failure, not a silent pass. File deleted; `git status` clean. |
| R13 | Both workflow definitions read | 2 workflows. `packaging-check.yml:44` runs `uv run pytest tests/test_packaging.py -v` and fires on `tests/**`. `doc-lint.yml` greps `docs/` for NUL bytes. Test-execution job: **present but scoped to 1 of 21 modules (14 of 502 tests)**. lint / format / typecheck / dependency-scan / secret-scan / lockfile-check / build-and-publish: absent — recorded as a cross-reference to `11`, not filed here. |
| R14 | Finding-shaped identifiers swept from the test tree; each resolved against the current tree and the register | 9 `D-` ids carried, **all 9 resolve** to entries in `.ai/plans/done/01-confirmed-code-defects_DONE.md`. Three carried ids use this phase's own live prefix (see TST-015). No identifier was adopted. |

### Documented skips (fixed wording)

- **R4 — crossing a real process, media-tool, browser-driver or HTTP-client boundary.** Attempted:
  run the product's own subprocess/network/browser paths unmodified. Why the evidence is unobtainable:
  the suite substitutes every one of them (R7 counts above) and a real crossing would require a live
  VK session, a CDN and a media payload that the declared prerequisites do not provide. What remains
  verifiable: the substitution counts, the coverage of the bodies behind the boundaries, and the
  consequences cited in TST-001, TST-002, TST-003 and TST-006. Owner of the unverifiable half: the
  boundary's own phase (`05` process/media-tool, `06` credentials, `03` network).
- **R10 — whether a `0o600` mode is actually in force.** Attempted: create a file, `os.chmod` it to
  `0o600`, read the real mode. Why the evidence is unobtainable: on this platform `os.chmod` toggles
  only the read-only attribute, so the probe measured `0o666` regardless of the request. What remains
  verifiable: that the four guards report a skip and never a pass, which is the form this phase files
  (TST-014). Owner of the unverifiable half: `06` for the credential file, `07` for every other
  artefact.
- **R1 — isolation.** Re-running the suite is not a test of isolation, and none of the findings below
  rests on repetition. Isolation was established by R5's variation, not by R1's agreement.

---

---

## Findings — each decision above its finding's retained original text

### TST-001 — validation record

**Decision:** REPRODUCED — the finding stands as filed. | **Original severity:** CRITICAL | **Confirmed severity:** CRITICAL | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `mandatory` (unchanged)

*Validation note — recorded above the field table because the report format has no slot for
it (see the header note).*

The muxer was re-run in this run, not read from the report. `ffmpeg -version` →
`N-117624-g9eb7e8d2a4-20241023`. With a 1-second real `mpeg2video` sample written to a
`.ts`, a response file containing `-i <sample> -c copy <out>`:

| Invocation | returncode | output produced |
|---|---|---|
| `ffmpeg @<argfile>` (what `downloader.py:303` emits) | **4294967274** (`-22`, `EINVAL`) | **no** |
| identical argv with `'@'` stripped | **0** | **yes** — 6919 bytes written |
| `ffmpeg @<file>` whose contents name a valid `lavfi` source | **4294967274** | **no** |

`Unable to choose an output format for '@…'` is the muxer treating the token as a literal
output filename. The report's control returned 2511 bytes and this run's returned 6919
because the source media differs; the shape the report measured is the shape measured here.

The supporting inventory in the finding is exact, not approximate:

- `downloader.py:303` is `cmd: list[str] = ["ffmpeg", f"@{argfile}"]` — confirmed verbatim.
- **42** `patch("asyncio.create_subprocess_exec")` sites in the test tree, **0** unpatched
  (19 in `test_ffmpeg_utils.py`, 23 in `test_hls_downloader.py`). No test in the suite
  spawns a real muxer, so nothing can fail on whether it honours `@`.
- The two real child processes in the whole suite are `tests/test_packaging.py:309`
  (`uv build`) and `tests/test_config.py:427` (an env probe). Neither is a muxer.
- `tests/test_hls_downloader.py:275-288` asserts the argv shape; its final assertion,
  `not argfile_path.exists()`, is satisfied by `_temp_argfile`'s own `finally`
  (`downloader.py:124`, `path.unlink(missing_ok=True)`) and not by the product.
- `tests/test_hls_downloader.py:725-729, 742` and `:787-790` supply a stand-in that opens
  the response file with `split()`, which is the only thing in the tree that ever reads one.
  The finding's line citations (725, 742, 787) are correct.
- The `SEC-001`/`SEC-002` oracles at `test_hls_downloader.py:640` and `:686` assert against
  argv tokens, so the class docstring's "run ffmpeg on the real argv" is not what executes.

**The report's own severity claim is the one that needed checking, and it holds against the
phase's own taxonomy.** `10-audit-test-coverage.md:329` reserves CRITICAL for "a subject a
sibling phase names as its highest-consequence behaviour has no test that can fail on it,
and the consequence is an artefact that is wrong or unsafe". `TRN-001` is phase 05's highest-consequence claim about this transport, and the
consequence it names — the muxer produces no artefact — is observed, not hypothesised. Both
halves of the CRITICAL row are satisfied.

**Cross-references — complement, not merge.** `TRN-001` (phase 05, HIGH, validated) owns
the *product* defect: the transport does not work and the concealment it claims does not
happen. This finding owns the *test* claim: the suite asserts that it does. Same subject,
two owners, two sides. Both are retained and neither absorbs the other; the product fix
belongs to `TRN-001` and is not re-filed here. Also adjacent: `ART-007` (phase 07, HIGH,
mandatory), which measures the `chmod 0o600` on this argfile at `0o666` and explicitly
grounds itself in an `icacls` listing rather than in the suite's mode oracles.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_hls_downloader.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** `HLSDownloader.download_with_ffmpeg` builds its command as
`["ffmpeg", f"@{argfile}"]` (`downloader.py:303`). Three tests assert that this form is what the
product emits, and each is satisfied by the *string*, not by any ffmpeg executing anything:

* `tests/test_hls_downloader.py:275-288` (`test_download_with_ffmpeg_uses_argfile_syntax`) asserts
  `len(captured_args) == 2`, `captured_args[0] == "ffmpeg"`, `captured_args[1].startswith("@")`,
  and `not argfile_path.exists()` after the call. The last one is satisfied because
  `_temp_argfile`'s `finally` unlinks the file (`downloader.py:124`) whether or not anything read it.
* `tests/test_hls_downloader.py:742` asserts `captured_args[0] == "ffmpeg"` and, at `:725`, strips
  the `@` with `args[1][1:]` **in the test's own stand-in** to read the file.
* `tests/test_hls_downloader.py:787` does the same.

The stand-in is the only thing in the whole system that ever reads the argfile. Because all 42
`asyncio.create_subprocess_exec` constructions in the suite are substituted (R7), **no assertion in
the suite can fail on whether the muxer honours `@`**. The suite therefore encodes a broken
convention as a passing, documented guarantee: `tests/test_hls_downloader.py:239` names it in prose
("uses ffmpeg @argfile to hide m3u8 URL and cookies"), and `:640`, `:686` carry it as a security
oracle.

**Evidence вЂ” R3** (`--cov` missing-line set в€© statement ranges parsed with `ast`): `downloader.py:303`
is covered, so the test does reach the body; the gap is the assertion, not the execution.

**Evidence вЂ” own runtime probe** against the installed muxer, decisive control included:

```
A. ffmpeg @<argfile>          returncode: 4294967274   (no output file)
   [... ] Unable to choose an output format for '@C:\...\a.args';
          use a standard extension for the filename or specify the format manually.
          Error opening output file @C:\...\a.args.
B. same argv passed directly  returncode: 0            output produced: True, 2511 bytes
C. @<file> naming valid lavfi returncode: 4294967274   (same literal-@ token error)
```

Control B is the same argument vector without `@`; control C shows the token is consumed as a literal
filename whatever the file contains. The muxer never opens the file.

**Exact consequence:** with `downloader.py:396`, every call to `download_with_ffmpeg` reaches
`if process.returncode != 0:` and returns `None`. The HLS transport the product documents and ships
produces no artefact, and the 498-test suite reports it green. The argument vector itself belongs to
`05` and the file on disk to `07`; this finding is filed only for what the test asserts about them.

**Recommendation:** the test's claim is wrong, not the production code's intent вЂ” per the project's
production-code-is-king rule, fix the test. Add one test that crosses the process boundary for real
for this specific body (ffmpeg is already a declared dependency and is on `PATH`), and demote the
three argv-shape tests to what they actually check: that secrets are absent from `process.argv`.
Assert the ffmpeg outcome, not the argv spelling. Until the transport is exercised end to end, no
test in the suite should carry `SEC-001`/`SEC-002` as satisfied on the argfile path.

---

---

### TST-002 — validation record

**Decision:** REPRODUCED — the finding stands as filed. | **Original severity:** CRITICAL | **Confirmed severity:** CRITICAL | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `mandatory` (unchanged)

*Validation note.*

Reproduced end-to-end through the product's own writer and the test suite's own consumer
harness, changing only the domain shape:

| Input domain | File line written | `jar.load()` result |
|---|---|---|
| `.vkvideo.ru` | `.vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession_id\tabc123` | **OK** — parsed `['session_id']`, sent to `https://vkvideo.ru/` |
| `vkvideo.ru` | `vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession_id\tabc123` | **raises `http.cookiejar.LoadError`** — `invalid Netscape format cookies file …` |

The raise site is the assertion `http/cookiejar.py:2051` (`assert domain_specified ==
initial_dot`) inside `_really_load`, surfaced as the `LoadError` the report names;
`yt_dlp.cookies` defines `class CookieLoadError(YoutubeDLError)`, which is the wrapper the
product's consumer path converts it into. The whole file is refused, not one entry.

**The claim that makes this CRITICAL is confirmed and is the strongest single number in
this report: `src/vkdownloader/services/cookies.py` is at 32 statements with 0 missed —
100 %.** Every line of the serialiser executes in this suite. The defect ships green
because the only consumer oracle in the tree is built from `_DOMAIN = ".vkvideo.ru"`
(`tests/test_cookies.py:25`) and all four round-trip tests route through helpers that
hard-code it.

The finding's "in-tree contradiction" sub-claim is exact:

- `tests/test_extractor.py:227` builds `{"name": "user", "value": "123",
  "domain": "vkvideo.ru"}` — the undotted shape — and asserts at `:234` only
  `"vkvideo.ru" in result`, which is satisfied by the substring alone. Line numbers exact.
- `tests/test_hls_downloader.py:1033` builds `Cookie(name="vk", value="abc123",
  domain="vkvideo.ru", path="/")` and asserts only `cookie_file.exists()`. Line numbers
  exact.

**Cross-reference — complement, not merge.** `SEC-009` (phase 06, HIGH, validated,
`RUNTIME-ERROR`, mandatory) owns the *product* defect: the serialiser writes a constant
`TRUE` into the include-subdomains column regardless of the domain at `cookies.py:78`.
This finding owns the *test* claim: the suite never constructs the shape the product will
meet in the wild. The two are the same mechanism from two owners and are cross-referenced,
not merged; the product fix is `SEC-009`'s.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_cookies.py`, `src/vkdownloader/services/cookies.py` |
| **Classification** | mandatory |

**Description:** `tests/test_cookies.py` is the only module that drives the cookie file through the
real consumer, and its docstring (`:1-15`) states the standard correctly: "Assertions are made against
the jar, never against the file's text: a file that *looks* correct is not evidence that the consumer
accepted it." Its fixture constant defeats that standard anyway. `tests/test_cookies.py:25` declares
`_DOMAIN = ".vkvideo.ru"`, and all four round-trip tests (`:54`, `:79`, `:116`, `:138`) build every
cookie through `_cookie` / `_cookie_without_expiry_key` / `_cookie_with_null_expiry`, each of which
hard-codes `_DOMAIN`. The second input shape a host produces is never constructed.

`services/cookies.py:78` writes the Netscape *include-subdomains* column as the literal `TRUE`,
independent of the domain it just read at `:67`. For a host-only domain the two columns disagree, and
the real consumer refuses the whole file.

**Evidence вЂ” R2:** `services/cookies.py` is **100 % covered, 0 statements missed**. Every line of the
defect executes on every suite run. The instrument cannot see it, because the suite never varies the
input that distinguishes the two shapes.

**Evidence вЂ” own runtime probe**, production writer в†’ real consumer, both shapes:

```
domain='.vkvideo.ru'  file line: b'.vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession_id\tabc123'
  jar.load() ok, parsed={'session_id'}, sent_to_vkvideo={'session_id'}
domain='vkvideo.ru'   file line: b'vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession_id\tabc123'
  jar.load() RAISED http.cookiejar.LoadError: invalid Netscape format cookies file ...
  http/cookiejar.py:2051  assert domain_specified == initial_dot  -> AssertionError
```

End to end through yt-dlp's own entry point (`yt_dlp.cookies.load_cookies`, which wraps `jar.load()`
in `except Exception: raise CookieLoadError`):

```
domain='.vkvideo.ru'   yt_dlp load_cookies(): OK
domain='vkvideo.ru'    yt_dlp load_cookies() RAISED yt_dlp.cookies.CookieLoadError: failed to load cookies
```

**In-tree contradiction that makes the gap unambiguous:** the suite itself constructs the host-only
shape twice and asserts only on the text вЂ” `tests/test_extractor.py:227` (`{"domain": "vkvideo.ru"}`,
inside `test_cookies_to_netscape_preserves_domain`, whose `:234` asserts only `"vkvideo.ru" in result`)
and `tests/test_hls_downloader.py:1033` (`domain="vkvideo.ru"`). Two test modules disagree about the
shape the browser reports; only one of them round-trips through the consumer, and it is the one that
picks the shape the format cannot reject.

**Exact consequence:** `extractor.py:288` obtains cookies from `page.context.cookies()`. When any
returned cookie is host-only, the file written at `ytdlp_downloader.py:304` and passed as
`--cookies` at `:305` is rejected by yt-dlp with `CookieLoadError`, so `--cookie-source browser`
supplies no cookies and the download proceeds unauthenticated. The whole file fails, not one line.
**UNVERIFIED** for the exact domain VK's session cookie carries вЂ” that half needs a live browser,
which the declared prerequisites exclude. The defect in the writer and the blind spot in the test are
both observed; the trigger is not.

**Recommendation:** production code is right, the test is wrong. Add the host-only shape to the
`_cookie()` builders in `tests/test_cookies.py` (a `domain` parameter defaulting to `_DOMAIN`, with
one case per column-agreement shape) so the file is driven through `jar.load()` on both. That single
addition is what would have caught the defect; the docstring's own standard, applied to both shapes,
suffices.

---

### TST-003 — validation record

**Decision:** REPRODUCED — the finding stands as filed. | **Original severity:** CRITICAL | **Confirmed severity:** CRITICAL | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `mandatory` (unchanged)

*Validation note.*

Re-run with nothing patched. 250 real `mpeg2video` `.ts` segments were written into a
`.video_segments` directory, the output path was created as a **directory** so the final
`ffmpeg` genuinely fails to open it, and the product's own `_merge_segments_batched` was
called with `(seg_dir, out, 250, 300.0)`. Every number in the report's evidence block is
the number measured here:

| Measurement | Report | This run |
|---|---|---|
| segments before | 250 | **250** |
| batch merges that succeeded | 3 (0-99, 100-199, 200-249) | **3** — three real `ffmpeg` invocations, no errors |
| return value | `None` | **`None`** |
| original segments surviving | 0 of 250 | **0 of 250** |
| batch temp files surviving | 0 | **0** |
| `final_list.txt` remaining | yes | **yes** |
| output file produced | no | **no** |

`final_merge_failed` was logged by the product with the muxer banner in its `error` field.
The loss mechanism is exactly as filed: `_merge_batch_segments` unlinks each segment as
soon as its batch is merged (`ffmpeg_utils.py:314-316`), and `_merge_segments_batched`'s
`finally` (`ffmpeg_utils.py:511-515`) unlinks every batch temp, so the `finally` reaches
disk and removes the last remaining copy of the data on the failure path as well as on
success.

**The finding's test-inventory claims are exact.** `tests/test_ffmpeg_utils.py:332-351` is
the only failure-path test for `_perform_final_merge`; it writes a single 10-byte
`batch_00000.ts` and asserts `result is False`. The 250-segment test at `:425-435` uses
`batch_size = 5` and the real success path, so the composition the user actually performs —
many segments, batch merges that succeed, one final merge that fails — is never executed.
Per-statement coverage agrees: `ffmpeg_utils.py` is missing `510`, the `return None` the
failure path takes, and no test in the tree reaches it.

**Cross-reference — complement, not merge.** `NET-001` (phase 03, CRITICAL, validated,
`RUNTIME-ERROR`, mandatory) owns the *product* consequence: the resume guarantee cannot
hold across this composition. This finding owns the *test* claim: the suite's tests cannot
detect the composition. Neither absorbs the other.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_ffmpeg_utils.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | mandatory |

**Description:** `_merge_batch_segments` deletes each batch's segment originals as soon as that batch
merges (`ffmpeg_utils.py:314-316`), and `_merge_segments_batched`'s `finally` (`:511-515`) then
deletes every batch temp it created. So a final-merge failure on a video above the 100-segment batch
size leaves nothing to retry from. The suite tests both halves of that chain and never their
composition:

* Success paths over the batch boundary are covered вЂ” `test_ffmpeg_utils.py:433` (250 segments),
  `:532` (150), `test_hls_downloader.py:2622` (`test_merge_segments_batched_uses_batch_size_100`, 250).
* The only final-merge *failure* test is `test_ffmpeg_utils.py:331-351`
  (`test_final_merge_returns_false_on_failure`). It passes **one** temp file, `assert result is False`,
  and asserts nothing about what is on disk. A one-temp-file final merge is not the batched shape
  (`:506` needs `len(temp_files) >= 1`, and the multi-batch case is what leaves zero originals).
* No test drives `_merge_segments_batched` to a failing final merge at all.

**Evidence вЂ” R3** (parsed statement ranges в€© missing lines): the failure branch of `_perform_final_merge`
is only partly executed вЂ” `:352-354` (the timeout path) is missing, `:363-364` executes. The
destructive `finally` at `:511-515` is reached on every `_merge_segments_batched` test and is
therefore *covered* while nothing asserts what it destroyed.

**Evidence вЂ” own runtime probe**, 250 real segment files, batch merges succeeding and the final merge
forced to fail:

```
segments before        : 250
ffmpeg invocations     : 4 (rc values: [0, 0, 0, 1])
_merge_segments_batched: None
original .ts survivors : 0 of 250
batch temps survivors  : []
final_list.txt present : True
output file produced   : False
```

**Exact consequence:** 0 of 250 originals survive. `segment_downloader.py:617-618` calls
`_cleanup_segments` only on success, but by then the directory holds only `final_list.txt`. The
documented resume guarantee вЂ” asserted for the playlist-fetch failure
(`test_hls_downloader.py:295-321`) and the segment-download failure (`:324-354`) вЂ” is not asserted for
the third failure mode, the only one that destroys the input. A user who hits a final-merge failure
must re-download every segment from the CDN.

**Recommendation:** add one test that builds more than 100 segments, forces the final merge to fail,
and asserts the state of the directory afterwards. If the intended guarantee is "a failed final merge
keeps its inputs", the test will fail against current production code and the fix belongs in
`ffmpeg_utils.py:314-316`/`511-515`; if the guarantee is "a failed merge is unrecoverable", the
docstring for `_merge_segments_batched` must say so, because the resume tests imply the opposite.
Either way the assertion has to exist before the behaviour is claimed.

---

---

### TST-004 — validation record

**Decision:** REPRODUCED, with one correction that changes the recommendation. RECLASSIFIED `advisory` → `mandatory`. | **Original severity:** HIGH | **Confirmed severity:** HIGH | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `mandatory` (reclassified)

*Validation note.*

Everything structural in the finding is confirmed exactly. `security.py:59-62`:

```python
59:    resolved = path.resolve()
60:    if ".." in resolved.parts:
61:        raise ValueError(f"Path traversal detected: {path}")
62:        logger.warning("output_path_traversal_detected", path=str(path))
```

Per-statement coverage for `src/vkdownloader/utils/security.py` in this run is 4/4
statements covered and **exactly `60, 61, 62` missing** — the guard the finding names,
never executed, while the pre-resolution guard at `:52-56` is fully covered.

The finding's characterisation of the test is verbatim correct:
`tests/test_security.py:195-209` — the function's own docstring says "resolve() removes
them lexically, then checks again" and the test's name is
`test_validate_output_path_rejects_traversal_even_if_resolved`; its comments at `:199` and
`:205` say the opposite ("resolved through Path.resolve().* as a pre-resolution check", "the
rejection reason is the same either way"); and its assertion at `:208` is
`"traversal" in str(exc_info.value)`, a substring both guards produce. Every path that
reaches line 59 is filtered by lines 52-56 first, so line 59 is only ever reached by
inputs that cannot produce line 60. `tests/test_security.py:183-191` cannot be made to
reach it either, for the reason measured next.

**Correction — the finding's first recommendation is not executable on this platform, and
the fix has to be the second one.** The finding offers "build a real post-resolution case —
a path whose `str()` is clean but whose resolved form carries `..`". Five constructions were
tried and `..` never survives `Path.resolve()`:

| Construction | `str(path)` | `str(path.resolve())` | `'..' in str(resolved)` |
|---|---|---|---|
| `symlink -> real/..`, then `link/x` | — | — | **symlink creation unavailable** (needs elevation) |
| symlink loop `a -> b -> a`, then `a/x` | — | — | **symlink creation unavailable** |
| plain lexical `a/../b` | `a\..\b` | normalised, no `..` | **False** |
| `\\?\C:\a\..\b` | `\\?\C:\a\..\b` | normalised, no `..` | **False** |
| drive-relative `C:a\..\b` | `C:a\..\b` | normalised, no `..` | **False** |

Two consequences. First, the first recommendation cannot be carried out on the declared
development platform, so the actionable fix is the one the finding also offers: rename the
test to what it asserts, move the two comments onto the correct guard, and say plainly in
the class docstring that the post-resolution guard has no oracle here. Second, and outside
this phase's ownership, the measurement is evidence for phase 06's `SEC-006` (whether the
`resolve()` guard is needed at all) — it is a defence-in-depth line that no construction
reachable on Windows or POSIX-without-elevation can trip.

**Why the classification is raised.** The finding is not "a test is missing"; it is a test
that **asserts coverage of a security guard it never reaches**, in a class whose docstring
is the only documentation of what is covered. The report template's guide puts security and
correctness in `mandatory`. The consequence is small today because the guard is
unreachable, and the reclassification is what keeps that from being the reason it is
ignored. **Cross-reference:** `SEC-006` (phase 06) owns the guard's necessity; it is not
re-filed here.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_security.py`, `src/vkdownloader/utils/security.py` |
| **Classification** | advisory |

**Description:** `tests/test_security.py:154-161` is a class whose docstring is specifically about the
post-resolution half of the traversal guard: "SEC-006: The pre-resolution `..` check is a no-op for
paths that callers already resolve. The fix adds a post-resolution check too." Its last test,
`test_validate_output_path_rejects_traversal_even_if_resolved` (`:195-209`), is named and documented
as verifying that post-resolution guard. It does not:

```python
path = Path("/safe/base") / ".." / "etc"        # :204  str(path) still contains ".."
# :205  # path.resolve() will resolve this to /etc (no ".."), but str(path) has ".."
# :206  # The pre-resolution check catches it. For the post-resolution check,
# :207  # we verify that a path object with ".." in its string form is rejected:
```

The test's own comments (`:205-207`) say the **pre**-resolution guard at `security.py:47-50` fires.
Its docstring (`:196-201`) says it verifies the **post**-resolution guard. The test asserts
`pytest.raises(DownloadError, match="Path traversal detected")` вЂ” a message both guards produce
verbatim, so it cannot distinguish them.

**Evidence вЂ” R2/R3** (missing-line set в€© the parsed range of `validate_output_path`):
`utils/security.py` reports missing `60, 61, 62`. Line `59` (`if ".." in str(resolved):`) is
evaluated on every call; the body that raises вЂ” `60`, `61`, `62` вЂ” **never executes in any of the
502-test run**. The guard the class exists to protect is untested.

**Exact consequence:** a reviewer reading the class docstring and the test name concludes the
post-resolution guard is covered. It is not. If that body were deleted, the suite stays green; if it
is load-bearing for callers that pass an already-resolved path (`security.py:102` does, via
`_resolve_output_file`), nothing in the suite would notice.

**Recommendation:** the two comments at `:205-207` are the honest description of what the test does.
Either build a real post-resolution case вЂ” a path whose `str()` is clean but whose resolved form
carries `..`, which needs a symlink or a UNC edge вЂ” and rename the test to match, or split it into two
tests with the pre-resolution one named for what it actually covers. Do not leave the docstring
claiming the second.

---

### TST-005 — validation record

**Decision:** REPRODUCED, with one corrected anchor. RECLASSIFIED `BEST-PRACTICE` → `SPEC-DEVIATION` and `advisory` → `mandatory`. | **Original severity:** HIGH | **Confirmed severity:** HIGH | **Type:** `SPEC-DEVIATION` (reclassified) | **Classification:** `mandatory` (reclassified)

*Validation note.*

The claim reproduces; one line citation is wrong and is corrected here. The report cites
`packaging-check.yml:44` in this finding and in R14. **Line 44 is `with:` under the
"Install uv" step.** The pytest invocation is at **`packaging-check.yml:53`**:

```yaml
52:      - name: Build artefacts and assert they match the manifest
53:        run: uv run pytest tests/test_packaging.py -v
```

Everything else in the finding is confirmed. `doc-lint.yml` runs a single
`grep -rlaP '\x00' docs/` and nothing else. `tests/test_packaging.py` collects 14 tests of
502. The only two real child processes in the entire suite are `test_packaging.py:309`
(`uv build`) and `test_config.py:427` (an env probe) — so the empirical claim that nothing
crosses a real boundary is right, and it is a property of the suite as it stands rather
than a gap in the census. No coverage measurement is declared anywhere: no `pytest-cov`
entry in `[dependency-groups] dev` (`pyproject.toml:111-115`), proved directly by
`uv run pytest --no-cov` failing with `pytest: error: unrecognized arguments: --no-cov`.

**Why the type is corrected.** `.ai/context/commands.md:15` declares `uv run pytest <path>`
as the project's Run-tests command, and `docs/01-tools/installation.md:91` documents
`uv run pytest tests/` as the development workflow — the full suite. A CI job that invokes
one module of twenty-one contradicts the project's own declared rule, and
`10-audit-test-coverage.md:336` defines `SPEC-DEVIATION` as "a test or configuration that
contradicts the project's own declared rule". `BEST-PRACTICE` requires "a defensible
arrangement with a demonstrated gap"; a gate that admits `tests/**` and runs under 3 % of
the tree is not a defensible arrangement, it is a divergence between what the project says
it verifies and what it actually verifies.

**Why the classification is raised.** The absence is what makes every other gap in this
report permanent: 239 missed statements, three CRITICAL oracles that cannot fail, and a
19-test boundary-free suite are all invisible to CI. The same subject is filed by phase 11
as `DEP-002` at `SPEC-DEVIATION` / `mandatory`; the two classifications are now consistent
and the shared remediation is tracked once in `VAL-125`.

**Cross-phase handling.** `DEP-001` (phase 11) covers the absent lint / format / typecheck
jobs; the finding correctly declines to restate it. `DEP-002` covers the same
full-suite step; see `VAL-125` for the merge candidate and the insertion-point collision.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.github/workflows/packaging-check.yml`, `.github/workflows/doc-lint.yml`, `pyproject.toml` |
| **Classification** | advisory |

**Description:** The repository has two workflow definitions. `doc-lint.yml` greps `docs/` for NUL
bytes and touches nothing else. `packaging-check.yml` is the only job that executes tests, and its
single command is `uv run pytest tests/test_packaging.py -v` (`:44`). That is 14 of the 502 collected
tests. The other 19 modules вЂ” including every test named in TST-001 through TST-004 and TST-006 вЂ”
have no execution outside the developer's own machine.

The gate is also correctly scoped in one respect and that is worth preserving: its path filter is
derived from the sdist allow-list, so `tests/**` does fire it. It simply does not run what lives
there.

**Evidence вЂ” R13** (both workflow files read in full): workflow count 2; commands run:
`uv sync --locked`, `uv run pytest tests/test_packaging.py -v`, and a `grep -rlaP '\x00' docs/`.
Present: test execution (partial). Absent: lint, format check, type check, dependency scan, secret
scan, lockfile check, build-and-publish. No coverage measurement is declared anywhere вЂ” neither in
the workflows nor in `pyproject.toml` (R11 found no `[tool.pytest.ini_options]` table, and no
`pytest-cov` entry in `[dependency-groups] dev`).

**Exact consequence:** the ranked coverage gaps in this report are not gated by anything. A regression
that removes an oracle, or reintroduces the argfile and cookie defects, is invisible to every party
except the developer who happens to run `pytest`. This is the "the ordered list is non-empty and
nothing in the repository gates it" finding from block (a): the 89 % figure is descriptive, and the
39 % of bodies that never execute in the highest-risk modules are not a control that anything enforces.

**Recommendation:** add a workflow that runs `uv run pytest tests` on `src/**` and `tests/**` changes.
Everything else вЂ” declaring a coverage tool, a threshold, a lint job вЂ” is `11`'s to add, and this
finding prescribes none of it. The single highest-value change is the one-command full-suite job.

---

---

### TST-006 — validation record

**Decision:** REPRODUCED, with two under-count corrections. | **Original severity:** HIGH | **Confirmed severity:** HIGH | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `mandatory` (unchanged)

*Validation note.*

The central claim is confirmed and is the one that matters: **`aiohttp` appears zero times
in the test tree.** A search of every `tests/**/*.py` for `aiohttp`, `ClientSession`,
`ClientTimeout`, `TCPConnector`, `CERT_NONE` and `_create_connector` returns 0 matches, so
no test in the suite enters `segment_downloader.py`'s aiohttp code at all. That is not a
manner of speech: it is the reason 67 of the module's 302 statements never execute.

Per-statement coverage for `src/vkdownloader/services/segment_downloader.py` in this run
is **302 statements, 67 missed, 77.8 %**, and every one of the ranges the finding names is
present in the missed set:

| Finding's claim | Missing lines measured |
|---|---|
| `_fetch_playlist_with_retry:234-244` | 234-244, all 11 |
| `_retry_429_with_backoff:267-269` | 267-269, all 3 |
| `_create_connector:301-303, 539-543` | 301-303 and 539-543, all 8 |
| `_await_and_cancel:562-570` | 562, 564, 565, 566, 568, 569, 570 (563, the `except` clause itself, is covered) |
| `_check_merge_space:456-463` | 456-463, all 8 |
| `downloader_throttle.py:296-299` (`_parse_retry_after`'s HTTP-date branch) | 296-299, all 4 |

**Correction 1 — one range is over-stated.** The finding says "`_clear_stale_segments:
120-128` loses 3 of 9". The missed set for the module is `[120, 126, 127, 128]` in that
region, so `121`–`125` execute; the true figure is 4 of 9, not 3 of 9. The direction of
the claim — that the function is only partly exercised — is unchanged, and the function
name in the finding points at the right function.

**Correction 2 — an under-count that strengthens the claim.** The finding says
`tests/test_segment_downloader.py` "passes a bare `MagicMock()` as the session" and cites
`:49`, `:158`, `:208`. There are **five**, at `:49`, `:108`, `:158`, `:208`, `:257`. The
file is 281 lines and collects 5 tests. The finding's three citations are the first three
of the five, so it under-reports; every one of the five is a `MagicMock()` where an
`aiohttp.ClientSession` is expected, which is a stronger statement of the same point.

The `downloader_throttle.py` claim is separately confirmed and separately calibrated:
`_parse_retry_after` **is** referenced 6 times and `Retry-After` 10 times in the test tree,
and the integer-seconds branch is covered — the missing lines are exactly the four of the
HTTP-date branch. The finding's wording is correct here ("the whole `Retry-After` HTTP-date
branch") and the phase-10 inventory claim of "0 references" applies to aiohttp, not to
this function. Nothing to correct.

**Why HIGH stands.** The phase's own table (`10-audit-test-coverage.md:330`) has no row
for a bare unclaimed coverage gap, and the finding is filed at HIGH on a reading of
"A body is claimed by a test and never executed" where `tests/test_segment_downloader.py`
is the module's only test. The row below it — MEDIUM — is occupied by *arrangements*
(a compared value the test itself configured, shared setup, an undeclared framework
default, an untracked artefact), none of which applies. The finding's own ranking table
assigns the highest consequence class (`C=3`) to the TLS switch at `:539-543` and to the
cancellation body at `:562-570`, and both of those are a sibling phase's highest-consequence
behaviour: `SEC-` on the credentials side and `CON-001` (CRITICAL) on the cancellation side.
CRITICAL is unavailable only because no wrong artefact was observed — the consequence is a
hypothetical regression, which the taxonomy explicitly requires to be filed without an
observed severity. **Cross-references:** `CON-001` and `SEC-009` are the owning product
claims; neither is re-filed here.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_segment_downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory |

**Description:** `aiohttp` is a declared runtime dependency and is used in exactly two modules.
Searching the whole test tree (excluding worktree directories) for `aiohttp`, `ClientSession`,
`ClientTimeout`, `TCPConnector`, `ssl.`, `CERT_NONE` and `_create_connector` returns **0 matches for
every pattern**. Not one test constructs, names, or stubs an HTTP client.

`tests/test_segment_downloader.py` is 281 lines and 5 tests, all for `_fetch_playlist_with_retry`, and
even those pass a bare `MagicMock()` as the session (`:49`, `:158`, `:208`). The module under them is
302 statements.

**Evidence вЂ” R2/R3** (`--cov` missing set в€© ranges parsed with `ast`):

* `services/segment_downloader.py` вЂ” 302 statements, **67 missed (77.8 %)**. Unreachable in the run:
  `_create_connector:539-543` (the entire `ssl.CERT_NONE` branch and the
  `ssl_verification_disabled` warning), `_await_and_cancel:562-570` (the whole cancellation body:
  `task.cancel()`, `asyncio.gather(..., return_exceptions=True)`, the `download_cancelled` log),
  `_run_parallel_download_with_backoff:234-244`, `_check_backoff_before_attempt:267-269`,
  `_try_single_download_attempt:301-303` (the `aiohttp.ClientError` handler),
  `_fetch_single_playlist:456-463` (every line of the real `session.get` call and its
  `aiohttp.ClientError` handler), `_refresh_token_and_retry:440-446`,
  `_download_segment_concurrent:677, 681, 715, 720` (four `raise asyncio.CancelledError` sites),
  `_create_segment_download_tasks:746-747`, `_clear_stale_segments:120-128`.
* `services/downloader_throttle.py` вЂ” 129 statements, 13 missed. `_retry_429_with_backoff:209-253`
  loses 7 lines and `_parse_retry_after:296-299` loses 4 вЂ” the whole `Retry-After` **HTTP-date** branch
  (`datetime.now(UTC)`, the `delta > 0` comparison, the return).
* `signal_handlers.py:52-54` and `:77-82` вЂ” see TST-012.

**Exact consequence:** none of the 502 passing tests can fail on a regression in the retry ladder, the
token-refresh handoff, the TLS-verification switch, the `Retry-After` date parser, or the cancellation
cleanup. A change that makes a cancelled download leak its tasks, or that silently disables
certificate verification when `ssl_verify=false`, or that mis-parses an HTTP-date `Retry-After`,
produces a green run. The `aiohttp.ClientError` handlers are the only thing standing between a
transient network fault and a failed download, and they have never run.

**Recommendation:** this is a coverage gap, not a production defect вЂ” the bodies are not shown to be
wrong here. Start with `_create_connector` (5 statements, one setting, and a security-relevant
switch), then `_await_and_cancel`, then `_parse_retry_after`'s date branch. Each needs a test that
supplies a real `aiohttp.ClientSession` against a local HTTP server; that harness does not exist yet
and building it is the real cost, not the individual tests.

---

---

### TST-007 — validation record

**Decision:** REPRODUCED — the finding stands as filed. | **Original severity:** HIGH | **Confirmed severity:** HIGH | **Type:** `BEST-PRACTICE` (unchanged) | **Classification:** `advisory` (unchanged)

*Validation note.*

Every count in this finding was re-measured and every one is exact. This is the
best-evidenced finding in the report and it needs no correction.

| Claim | Measured |
|---|---|
| 5 sites replace the **process-global** primitive | **5** — `test_extractor.py:161` (`patch("asyncio.wait_for")`) and `:162` (`patch("asyncio.get_running_loop")`), `test_hls_downloader.py:1477`, `:1549`, `:1629` |
| 14 sites replace the **subject itself** | **14** — `download_hls_with_resume` ×7 (`test_downloader.py:279, 325, 377, 447, 528, 572`; `test_hls_downloader.py:1958`) and `HLSDownloader.download_with_ffmpeg` ×7 (`test_downloader.py:274, 320, 372, 442, 524`; `test_hls_downloader.py:1954, 3254`) |
| 24 sites replace `cli.Settings` with a `MagicMock` | **24** — the 25th textual match in `test_cli.py` is the docstring at `:1473` stating the class does *not* patch it |
| counter-measure class at `test_cli.py:1465-1473` | confirmed present |
| the 8 in-repo `asyncio.wait_for` call sites become the stand-in | all 8 at the exact lines given: `infrastructure/browser.py:77, 87`; `ffmpeg_utils.py:200, 238`; `segment_downloader.py:719`; `downloader_throttle.py:72, 365` |
| `_merge_segments_batched` patched at `test_hls_downloader.py:1201, 1250, 1310, 1461, 1551, 1613, 1727` | confirmed, each with a paired `_fetch_playlist_with_retry` patch at `1193, 1242, 1302, 1453, 1519, 1605, 1708` — so `download_hls_with_resume` is exercised with both of its outcomes supplied and both of its I/O boundaries substituted |

**The counter-example the finding points at is the finding's own best evidence, and it is
confirmed verbatim.** `tests/test_downloader_throttle.py:522`, `:626` and `:642` patch
`"vkdownloader.services.downloader_throttle.asyncio.wait_for"` — the module attribute,
through the importing module — and get exactly the same isolation. One of those sites
(`:522`) sits in the *same file* as the 24 `cli.Settings` patches, on the same
function-scoped-fixture model, with a class docstring saying why. The defect is a missing
convention, not a missing capability.

**Why BEST-PRACTICE / advisory is right and is not raised.** The phase's own table
(`10-audit-test-coverage.md:336`) defines `BEST-PRACTICE` as "a defensible arrangement
with a demonstrated gap" and the template's advisory row as "code quality improvements,
refactoring suggestions, best practice enhancements" — a direct match. The gap is
demonstrated (five process-global substitutions), the arrangement is otherwise sound, and
no behaviour is asserted falsely. That is the definition, and this run does not inflate it
past the definition. **No `RUNTIME-ERROR` reclassification is available or appropriate
here**: nothing was observed failing, which is why the report is right to record this as a
count rather than as an observation.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-007 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_extractor.py`, `tests/test_hls_downloader.py`, `tests/test_cli.py` |
| **Classification** | advisory |

**Description:** R8 resolved every `patch()` first argument to a dotted name (426 sites) and assigned
each to one of four classes. Three classes disqualify the substitution.

**The subject itself** вЂ” 14 sites: `vkdownloader.services.downloader.download_hls_with_resume` (7) and
`vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg` (7). A test that replaces the
body it is named for cannot fail on it. This is the mechanical reason TST-001 and TST-003 could not
have been caught: `test_hls_downloader.py:1201, 1250, 1310, 1461, 1551, 1613, 1727` all patch
`_merge_segments_batched`, and `:1201` et al. also patch `_fetch_playlist_with_retry`, so
`download_hls_with_resume` is exercised with both of its outcomes supplied.

**A scheduling primitive the runtime uses** вЂ” 5 sites, and these are the process-global stdlib names,
not module attributes:

* `tests/test_extractor.py:161` `patch("asyncio.wait_for", side_effect=fake_wait_for)` and
  `:162` `patch("asyncio.get_running_loop")` (bare stdlib paths).
* `tests/test_hls_downloader.py:1477, 1549, 1629` `patch("asyncio.wait_for", side_effect=mock_wait_for)`.

For the duration of those tests, every `asyncio.wait_for` in the process is the stand-in вЂ” including
the ones in `infrastructure/browser.py:77, 87`, `services/ffmpeg_utils.py:200, 238`,
`services/segment_downloader.py:719` and `services/downloader_throttle.py:72, 365`, none of which
those tests are about. `get_running_loop` is replaced with a bare `MagicMock` at
`test_extractor.py:162`, so any code under test that reads loop properties reads a mock.

**A production model whose validation is the subject** вЂ” 24 sites patching
`vkdownloader.cli.Settings` with a `MagicMock` (`test_cli.py:120, 147, 176, 258, 305, 349, 395, 450,
515, 565, 598, 631, 663, 716, 757, 802, 875, 941, 992, 1045, 1088, 1138, 1429, 1458`). Pydantic
validation, defaults and coercions are not exercised in any of them.

**Counter-argument, recorded because it is real:** `tests/test_cli.py:1465-1473` documents a class
(`TestEntryPointSourcePrecedence`) that deliberately does *not* patch `cli.Settings` so the `.env`
file and the variables are exercised end to end. The mitigation exists. It covers 4 of 24 sites.

**Evidence вЂ” R8/R9:** no exact leaf-name self-substitution was found (a test never patches a symbol it
also imports by that exact name). The disqualifying sites are the ones above. Two self-confirming
classes are present and are filed under (e): read-backs of a stand-in's own call record
(`test_security.py:75` `call_kwargs = mock_logger.warning.call_args[1]`, then `:76-77` assert on
those kwargs) and values the test configured into a stand-in (the 24 `MagicMock` settings objects,
whose `max_concurrent_downloads=4` and `log_file=None` are both the input and the expectation).

**Exact consequence:** with the subject replaced there is no oracle on it, so no change to
`download_hls_with_resume` or `download_with_ffmpeg` can be detected by the tests named after them вЂ”
which is precisely the mechanism by which TST-001 and TST-003 shipped. With `asyncio.wait_for`
replaced process-wide, a change in how any *unrelated* body sequences its subprocess teardown would
be invisible in exactly the tests that were supposed to catch it.

**Recommendation:** patch the module attribute (`vkdownloader.services.downloader_throttle.asyncio.wait_for`,
as `tests/test_downloader_throttle.py:522, 626, 642` already do correctly in the same codebase) rather
than the stdlib name, and never patch `get_running_loop` when the body under test only calls it. For
the CLI tests, keep `Settings` real and vary the environment instead вЂ” `tests/test_config.py:383-460`
already shows the pattern that makes that work.

---

### TST-008 — validation record

**Decision:** REPRODUCED, with one corrected line citation. | **Original severity:** HIGH | **Confirmed severity:** HIGH | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `advisory` (unchanged)

*Validation note.*

The gap is confirmed and is larger than the finding states. Per-statement coverage for
`src/vkdownloader/cli.py` in this run, measured **on the working tree**:

```
missing: 123, 207, 219, 220, 247, 258, 259, 260, 261, 262, 263, 264, 265, 266, 379, 383
```

`258-266` is exactly the `except (VideoNotFoundError, ...)` arm plus the bare
`except Exception` fallback, nine consecutive lines, never executed. `cli.py:123` is also
missing — that is `TST-014`'s anchor and is decided separately. Everything the finding says
about the surrounding structure is confirmed by reading the file: `_resolve_cookies` is
called at `cli.py:157` with **no** `try`/`except` around it, so both exception types can
only surface at the command tail, and `log_path` is initialised at `:154` and only bound
at `:261`, so the `UnboundLocalError` branch is reachable.

`tests/test_cli.py` collects **exactly 50 tests** — the finding's figure is exact.

**Correction — one line citation.** The finding says "`tests/test_cli.py:941` sets
`mock_selector.select.side_effect = QualityNotAvailableError(...)`". Line 941 is
`with patch("vkdownloader.cli.Settings") as mock_settings_cls:`. The side-effect assignment
is at **`test_cli.py:935`**:

```python
935:    mock_selector.select.side_effect = QualityNotAvailableError(
```

The finding's inference is unaffected: `youtube_client.py:522-523, 529` raises
`QualityNotAvailableError` and no CLI test sets it on the selector, so `cli.py:262-263`
is unreachable in the suite. Per-statement coverage agrees independently —
`src/vkdownloader/services/youtube_client.py` is missing `522`, `523` and `529`.

**Both-tree check, as required by this run's tree state.** `src/vkdownloader/cli.py` and
`src/vkdownloader/config.py` carry uncommitted edits from a concurrent agent; `HEAD` is
`a335b2a`. The two trees differ only in `cli.py`'s preamble region, so this finding's
anchor is stated twice and **both are measured**: the working tree's `258-266` is the
`except` arm, and `git show HEAD:src/vkdownloader/cli.py` places the identical arm at
**`240-248`** (`raise typer.Exit(1)` at `246`, the `except Exception` fallback at `247-248`,
`logger.exception` at `248`). The arm is dead on both trees; only the line number moves.

**Why HIGH stands.** `10-audit-test-coverage.md:330` reserves HIGH for "a body is claimed by
a test and never executed". A 50-test `CliRunner` suite drives the `download` command
end-to-end; the command's entire failure surface executes no assertion. The gap is also the
cheapest in the report to close — `test_cli.py:935` is the exact pattern to copy, the
module-level `logger` is a real structlog logger rather than a stand-in, and the finding's
own recommendation is a six-line test.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-008 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_cli.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `tests/test_cli.py` has 50 tests that drive the Typer app through `CliRunner`, and
they cover the success path thoroughly. None of them reaches the command's failure surface. Working
tree lines (`cli.py` is uncommitted; the tail is identical at `HEAD`):

* `cli.py:258-260` вЂ” `except VideoNotFoundError:` в†’ `"Video not found. Verify the URL is correct and
  the video is public."` в†’ `raise typer.Exit(code=1)`. **Not reached.** A 404 from VK вЂ” the single
  most common user error for this product вЂ” has no executing oracle.
* `cli.py:263-266` вЂ” the generic `except Exception:` that logs `download_failed` with a sanitised URL
  and exits 1. **Not reached.**
* `cli.py:219-220` вЂ” `"Download failed"` / `typer.Exit(code=1)` on the download-exception path. **Not
  reached.**
* `cli.py:379` вЂ” `app()` under `if __name__ == "__main__"`. **Not reached.**

**Evidence вЂ” R2/R3:** `cli.py` reports missing `123, 207, 219, 220, 247, 258, 259, 260, 261, 262,
263, 264, 265, 266, 379, 383`. The nine consecutive lines `258-266` are one `try/except` arm.

**Exact consequence:** the exit code the CLI returns for a missing video, and the message it prints,
are unverified. `tests/test_cli.py:941` sets `mock_selector.select.side_effect =
QualityNotAvailableError(...)` and that arm *is* covered вЂ” so the suite has demonstrated the pattern
and simply did not apply it to `VideoNotFoundError` or to the generic handler. A change to either
message, or to the exit code, ships untested.

**Recommendation:** two `CliRunner` tests вЂ” `side_effect=VideoNotFoundError(...)` and
`side_effect=RuntimeError(...)` on `vkdownloader.cli.perform_download` вЂ” assert the printed text and
the exit code. The machinery already exists in the same file.

---

---

### TST-009 — validation record

**Decision:** REPRODUCED — the finding stands as filed. The **non-reproduction it records is rejected**: it measured a different invocation path from the one the sibling finding names, and the sibling finding survives. | **Original severity:** MEDIUM | **Confirmed severity:** MEDIUM | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `advisory` (unchanged)

*Validation note — this decision also settles the report's first recorded non-reproduction.*

**The tautology, confirmed.** `tests/test_config.py:312` is

```python
assert "Did you mean" in formatted or "Valid fields" in formatted
```

`config.py:227-243` emits `"Did you mean: …"` on one branch and `"Valid fields are: …"` on
the other, on mutually exclusive conditions, so for the input the test actually constructs
the disjunction is true by construction. The test cannot fail for a wrong suggestion. The
finding's other claims are exact as well: `:308` exercises the constructor-keyword path
(`Settings(maxretries="9")`), and `config.py:211` takes
`prefix + loc.lower().replace(".", "_")` — which is why the constructor path works and the
environment-file path does not (see the adjudication below).

**The 25-misspelling probe reproduces exactly, row for row.** Driven through
`Settings(**{bad: "1"})` and `format_validation_error`, all 25 misspellings took the
`Did you mean` branch, every suggested name was a member of `Settings.model_fields` — **0 of
25** produced a name absent from it — and the three examples the finding cites as evidence
of *semantic* mismatch reproduce verbatim: `quality` → `VKDOWNLOADER_USER_AGENT`,
`qualities` → `VKDOWNLOADER_MAX_RETRIES`, `timeout` → `VKDOWNLOADER_TIMEZONE`.

**The adjudication: `CFG-003` survives and the phase-10 non-reproduction does not.** The
two measurements are of *different surfaces*, and which surface is decided by which
invocation the misspellings were typed into:

| Path | Misspelling | `loc` | Suggestion | Semantically right? |
|---|---|---|---|---|
| constructor kwargs (phase 10's 25) | `maxretries` | `maxretries` | `VKDOWNLOADER_MAX_RETRIES` | **yes** |
| **environment file** (phase 02's 19) | `VKDOWNLOADER_MAXRETRIES` | `vkdownloader_maxretries` | `VKDOWNLOADER_DOWNLOAD_TIMEOUT` | **no** |
| constructor kwargs (phase 10's 25) | `downloaddir` | `downloaddir` | `VKDOWNLOADER_DOWNLOAD_DIR` | **yes** |
| **environment file** (phase 02's 19) | `VKDOWNLOADER_DOWNLAOD_DIR` | `vkdownloader_downlaod_dir` | `VKDOWNLOADER_DOWNLOAD_DIR` | **no** |
| **environment file** | `VKDOWNLOADER_DOWNLAOD_TIMEOUT` | `vkdownloader_downlaod_timeout` | `VKDOWNLOADER_DOWNLOAD_DIR` | **no** |
| **environment file** | `VKDOWNLOADER_LOG_LVL` | `vkdownloader_log_lvl` | `VKDOWNLOADER_DOWNLOAD_DIR` | **no** |

The same ten misspelled names were then driven through **both** paths to remove the list
from the comparison. The constructor path returned a semantically correct suggestion for
10 of 10; the environment-file path returned a wrong one for 8 of 10 — the five distinct
dominating neighbours are `VKDOWNLOADER_DOWNLOAD_DIR` and
`VKDOWNLOADER_DOWNLOAD_TIMEOUT`. `tests/test_config.py:304-312` is a constructor-keyword
test, and the phase-02 validator's explanation of why the suite misses the defect is
correct and is confirmed here: the two namespaces coincide on the constructor path
(`"maxretries"` and `"vkdownloader_maxretries"` yield the same three nearest names) and
diverge on the file path.

`CFG-003` (phase 02, MEDIUM, `SPEC-DEVIATION`, mandatory, validated) therefore stands with
its measured 12-of-19. This report's "0 of 25 names outside `Settings.model_fields`" is
also **structurally incapable of being anything else** — the suggestion is built from
`Settings.model_fields` by `config.py:211-216`, so it is a member of that set by
construction. The two numbers are not in conflict: one measures *syntactic validity* and
the other *semantic correctness*, and only the second is the defect. The claim as worded in
this report — "not reproduced by **this phase's measurement**" — is literally true and
carries no contradiction, but it records the wrong surface and therefore cannot be acted
on by a reader of the two reports side by side. That is the defect in the non-reproduction
record, and it is the reason a cross-reference is written here.

**This is a complement, not a conflict, and no `VAL-` is minted.** `CFG-003` owns the
product behaviour (the suggestion is built from the wrong namespace on the environment-file
path); `TST-009` owns the test (the only renderer oracle is a disjunction over a
constructor-path input). Both are retained. The phase-10 recommendation is right and is the
one that lands: add a case that drives the environment-file path — `maxretries` must
suggest `VKDOWNLOADER_MAX_RETRIES` — which the existing assertion cannot fail and the
product cannot currently pass.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-009 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_config.py` |
| **Classification** | advisory |

**Description:** `tests/test_config.py:304-312` is the only test on `format_validation_error`'s
suggestion behaviour. Its final line is a disjunction:

```python
assert "Did you mean" in formatted or "Valid fields" in formatted   # :312
```

`config.py:226-232` emits **exactly one** of those two strings, on mutually exclusive branches: the
first when `difflib.get_close_matches` returns a candidate (`:227-230`), the second when it does not
(`:231-232`). The assertion is therefore true for every input the function can receive. Nothing in the test constrains *which*
name is suggested.

**Evidence вЂ” own runtime probe** over 25 misspellings: every row took the "Did you mean" branch, so
the second disjunct is never even the relevant one; and every suggested name was a member of
`_build_valid_env_vars()`. Examples of the suggestion's *usefulness* (a different question, owned by
`02`): `quality` в†’ `VKDOWNLOADER_USER_AGENT`, `qualities` в†’ `VKDOWNLOADER_MAX_RETRIES`,
`timeout` в†’ `VKDOWNLOADER_TIMEZONE`.

**Non-reproduction, recorded with exact inputs:** on the 25 misspellings above, the suggestion is
**always a syntactically valid variable name** вЂ” 0 of 25 produced a name absent from
`Settings.model_fields`. The claim that the suggestion is *wrong* in 12 of 19 cases is **not
reproduced by this phase's measurement**; the semantic mismatch above is the only defect the probe
observed, and whether it is a defect is `02`'s to decide. What is observed here, without inheritance,
is that the test is structurally incapable of catching either a wrong name or a missing branch.

**Exact consequence:** a change to the cutoff (`0.3` at `config.py:227`), to `n=1`, or to the branch
structure would leave this test green. The test's own docstring (`:305`) promises "Should suggest the
correct field name" вЂ” the assertion does not check that.

**Recommendation:** split the disjunction. Assert `f"Did you mean: VKDOWNLOADER_{expected_field}?" in
formatted` for a parametrised set of known typos, and a separate test that the "Valid fields" branch
is reached for an input far from every field name. That is two assertions instead of one tautology,
and it is what the docstring already describes.

---

---

### TST-010 — validation record

**Decision:** REPRODUCED — the finding stands as filed. | **Original severity:** MEDIUM | **Confirmed severity:** MEDIUM | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `advisory` (unchanged)

*Validation note.*

Confirmed by absence, which is the strongest form available for this claim. The repository
contains no `pytest.ini`, no `tox.ini` and no `setup.cfg`. `pyproject.toml` has no
`[tool.pytest.ini_options]` table — its only tables are `[tool.hatch.build.targets.wheel]`,
`[tool.hatch.build.targets.sdist]`, `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.isort]`,
`[tool.mypy]` and `[[tool.mypy.overrides]]`. The suite's `asyncio` mode, root directory and
collection root are all implicit; 174 `@pytest.mark.asyncio` markers carry the suite's
event-loop behaviour and `marker = pytest.mark.asyncio` is registered nowhere in the tree.

The `pytest-cov` half is confirmed positively, not just by absence:

```
$ uv run pytest tests/test_config.py --no-cov
pytest: error: unrecognized arguments: --no-cov
```

`[dependency-groups] dev` (`pyproject.toml:111-115`) lists `pytest>=8.0.0` and
`pytest-asyncio>=0.23.0` and nothing else that provides a coverage plugin. The 4
`@pytest.mark.skipif` markers and their `os.name` / `isatty()` reasons are therefore read
by the *installed* `asyncio` plugin and pytest core, never by a project-declared
configuration.

**Why MEDIUM and not HIGH is the right row.** `10-audit-test-coverage.md:331` has
"A framework default the suite depends on is declared nowhere" at exactly MEDIUM, and that
is the finding to the word. The HIGH row's nearest clause is "nothing in the repository
measures or enforces the suite outside one machine", and that belongs to `TST-005`, which
is filed once at that severity. Splitting one absence across two findings at two severities
would be exactly the comparison-within-report noise this pipeline exists to remove.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-010 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `pyproject.toml`, `tests/` |
| **Classification** | advisory |

**Description:** There is no pytest configuration file anywhere: `pyproject.toml` has no
`[tool.pytest.ini_options]`, and `pytest.ini`, `tox.ini` and `setup.cfg` do not exist at the root or
in the test tree. Everything the runner does is therefore the framework's default, and the suite
depends on two of those defaults without saying so.

**Evidence вЂ” R11:** configuration files found: none. Markers used: `asyncio` Г—174, `skipif` Г—4.
Markers registered: both are registered (the first by pytest-asyncio, the second by pytest core), so
the marker diff is empty. The gap is the undeclared settings: `asyncio_mode`, `testpaths`,
`filterwarnings`, `addopts`, `xfail_strict` and `markers` are all unset.

**Evidence вЂ” R12** (the implicit default, executed, not read): a throwaway `async def` test with no
decoration, in a scratch file outside the tracked tree, run with `--rootdir=<repo>`:

```
1 failed
Failed: async def functions are not natively supported.
You need to install a suitable plugin for your async framework ...
```

pytest-asyncio 1.4.0 defaults to `asyncio_mode=strict`. The practical cost is what this measures: the
suite's entire async execution contract is 174 manually applied decorators plus an undeclared plugin
default. Under `asyncio_mode=auto` вЂ” a common project-wide setting, and one a maintainer adding a
first pytest table would plausibly write вЂ” all 174 become redundant; under a future default change,
they are the only thing keeping 174 tests from silently not running.

**Exact consequence:** the suite has no declared statement of which plugins it requires, no declared
marker registry, and no warning policy. A dependency bump that changes a default is caught, if at
all, by noticing that tests stopped running вЂ” not by a failing assertion.

**Recommendation:** add a `[tool.pytest.ini_options]` table with `asyncio_mode` stated explicitly
and `testpaths = ["tests"]`. If `auto` is chosen, the 174 decorators can be dropped in a separate,
mechanical change. Stating the mode is the whole fix; the table is a few lines.

---

### TST-011 — validation record

**Decision:** REPRODUCED — the finding stands as filed. | **Original severity:** MEDIUM | **Confirmed severity:** MEDIUM | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `advisory` (unchanged)

*Validation note.*

The directory census is exact. `tests/integration/` contains exactly one file,
`__init__.py`, whose entire content is the docstring `"""Integration tests package for VK
Video Downloader."""` — together with three stale `__pycache__` `.pyc` files left from
`test_mock_vk_server.cpython-312-pytest-9.0.3` and `…9.1.1`. The file the report says
nothing is named after **does not exist in any form**, only its two compiled predecessors
do. The directory contributes **0 of 502** tests. The manifest entry
`"tests/integration/__init__.py"` at **`tests/test_packaging.py:118`** is confirmed, and
`test_packaging.py:177-188` is what enforces it.

The finding's supporting census is also exact: `uv run pytest tests --collect-only -q`
reports `5 tests collected`, all from `tests/test_packaging.py`. The two real child
processes in the whole suite are `tests/test_packaging.py:309` (`uv build`) and
`tests/test_config.py:427` (an environment probe) — so a single tier owns both of them,
and the tier that exists to cross the boundaries the report shows are never crossed
(`TST-007`) owns none.

**A strengthening observation, added here rather than left out.** `tests/test_packaging.py`
itself forbids the audit corpus from shipping: `FORBIDDEN_SDIST_PREFIXES` at `:186-190`
lists `".ai/"` with the comment "the audit corpus: findings, plans, research, phase
catalogue", alongside `".kilo/"` and `".github/"`. `EXPECTED_SDIST_ENTRIES` at `:121` ships
`tests/test_cli.py`. So in the **released artefact**, the `TST-002` / `TST-004` /
`TST-006` identifiers carried in the test tree (see `TST-015`) and the `D-` identifiers
they belong to both resolve to nothing at all — the files they point at are excluded from
the sdist by the project's own packaging gate. That makes the collision worse than a
reader of the working tree can see, and it is why `TST-015`'s recommendation is a rename
rather than a documentation note.

**No type reclassification.** `SPEC-DEVIATION` is arguable — one could file this as
`DOC-UPDATE` on the docstring alone. The finding is not about the docstring: it is about
`test_packaging.py:118` *enforcing* an empty declaration into the release artefact, which
is a test that pins an empty tier as if it existed. That is a test passing for the wrong
reason, which the phase's own edge-case list names, and `SPEC-DEVIATION` is the honest
label for it. Recorded here so the choice is visible rather than silent.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-011 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/integration/`, `tests/test_packaging.py` |
| **Classification** | advisory |

**Description:** `tests/integration/` contains one file, `__init__.py`, whose entire content is
`"""Integration tests package for VK Video Downloader."""` There is no test in it. R1 collected 502
tests, all from the 19 modules directly under `tests/`. The directory is nevertheless declared as
shipped content: `tests/test_packaging.py:118` lists `tests/integration/__init__.py` in
`EXPECTED_SDIST_ENTRIES`, and `test_sdist_entry_set_matches_the_manifest` (`:418-423`) fails if it
disappears. So the one tier whose purpose is to cross the boundaries R7 records as never crossed is
asserted into the release artefact while contributing nothing.

**Evidence вЂ” R1** (`--collect-only -q`): 502 collected, every one from `tests/test_*.py`.
**Evidence вЂ” R7:** 0 unpatched constructions of any external boundary, across all 502 tests. **0
tests contributed by the tier that exists to cross them.** Two real child processes exist in the whole
suite (`test_packaging.py:309` `uv build`; `test_config.py:427` the `.env` positive-control probe) and
neither exercises a product boundary.
**Evidence вЂ” R2:** the tree still contains `tests/__pycache__/test_http_client.cpython-312*.pyc` and
`tests/integration/__pycache__/test_mock_vk_server.cpython-312*.pyc` вЂ” compiled artefacts of test
modules that no longer exist in the source tree. Recorded as inventory; the `.pyc` files are stale
build output, not evidence, and they are gitignored.

**Exact consequence:** a reader of the tree sees an integration package and reasonably infers an
integration tier. There is none, and the packaging test enforces the illusion. The consequence of
every boundary in R7 being crossed zero times is cited to the owning phases; what is filed here is
that the gap has a name and no content.

**Recommendation:** either populate the package or remove it. If it is removed, drop
`tests/integration/__init__.py` from `EXPECTED_SDIST_ENTRIES` in the same change вЂ” that test will
tell you if you forget. Building the tier itself is not an audit subject and is not prescribed here.

---

---

### TST-012 — validation record

**Decision:** REPRODUCED, with one sentence corrected. | **Original severity:** MEDIUM | **Confirmed severity:** MEDIUM | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `advisory` (unchanged)

*Validation note.*

The coverage census is exact. `src/vkdownloader/services/signal_handlers.py` is 46
statements with 13 missed — **71.7 %**, the lowest of any module in the package that has a
test at all (`segment_downloader.py` 77.8 %, `browser.py` 82.0 %; `__main__.py` is at 0 % and
has no test — the only two references to it in the whole tree are its two manifest entries
in `test_packaging.py:86, 149`). The missing set in this run is
`37, 38, 44, 52, 53, 54, 65, 66, 77, 78, 79, 80, 82`, matching the finding exactly:

- `:37-38` — the `except RuntimeError` guard around `asyncio.get_running_loop()`.
- `:44` — `_registered_signals.add(sig)` on the `loop.add_signal_handler` success path.
- `:52-54` — the `else` branch: the no-running-loop fallback loop.
- `:65-66` — the same `RuntimeError` guard in `cleanup_signal_handlers`.
- `:77-82` — the cleanup `else` branch that resets handlers to `SIG_DFL`.

**Correction — one sentence in the finding is false, and its own evidence contradicts it.**
The finding says: "The fallback loop it claims to cover, `signal_handlers.py:52-54`, is
therefore *entered* but its `signal.signal` call is the mock." Lines `52`, `53` and `54` are
in the missing set, so that `else` branch is **never entered at all**. What the test at
`tests/test_hls_downloader.py:2640-2664` actually exercises is the other fallback:
it patches `asyncio.get_running_loop` to return a `_FakeLoop` whose
`add_signal_handler` raises `NotImplementedError`, so `setup_signal_handlers` takes
`signal_handlers.py:40-49` and registers through the `except NotImplementedError` branch at
`:45-49`, whose `signal.signal(...)` at line **48** is covered. In other words the test
*does* verify the Windows fallback it names — "a loop that cannot register via the loop API
falls back to `signal.signal`" — and does **not** touch the no-loop fallback. The
conclusion the finding draws is unaffected and is if anything stronger for it: the no-loop
registration and the entire restoration path have no oracle at all, and `mock_signal.call_count == 2`
at `:2659` is a read-back of the stand-in's own call record.

The second test at `:2667-2697` is a **real** oracle on the handler logic and the finding is
right to leave it alone: it records the registered handler, calls it directly with
`handler(sig, None)` and asserts `shutdown_event.is_set()`. No real signal is delivered,
which is correct and honest. `tests/test_progress_display.py:283-313`'s manual
`signal.signal` save-and-restore is also confirmed, and it is not the defect.

**Why MEDIUM is right and the substituted-site count is not re-filed here.** The five
process-global and fourteen subject-level substitutions are `TST-007`'s, filed once at HIGH
as `BEST-PRACTICE` / advisory. This finding's subject is the *unexecuted effect* — two
registration loops and one restoration loop — and the phase's own rule is explicit that
"a finding whose consequence was not observed is filed with the structural fact and an
explicit `UNVERIFIED` marker, never with an observed severity". The structural fact is
confirmed; the guarantee that real signal registration and real restoration work is
**`UNVERIFIED`**. The handler *logic* is covered by a genuine oracle, which is what keeps
this below `TST-006` and `TST-008`. **Cross-reference:** the real-signal guarantee's
`UNVERIFIED` status is phase 01's (`ENT-` owns registration placement and reachability) and
phase 04's (`CON-` owns the shutdown event and the context-copy workaround); neither is
re-filed here.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-012 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_hls_downloader.py`, `src/vkdownloader/services/signal_handlers.py` |
| **Classification** | advisory |

**Description:** `services/signal_handlers.py` is 46 statements with **13 missed вЂ” 71.7 %, the lowest
of any module in the package that has a test at all.** The suite does test the module
(`test_hls_downloader.py:2636-2681`), but it does so by replacing the very thing under test.

`test_windows_fallback_registers_signal_handlers` (`:2640-2664`) patches
`asyncio.get_running_loop` to a `_FakeLoop` whose `add_signal_handler` raises `NotImplementedError`
(`:2647-2652`) **and** patches `signal_module.signal` (`:2655`). The fallback loop it claims to cover,
`signal_handlers.py:52-54`, is therefore entered but its `signal.signal` call is the mock вЂ” and
`mock_signal.call_count == 2` (`:2659`) is a read-back of the stand-in's own call record. The
`RuntimeError` guard at `:37-38` and the `_registered_signals.add` at `:44` are missing; the cleanup
loop at `:77-82` is missing.

**Evidence вЂ” R2/R3** (missing set в€© parsed ranges): `signal_handlers.py` missing `37, 38, 44, 52, 53,
54, 65, 66, 77, 78, 79, 80, 82`.

**Exact consequence:** whether a real `signal.signal` registration succeeds on this platform, and
whether `cleanup_signal_handlers` actually restores `SIG_DFL`, is unverified. `assert
mock_signal.call_count == 2` (`:2659`) is satisfied by the mock being called twice; it is not evidence
that the process's signal disposition was set or restored. Whether the handler correctly derives
shutdown state from a delivered signal belongs to `04`; the *form* of the oracle standing in for it
is what this phase files, and the guarantee is **UNVERIFIED** вЂ” a real signal is not delivered by the
test environment, and R6 confirmed no test supplies one.

**Recommendation:** keep the unit test for the branch selection, but say what it checks вЂ” branch
choice, not registration. The registration effect is only observable in a subprocess that is
actually signalled, which the current tier cannot do; recording that as a known gap in the module
docstring is better than a test name that implies otherwise.

---

---

### TST-013 — validation record

**Decision:** REPRODUCED — the finding stands as filed. | **Original severity:** MEDIUM | **Confirmed severity:** MEDIUM | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `advisory` (unchanged — see below, a reclassification was considered and declined)

*Validation note.*

The four skips, their guards and the values they would assert were re-measured
independently, and the finding's table is exact — `@pytest.mark.skipif(os.name == "nt")` at
`tests/test_config.py:343` and `:359` and `tests/test_hls_downloader.py:539`, plus one
`stdin.isatty()` / `stdout.isatty()` case. A standalone probe reproduces the measured mode:
`os.chmod(path, 0o600)` → `0o666`, and `path.touch(mode=0o600)` → `0o666`. The
`0o600`-requested / `0o666`-measured claim is confirmed.

**The distinction the finding insists on, and this run does not disturb it.** These are
**reported skips**, not reported passes, and each carries a skip reason that is a true
statement about the platform at collection time — measured in Checkpoint 1 above. The
finding says so twice, in its own text, and it is right twice. That is precisely why
`10-audit-test-coverage.md:330`'s HIGH row — "an oracle reports success while executing no
assertion" — is **unavailable** here: the phase's own rule (`:338`) is that an available
outcome is a declaration, not a failure, and "a problem recorded against the harness" is
explicitly not a finding. The finding is filed for the *form* — the only statement of a
credential-file permission claim in the tree never assesses it on the platform the project
develops on — and MEDIUM is the correct place for that.

**A reclassification to `mandatory` was considered and is declined, with the reason
recorded.** The confidentiality consequence of the same unmet guarantee is already filed
and already `mandatory` by its owner: `ART-007` (phase 07, HIGH, `BEST-PRACTICE`,
mandatory) states "requested `0o600`, measured `0o666`, access state not confining, zero
independent controls, zero oracles that can fail here" and grounds itself in an `icacls`
listing. Promoting this *test-form* finding to mandatory while the owning security finding
already is would put one fact in the Mandatory Fixes list twice at two urgencies. The
cross-reference below is the correct mechanism instead.

**Cross-reference — complement, not merge, and one correction to the finding's own
framing.** `ART-007`'s R3 section already carries this finding's entire four-oracle table,
its "all four are skipped on the declared platform" verdict and the out-of-band `0o666`
measurement, and it does so **without** resting on the suite — its own basis is the
`icacls` listing and its count of zero confining controls. So the substantive claim is not
missing from the corpus, and the claim this report adds is the narrower one the brief puts:
"whether the suite tests the security claim at all" — which is true, and is not stated
anywhere else as a defect. Both are retained; the fix TST-013 prescribes is
platform-independent, costs three lines, and is not covered by anything in `ART-007`:
substitute `os.chmod` itself and assert the call is made with `0o600`, which the oracles
were written to assert and which the platform neutralises.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-013 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_config.py`, `tests/test_hls_downloader.py` |
| **Classification** | advisory |

**Description:** Four `@pytest.mark.skipif(os.name == "nt")` guards вЂ” `test_config.py:337` and `:353`
(log file mode), `test_hls_downloader.py:533` and `:679` (cookie file and argfile mode) вЂ” are skipped
on every run on the declared development platform. Each is a reported **skip**, not a reported pass,
and each carries a reason that is accurate and specific ("`os.chmod` there toggles only the read-only
attribute, so the measured mode is `0o666`"). All four are justified: the assertion is a factual claim
about a POSIX mode, and the platform does not offer the mode.

The form is the finding. Of the suite's whole security surface, exactly two artefact-permission claims
are made in tests вЂ” the temp cookie file at `test_hls_downloader.py:539-550` and the log file at
`test_config.py:343-370` вЂ” and **neither ever runs an assertion on the platform where the code is
developed.** A further 16 permission-adjacent assertions elsewhere in the suite are about paths and
content, not modes, and do execute.

**Evidence вЂ” R10** (real state read by a throwaway probe test, not searched for):

```
sys.stdin.isatty()  = True
sys.stdout.isatty() = False
sys.stderr.isatty() = False
os.name             = 'nt'
st_mode & 0o777 after chmod 0o600 = 0o666
st_file_attributes                 = 32
stat.S_IWRITE set?                 = True
```

So the guards are honest: unskipped, the assertions would fail at `0o666`, exactly as the reason
states. **The form of each oracle is a reported skip** вЂ” an assertion body that never executes.

**Exact consequence:** on the declared platform, a change to `os.chmod(path, 0o600)` at
`ytdlp_downloader.py`/`downloader.py:119`/`config.py:344` вЂ” including deleting the call entirely вЂ”
produces a green run. The `0o600` claim is carried by four tests that never assess it here, and by
nothing else. **UNVERIFIED** for whether the mode is in force; the guarantee belongs to `06` for the
credential file and `07` for the other artefacts, and this finding files only the shape of the oracle.

**Recommendation:** the guards are right; what is missing is any platform-independent assertion of
the *intent*. A test that asserts the `os.chmod(..., 0o600)` call is made вЂ” by substituting
`os.chmod` and asserting on the requested mode вЂ” would run everywhere and would catch the call being
removed. The mode check would then remain as the POSIX-only oracle it honestly is.

---

### TST-014 — validation record

**Decision:** REPRODUCED, with an applicability caveat that must travel with the finding. | **Original severity:** MEDIUM | **Confirmed severity:** MEDIUM | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `advisory` (unchanged)

*Validation note — this decision is conditional on the working tree and says so.*

**The tree state, stated because it is load-bearing here and nowhere else.** `HEAD` is
`a335b2a`. `src/vkdownloader/cli.py` and `src/vkdownloader/config.py` carry **uncommitted**
edits from a concurrent agent. The uncommitted `cli.py` change replaces the three
per-command settings constructions with a single `_run_command_preamble` helper
(`cli.py:123-131`), which introduces the `try:` at `:124`, the `except Exception` at
`:125-126` and the `except UnboundLocalError` at `:127-130` that the finding names.
**`git show HEAD:src/vkdownloader/cli.py` has no such block.** The whole of this finding's
subject is an uncommitted diff, and it is the only one of the 16 whose subject is.

**Both trees measured, as required.** On the working tree, `cli.py` is missing `123` in
this run's coverage output, so the `typer.echo` notice line is genuinely never executed.
Every other line the finding names is present and covered on **both** trees — the
`try`/`except` scaffolding at `123-131` and the wiring at `166` and `197` are missing only
because the helper itself is missing there too. So the structural claim is: on the tree
that carries the change, the body at `cli.py:123` is uncovered and the one test that
reaches it cannot fail on it; on `HEAD` the body does not exist at all.

**The test claim is exact.** `tests/test_cli.py:1841-1845` patches

```python
patch("vkdownloader.cli.warn_unknown_env_vars") as mock_warn,
```

with no `return_value`, so the call returns a `MagicMock`, which is truthy — the `if` at
`cli.py:128` is entered and the `for rejected in unknown` at `:129` iterates a
`MagicMock` zero times. The assertions at `:1850-1854` check
`mock_warn.assert_called_once()`, `mock_log_env.assert_called_once()`,
`mock_setup.assert_called_once()`, `mock_setup.call_args[0][0] is settings` and
`settings.max_retries == 5`. None of them can fail on the notice body. The test's own
docstring at `:1833-1838` says it asserts "the wiring (component interaction) rather than
implementation details" — true, and the finding is not disputing it.

The second site is confirmed: `tests/test_cli.py:1302-1305` patches
`warn_unknown_env_vars` with `side_effect=RuntimeError("environment scan failed")` to
reproduce the D-03 `UnboundLocalError` on the same path. That test has coverage of the
`except Exception` arm and none of the notice. `tests/test_security.py:75`
(`cookie_jar = MagicMock(); cookie_jar.load = lambda *a, **k: None`) is a third instance of
the same form and is the reason the report's appendix correctly lists two self-confirming
classes.

**The applicability caveat, which is part of the decision.** A finding whose evidence
cites a working-tree diff passes here and is recorded as passing. It must be re-checked, or
dropped, at the moment the concurrent change is committed as-is, amended or reverted; if it
is committed as-is the finding stands against the committed tree, and if it is reverted the
finding is stale and must not be carried forward. This caveat is written into the artifact
rather than left in the run's head, because the next reader will not have this run's
`git status`. **Cross-reference:** the preamble's placement is phase 01's (`ENT-002` /
`ENT-003`, already validated and cross-referenced with `VAL-105`); what this finding owns
is that no oracle in the tree can fail on the change's effect.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-014 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_cli.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `src/vkdownloader/cli.py` carries an uncommitted edit (working tree 383 lines; `HEAD`
320). It moves the unknown-`VKDOWNLOADER_*` notice out of the logging path and into the preamble as
plain stderr text вЂ” `cli.py:119-128`:

```python
unknown_vars = warn_unknown_env_vars()
if unknown_vars:
    valid_vars = sorted(_build_valid_env_vars())
    for var in unknown_vars:
        typer.echo(f"Ignored unknown environment variable '{var}'. ...", err=True)
```

**Working-tree-anchored; this code is uncommitted and may change.** The corresponding removal in
`config.py` deletes the `unknown_env_var_ignored` warning and the module logger.

Two tests touch the preamble. `test_cli.py:1841-1854` patches
`vkdownloader.cli.warn_unknown_env_vars` with no `return_value`, so the stand-in returns a
`MagicMock` вЂ” truthy, iterating as empty вЂ” and asserts only `mock_warn.assert_called_once()`,
`mock_log_env.assert_called_once()` and `mock_setup.assert_called_once()`. `test_cli.py:1303` patches
it to raise. Neither asserts what is printed. The other two preamble tests (`:1861`, `:1884`) replace
`_run_command_preamble` wholesale.

**Evidence вЂ” R2:** `cli.py` reports line `123` вЂ” the `typer.echo(` call вЂ” as **missing**. The notice
body has never executed in any run.

**Exact consequence:** the notice's text, its `err=True` routing, and the fact that it fires **once
per unknown variable** are all unverified. A typo in the message, a missing `err=True`, or a
regression that makes the loop fire zero or twice passes. Because `warn_unknown_env_vars` returns a
truthy `MagicMock` in the only test that reaches the body, the branch is entered by accident and its
loop runs zero times вЂ” a test that reaches the code and checks nothing about it.

**Recommendation:** set `return_value=["VKDOWNLOADER_MAXRETRIES"]` on the existing patch and assert
`result.output`/the captured stderr contains that variable name and the valid-variable list. One test
addition; the patch is already there.

---

---

### TST-015 — validation record

**Decision:** REPRODUCED, with one residual the finding's recommendation does not
cover. | **Original severity:** LOW | **Confirmed severity:** LOW | **Type:** `DOC-UPDATE`
(unchanged) | **Classification:** `advisory` (unchanged)

*Validation note.*

The inventory is complete and correct. A search of every `tests/**/*.py` for an identifier
of the report's own form returns exactly three, at exactly the cited lines:

| Site | Carried form | Points at |
|---|---|---|
| `tests/test_cli.py:277` | `TST-002` | audit `TST-002` = the ffmpeg response-file oracle, an audit finding, nothing to do with the "Failed URLs" error-reason comment beside it |
| `tests/test_hls_downloader.py:501` | `TST-004` | audit `TST-004` = the path-traversal guard's oracle, an audit finding |
| `tests/test_hls_downloader.py:2843` | `TST-006` | audit `TST-006` = the untested `aiohttp` body, an audit finding |

All three pre-date the audit and all three collide with this phase's **live** identifiers
now in use, in the same file the report writes. The other 12 carried forms were verified to
resolve to exactly one catalogue: nine `D-` identifiers (`D-01`, `D-02`, `D-03`, `D-04`,
`D-05`, `D-09`, `D-10`, `D-11`, `D-12`) all resolve to
`.ai/plans/done/01-confirmed-code-defects_DONE.md`, which carries thirteen `D-` headings
(`D-01`–`D-13`). The finding's R14 claim that all 9 resolve is confirmed exactly.

**A strengthening observation, added here because it changes the fix's justification.**
`tests/test_packaging.py:186-190` lists `".ai/"` in `FORBIDDEN_SDIST_PREFIXES` — the audit
corpus and the defect register are **excluded from the sdist by the project's own packaging
gate** — while `EXPECTED_SDIST_ENTRIES:121` ships `tests/test_cli.py`. In the released
artefact, therefore, all thirteen carried forms resolve to nothing at all, and the three
`TST-` forms additionally collide with three live identifiers in a file that is not
shipped. The finding asks for a rename; that is the right fix, and the packaging fact is
why it is a rename and not a documentation footnote.

**The residual the recommendation does not cover, recorded here rather than filed
separately.** The report lists `VAL-105` in its inventory — `tests/test_cli.py:1829` and
`:1858` both cite it — but its recommendation covers only the three `TST-` sites. `VAL-105`
is a **validation-store** identifier: it is the "shared preamble anchor with `ENT-002`,
`ENT-003`" finding in `.ai/audit/99-validation/01-entry-architecture-validated-findings.md`,
a transient artefact of one audit run. A test docstring citing it as a durable reference
will become unresolvable the moment the audit corpus is archived, and it is a second
instance of the `VAL-`/`TST-` prefix leakage the report is about. It is not filed as its
own finding here: `TST-015` is the owning finding, it records the site, and minting a
separate `VAL-` for a site another finding in the same report already lists would split one
root cause across two IDs. The recommendation is widened by one line when it is acted on:
cover the two `VAL-105` sites with the same rename.

**Why LOW and `DOC-UPDATE` stand.** `10-audit-test-coverage.md:332` puts "a test's own
documentation names a subject that no longer resolves" at LOW, and `:336` defines
`DOC-UPDATE` as "a reference in a test's own documentation that no longer resolves". This
is that case; the identifiers do resolve *today*, which is why it is LOW and not MEDIUM.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-015 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `tests/test_cli.py`, `tests/test_hls_downloader.py` |
| **Classification** | advisory |

**Description:** The phase catalogue reserves `TST-` for itself and notes that a two-character
collision is unresolvable by the validator. The collision already exists in the tree:

* `tests/test_cli.py:277` вЂ” `(TST-002)`
* `tests/test_hls_downloader.py:501` вЂ” `"""Direct unit tests for _create_temp_cookie_file (TST-004)."""`
* `tests/test_hls_downloader.py:2843` вЂ” `(TST-006)`

**Ownership, per site, recorded before anything is filed:** all three are in *test* documentation, so
they are this phase's. None is adopted, extended or renumbered by this report вЂ” TST-001 through
TST-014 are minted fresh and skip past the occupied numbers. The other carried forms are
`CFG-001`/`CFG-002`, `DF-007`, `INT-001`вЂ¦`INT-007`, `SEC-001`вЂ¦`SEC-007`, `SRV-003`, `SRV-006`,
`STR-008`, `VAL-105`, and `D-01`вЂ¦`D-05`, `D-09`вЂ¦`D-12`.

**Evidence вЂ” R14:** all nine `D-` ids carried by the test tree **resolve** to entries in
`.ai/plans/done/01-confirmed-code-defects_DONE.md` вЂ” no stale register reference. `D-06`, `D-07`,
`D-08` and `D-13` exist in the register and are referenced by no test; `D-08`'s subject is precisely
the four permission oracles now recorded as skips in TST-013, so its absence from the tree is
consistent with the fix having landed.

**Exact consequence:** a reader вЂ” or the validator's cross-finding merge detection вЂ” cannot tell from
`TST-002` at `test_cli.py:277` whether it refers to this phase's catalogue or to the project's own
pre-audit defect list. One `TST-` identifier in the tree points at a test that has nothing to do with
test coverage.

**Recommendation:** rename the three sites to a form the audit does not use вЂ” `D-` is already
exhausted and correct for register entries, so these three want either the register's numbering if
they track a real defect, or no identifier at all. The two `TST-` sites in `test_hls_downloader.py`
describe coverage additions with no defect behind them and can simply drop the parenthetical.

---

---

### TST-016 — validation record

**Decision:** REPRODUCED — the finding stands as filed. | **Original severity:** LOW | **Confirmed severity:** LOW | **Type:** `SPEC-DEVIATION` (unchanged) | **Classification:** `advisory` (unchanged)

*Validation note.*

The counting method and the module percentages are confirmed. The finding's numbers were
obtained with `-p no:randomly`; that flag is not needed here because the suite runs in file
order, and the re-measurement with it omitted produces the same per-statement sets. Module
figures in this run: `ffmpeg_utils.py` 252 statements / 14 missed = **93.6 %** (the report
says 94 %), `ytdlp_downloader.py` 168 / 24 missed = **85.7 %** (the report says 86 %), and
`config.py` 163 / 7 missed = **95.7 %**. All eight branch ranges the finding names are
present in the per-statement missing sets:

| Finding's claim | File | Missing lines measured |
|---|---|---|
| `ffmpeg_utils.py:305-307` — the batch-merge `TimeoutError` arm | `ffmpeg_utils.py` | `305, 306, 307` |
| `ffmpeg_utils.py:352-354` — the final-merge `TimeoutError` arm | `ffmpeg_utils.py` | `352, 353, 354` |
| `ytdlp_downloader.py:103-107` — cancel-and-await after the first completion | `ytdlp_downloader.py` | `103, 104, 105, 106, 107` |
| `ytdlp_downloader.py:522, 523, 529` — the `except QualityNotAvailableError` arms | `ytdlp_downloader.py` | `522, 523, 529` |
| `ytdlp_downloader.py:547-561` — the five resume re-entry exception arms | `ytdlp_downloader.py` | `547, 548, 553, 554, 559, 561` |
| `downloader.py:321, 342, 376, 404` — the four `if not await cancel_subprocess(process)` guards | `downloader.py` | `321, 322`; `342, 343`; `376, 377`; `404, 405` |
| `downloader.py:375-382` — the shutdown branch of the exit-time drain | `downloader.py` | `371, 376, 377, 382` |
| `config.py:232` — the `Valid fields are:` branch | `config.py` | `232` |

**One note on the tree state, which is where this finding touches it.** `config.py:232` is
the same line on both trees; the uncommitted `config.py` change removes the
`logger.warning("unknown_env_keys_detected", ...)` loop and its debug call, so the working
tree's `config.py` has 7 missed lines where `HEAD` has 10. The finding's own line `232` is
unaffected. Its claim that `ffmpeg_utils.py:305-307` is "the same
`except TimeoutError` as the final merge's, in the batch half" is confirmed by reading
`:303-307` and `:350-354` — the two `except` blocks are textually identical and neither
executes.

**`downloader.py:303` is covered, and that is what makes this a coverage finding and not a
second `@argfile` finding.** `TST-001` rests on line 303 being *executed* while every
assertion about its effect is a stand-in. This finding is about the eight branches that
never execute at all. They are different subjects and neither absorbs the other.

**Why LOW stands.** Each of the eight arms is a degradation path: on its own, none produces
a wrong or unsafe artefact — a missing branch here means a timeout is not translated into a
clean `None`, or a `QualityNotAvailableError` falls through to a generic error, or a
cancellation is not drained promptly. The phase's own table has no row for an unclaimed
degradation branch, and the report's own ranking gives these bodies consequence class 2
against the class-3 bodies in `TST-006` and `TST-003`; the severities are consistent with
that split. It is filed `advisory` and it is the right size for what it describes.

**The redaction backstop at `ffmpeg_utils.py:240-242` is a secret-logging path and is not
downgraded by the LOW severity of the finding that mentions it.** It is missing here, and it
is phase 06's `SEC-002` subject. It is cross-referenced, not re-filed. Separately, the
phase-08 claim this finding's ranking table cites — "no test reads the log file's content at
all" — is **upheld**; the non-reproduction recorded beside it in the source report is not,
and the adjudication is `VAL-120` and is reproduced in full in Checkpoint 3 below.

**The finding as filed, retained verbatim:**

| Field | Value |
|-------|-------|
| **ID** | TST-016 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/utils/url_sanitizer.py` |
| **Classification** | advisory |

**Description:** Beyond the network layer in TST-006, several failure paths that exist specifically to
degrade gracefully are never entered, so the degradation they implement is unverified.

* `ffmpeg_utils.py:305-307` вЂ” `_merge_batch_segments`'s `except TimeoutError` в†’ `batch_merge_timeout`
  в†’ `return None`. The **timeout** half of a batch merge has never run; the returncode half at
  `:309-312` has.
* `ffmpeg_utils.py:352-354` вЂ” `_perform_final_merge`'s `except TimeoutError` в†’ `final_merge_timeout`
  в†’ `return False`. Same shape, opposite outcome from the tested returncode path.
* `ytdlp_downloader.py:522-529` вЂ” `except QualityNotAvailableError` and the re-raise at `:529` in
  `_attempt_segment_resume`; `:547-561` вЂ” the `except (ExtractionError, OSError)` /
  `except ValueError` arms and their `raise`s.
* `ytdlp_downloader.py:86-108` вЂ” `_await_first_and_cancel_others`: `task.cancel()`, `await task`,
  `except asyncio.CancelledError: pass` at `:103-107`, all missing.
* `downloader.py:375-382` вЂ” `download_with_ffmpeg`'s shutdown branch: when
  `shutdown_event.is_set()`, `cancel_subprocess` and `ffmpeg_cancel_not_clean`. The four
  `if not await cancel_subprocess(process)` guards at `:321, 342, 376, 404` are all missing, so the
  "the child was not reaped" warning has never been emitted in a test.
* `utils/url_sanitizer.py:29-30` вЂ” `except Exception: return "***REDACTED***"`, the redaction
  backstop. Never runs.
* `config.py:232` вЂ” the `Valid fields:` branch of `format_validation_error`, the other half of
  TST-009's disjunction. Never runs; that is why my 25-misspelling probe saw the "Did you mean"
  branch every time.

**Evidence вЂ” R2/R3** (missing set в€© parsed ranges), listed per body above. `ffmpeg_utils.py` is 94 %
and `ytdlp_downloader.py` 86 % overall вЂ” high figures that coexist with these eight unexecuted
branches, which is the concrete illustration that a module percentage says nothing about any body.

**Exact consequence:** a change to the timeout handling, the cancel-and-wait sequence, the resume
retry arms, or the redaction backstop ships untested. Each of these is a degradation path: its whole
purpose is to behave correctly when something has already gone wrong, which is exactly the situation
the suite never constructs.

**Recommendation:** these are the cheapest bodies in the report to cover вЂ” each is an `except` arm
around a stub. The shared shape is: substitute the awaited call with a stand-in that raises, assert
the return value and the logged event. `tests/test_ffmpeg_utils.py` already has
`MagicMock(spec=asyncio.subprocess.Process)` set up for exactly this.

---

---

## Appendix вЂ” (a) ranking evidence

The factor table below is the raw material for block (a). `O` is oracle strength (3 a test can fail on
the body В· 2 a test asserts a call or a return but not the body В· 1 a test exists whose name or
documentation claims it В· 0 no test references it), measured by R3 and R9. `C` is the consequence
class read from the owning phase's own severity vocabulary; no severity is assigned here. `E` is
reachability (2 reachable without an external boundary В· 1 only behind a boundary the suite mocks В·
0 not reachable in this environment), measured by R7. The comparator is `O` ascending в†’ `C` descending
в†’ `E` ascending в†’ owning phase ascending в†’ subject name ascending, applied with no judgement between
the table and the order.

| Body (owner) | O | C | E | Basis |
|---|---|---|---|---|
| `ffmpeg @argfile` transport, `downloader.py:303` (05) | 2 | 3 | 1 | assertions are on the argv shape only; R7 shows 0 real subprocess crossings |
| Netscape cookie file в†’ real consumer (06) | 2 | 3 | 1 | 100 % executed, 0 missed; the asserted input is the test's own constant |
| segment originals across a failed final merge, `ffmpeg_utils.py:511-515` (03) | 2 | 3 | 1 | no test drives the failing batched merge; the only failure test uses 1 temp file |
| TLS-verification switch, `segment_downloader.py:539-543` (06) | 0 | 3 | 1 | 0 references to `_create_connector`; body unexecuted |
| cancellation cleanup, `segment_downloader.py:562-570` (04) | 0 | 3 | 1 | 0 references to `_await_and_cancel`; body unexecuted |
| `Retry-After` HTTP-date parse, `downloader_throttle.py:296-299` (03) | 0 | 2 | 1 | body unexecuted |
| `download` error tail, `cli.py:258-266` (01) | 0 | 2 | 2 | body unexecuted; reachable with no boundary |
| post-resolution traversal guard, `security.py:59-62` (06) | 1 | 3 | 2 | a test's docstring claims it; the body is unexecuted |
| permission-mode oracles Г—4 (06/07) | 1 | 3 | 2 | reported skip; the assertion body never executes |
| `_await_first_and_cancel_others`, `ytdlp_downloader.py:103-107` (04) | 0 | 2 | 1 | body unexecuted |
| batch/final merge timeout arms, `ffmpeg_utils.py:305-307, 352-354` (03) | 0 | 2 | 1 | bodies unexecuted |
| redaction backstop, `url_sanitizer.py:29-30` (06) | 0 | 3 | 2 | body unexecuted |
| `format_validation_error` suggestion name (02) | 0 | 1 | 2 | the assertion is a disjunction; no test constrains the name |
| log-file format contract (08) | 0 | 1 | 2 | 0 tests read the log file's content; only `.exists()` and modes |

Applying the comparator: the four `O=0, C=3` bodies lead, then the three `Oв‰¤1, C=3`, then the `O=2`
rows. **The list is non-empty, and nothing in the repository gates it** вЂ” that is the finding, filed
once as TST-005. The per-body consequence of each row belongs to the owning phase; this phase cites
the measurement and files the absence of the oracle, once each, in TST-001 through TST-016.

### Non-reproductions (recorded with exact inputs, not as clean results)

* **"The `Did you mean` suggestion names a field that does not exist."** Inputs: 25 misspellings вЂ”
  `maxretries, max_retry, max_retrie, download_dir_, downloaddir, logfil, log_leve, sslverif, quality,
  qualities, timeout, cookey_source, useragent, throttledrate, http_chunksize, browser_wait, headles,
  tz, headlesss, downlaod_dir, maxtimeout, retrys, logg_level, sslverifyy, browserr` вЂ” each passed to
  `Settings(**{bad: "1"})` with the resulting `ValidationError` handed to `format_validation_error`.
  Result: **0 of 25** produced a name absent from `Settings.model_fields`. The *test-side* fact that
  the assertion cannot detect this is filed as TST-009; the *behaviour* is not reproduced here.
* **"The log file declared JSON is not JSON."** Input: `setup_logging(Settings(log_file=..., log_level="DEBUG"))`,
  then three events through the product's own logger (`vkdownloader.services.downloader.logger`, the
  object every module obtains) plus one through `structlog.get_logger`. Result: **4 of 4 physical
  lines parse as JSON**, because `config.py:365-367` selects `JSONRenderer` when `log_file` is set and
  every product call site goes through structlog. The mixed-format case is reached only when a raw
  stdlib `logging` call shares the file вЂ” which is a question about *which* logger a code path uses,
  not about the renderer, and I did not observe a product path that does it. What **is** established:
  **no test reads the log file's content at all** (`test_config.py:328-370` asserts `.exists()` and
  two modes). The coverage gap is filed; the defect claim is not reproduced by this phase.
* **The four permission skips.** Reproduced as reported skips, and their stated reason verified
  independently (see TST-013, R10). Not re-filed as anything other than the form of the oracle.

---

---

## Checkpoint 2 — R2 Cross-Finding Analysis

- **Stage:** R2 Cross-Finding Analysis
- **Findings in scope:** 16 source findings + every finding in the corpus cited by them
- **Cross-phase conflicts:** **1** — `VAL-120`, the log-file JSON subject
- **Complements retained (not merges):** 4 — `TST-001`/`TRN-001`, `TST-002`/`SEC-009`,
  `TST-003`/`NET-001`, `TST-004`/`SEC-006`
- **Merge candidates:** **1** — `VAL-125`, `TST-005`/`DEP-002`
- **Audits of code whose owning phase has not run:** 0
- **Checklist against block (b)'s seven rows, recorded so a second run need not re-derive it:**

| Block (b) row | Instances in this corpus | Handling |
|---|---|---|
| Same root cause | `TST-005` / `DEP-002` — one subject (`packaging-check.yml`'s single test step), one remediation, two different `Type` and `Classification` | merge candidate, `VAL-125`; **not merged here** — `11`'s validator owns its half and has not run |
| Same subject, different phase | `TST-001`/`TRN-001`, `TST-002`/`SEC-009`, `TST-003`/`NET-001`, `TST-004`/`SEC-006` | each side owns its own subject; both retained, cross-referenced on the finding's `**See also:**` line |
| Same evidence | `TST-013` / `ART-007`'s R3 section — the identical four-oracle table and the identical out-of-band `0o666` | `ART-007` also carries the *product* guarantee it fails; different subjects, one measurement. Retained, cross-referenced, no merge |
| Symmetric duplicates | 0 | — |
| Genuine complement | the four pairs above, plus `TST-006`/`CON-001` and `TST-006`/`SEC-` on the TLS switch, and `TST-007`/`DEP-001` on the absent lint jobs | retained, cross-referenced |
| Duplicate of something already filed | 0 | — |
| Incompatible claims | 1 — `VAL-120` | escalated, resolved, both claims quoted |

**The two non-reproductions the source report records were re-measured, and one of them is
a conflict and one of them is a complement. Both are settled here in full; neither is left
as an open question for the next run.**

### The "did you mean" non-reproduction — a complement, and `CFG-003` survives

The source report records: *"0 of 25 produced a name absent from `Settings.model_fields` …
The claim that the suggestion is wrong in 12 of 19 cases is not reproduced by this phase's
measurement."* The full adjudication, with the measurements that settle it, is the
validation note on `TST-009` above. The finding in one line: **the two numbers measure
different surfaces, and the surface decides the answer.** Phase 10 typed its 25
misspellings as **constructor keyword arguments**; phase 02 wrote its 19 as
**environment-file keys**. The same ten names driven through both paths return a
semantically correct suggestion 10 of 10 times on the constructor path and 8 of 10 times
wrong on the file path, because `config.py:211` builds the search key as
`prefix + loc.lower()`, and on the file path `loc` already carries the prefix — so
`vkdownloader_maxretries` is compared against `vkdownloader_download_dir` and
`vkdownloader_download_timeout`, which dominate it, while the bare `maxretries` is compared
against `download_dir` and `download_timeout` in a field-only namespace where
`max_retries` is the nearest match. There is no incompatible assertion between the two
reports, so no `VAL-` is minted. **`CFG-003` (phase 02, MEDIUM, mandatory, validated)
stands with its 12-of-19; the phase-10 non-reproduction is a correct negative on the wrong
path.** The single defect the pair identifies is the same one, and `TST-009`'s
recommendation — add an environment-file-path case — is the fix.

### The log-file JSON non-reproduction — a conflict, and `OUT-002` survives

The source report records: *"4 of 4 lines parse as JSON … I did not observe a product path
that does it. The mixed-format case is reached only when a raw stdlib `logging` call shares
the file."* That second sentence is **false**, and the measurement below is what falsifies
it.

Three shapes were run through the product's own `setup_logging(Settings(log_file=…,
log_level="DEBUG"))`, one per process, because `logging.basicConfig` is a no-op after the
first call in a process:

| Shape | Records emitted | Physical lines | Parse as JSON | Traceback markers |
|---|---|---|---|---|
| **success path only** — 4 events, no exception (the report's shape) | `hls_playlist_fetched`, `segment_downloaded`, `segment_retry`, `download_complete` | **4** | **4** | 0 |
| **1 single-link `logger.exception(...)`** | + `download_failed` | **6** | **2** | **2** |
| **1 two-link chained `logger.exception(...)`** | + `download_failed` | **13** | **2** | **4** |

The success row is the report's measurement, reproduced exactly. The other two rows are the
defect.

**The mechanism, isolated.** `config.py:373`'s `format_exc_info` pops `"exc_info"` from the
**structlog event dict**. But `structlog.stdlib.BoundLogger.exception` passes
`exc_info=True` into `logging.Logger.exception`, which sets the **`LogRecord`** attribute
`record.exc_info`; the stdlib `Formatter` then appends the chain a second time, outside the
JSON envelope. Captured directly: after `format_exc_info` runs, `record.exc_info` is still
populated (`('AssertionError', AssertionError(...), traceback)`), and formatting that one
record through `logging.Formatter("%(message)s")` yields **415 characters** of traceback
appended to a **1-character** message.

**The product path exists, and it sits inside the very block `TST-008` shows no test
executes.** `src/vkdownloader/cli.py:264` is `logger.exception("download_failed", url=url,
video_id=video_id)` inside `except VideoNotFoundError` on the **default** `download` path,
with `logger = structlog.get_logger(__name__)` at module scope. `services/downloader.py:264`
is the same call inside `except`. Neither is a "raw stdlib `logging` call" — both are
structlog bound loggers, which is exactly the form measured above. Two consequences: the
report's claim that no product path reaches the mixed-format case is contradicted by a named
line in the code under audit, and the very nine lines `TST-008` files as never executed are
the lines that emit the unparseable record.

**The reconciliation is exactly the one the brief proposed, and it is confirmed: the defect
needs an exception record, and a 4-record success path cannot show it.** A 4-line success
log is 4 valid JSON lines. The moment one `logger.exception` record is emitted the same file
becomes 6 lines of which 4 do not parse, with the chain written twice.

**This is a cross-phase conflict, so it is escalated as `VAL-120` below.** `OUT-002`
(phase 08, MEDIUM, `SPEC-DEVIATION`, mandatory, validated) is the surviving finding, and
the phase-10 non-reproduction is rejected.

---

## Findings filed against the audit inputs — `VAL-120` … `VAL-125`

These are defects in the audit inputs themselves — a cross-phase conflict, an absent
decision slot, a broken base-context read, an unevaluable gate, an unexempted census, and a
merge candidate with one insertion point. They are `SPEC-DEVIATION` against the pipeline's
own documents, and none of them is a product-code finding.

### VAL-120: The report asserts the log-file JSON defect is unreachable from a product logger; phase 08's validated `OUT-002` asserts the product's own exception path produces records that are not JSON

| Field | Value |
|---|---|
| **ID** | `VAL-120` |
| **Severity** | CRITICAL |
| **Type** | `SPEC-DEVIATION` |
| **Affected Modules** | `.ai/audit/10-test-coverage/findings.md` (the non-reproduction appendix and the ranking table's "log-file format contract (08)" row), `.ai/audit/08-cli-observability/findings.md` (`OUT-002`) |
| **Classification** | mandatory |

**Description.** Two phases assert incompatible facts about one subject. Phase 10's
validated report records a non-reproduction: *"4 of 4 lines parse as JSON … I did not
observe a product path that does it. The mixed-format case is reached only when a raw
stdlib `logging` call shares the file — which is a question about which logger a code path
uses, not about the renderer."* Phase 08's validated report records the opposite for the
same log file: 22 075 bytes and 141 lines from a real failing download, 130 of them not
JSON, and the log-file contract
(`docs/01-tools/installation.md`, `docs/11-guides/logging.md`, the `_log_file_env_var`
docstring) breaking. Both are validated. One is wrong, and which one is decided by
measurement, not by preference.

**Evidence.** The three measurements are in the adjudication block above. The decisive
three: the success path is 4 lines / 4 parseable; one single-link `logger.exception` record
is 6 lines / 2 parseable with the chain written twice; one two-link chained record is 13
lines / 2 parseable with the chain written four times. The mechanism is isolated at
`config.py:373` — `format_exc_info` pops the key from the structlog event dict while
`BoundLogger.exception` has already set the `LogRecord` attribute, and the stdlib
`Formatter` appends 415 characters of traceback to a 1-character message. The product path
is named: `src/vkdownloader/cli.py:264`, on the default `download` path, with a
structlog `BoundLogger` — not a "raw stdlib `logging` call".

**Recommendation.** Strike the non-reproduction paragraph from the phase-10 report and
replace it with the measured shape table. Do **not** touch `OUT-002`: it is the surviving
finding, its severity and classification are correct, and the phase-08 validator's
demonstration is reproduced here independently. The correct forward action is `OUT-002`'s
own, and phase 10's own separately-valid claim — that no test in the tree reads the log
file's content at all — is upheld by this run and stands as the reason the defect was never
caught.

**Why CRITICAL.** `99-audit-validate.md:329` reserves CRITICAL for a cross-phase conflict.
Two validated reports now disagree about whether the product writes parseable JSON when it
logs a failure, and an operator reading the corpus can reach either conclusion.

### VAL-121: The report format has no slot for a validation decision, and the role that writes a report omits one of the four type labels the format defines

| Field | Value |
|---|---|
| **ID** | `VAL-121` |
| **Severity** | MEDIUM |
| **Type** | `SPEC-DEVIATION` |
| **Affected Modules** | `.ai/audit/templates/audit-findings.md`, `.kilo/agents/auditor.md:257-259`, `.kilo/agents/validator.md:243-245, 356-358` |
| **Classification** | mandatory |

**Description.** Two defects in one input, both observed, both with a two-line fix.
First, the format's finding block runs from the heading straight into the field table
(`:19-33`) and its nine mandatory fields (`:64-74`) contain no decision field, so a
`Validation Note` — which this phase must attach to **every** decided finding — has nowhere
to go. Second, the template defines four type labels
(`Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`, `:68`) and the roles
that actually write and decide reports carry three. `.kilo/agents/auditor.md:257-259` lists
`[SPEC-DEVIATION]`, `[BEST-PRACTICE]`, `[DOC-UPDATE]`. `.kilo/agents/validator.md:243-245`
and again at `:356-358` list the same three. `RUNTIME-ERROR` is absent from both.

**Evidence.** The omission is not cosmetic: **13 findings already published in this corpus
are typed `RUNTIME-ERROR`** — `ENT-001`, `ENT-002`, `ENT-003`; `NET-001`, `NET-003`,
`NET-004`, `NET-005`, `NET-008`, `NET-010`, `NET-016`, `NET-017`; `CON-001`, `CON-003`,
`CON-004`, `CON-005`, `CON-006`, `CON-007`, `CON-008`; `SEC-009`; `ART-008`, `ART-009`,
`ART-012`, `ART-013`; `OUT-001`, `OUT-013`, `OUT-016`. Every one of them is a legal report
that the agent instructed to produce it was never told it could produce. The format is the
authority for the vocabulary; the role file is the defective side. The absent decision slot
has been worked around in all nine existing validation stores — each states the deviation
once at the top and writes its notes above the field table.

**Recommendation.** Add `| **Validation Note** | {decision, re-derived severity, and what the validator measured} |` to the template's field table, and add `- `RUNTIME-ERROR` — anything observed failing at runtime.` to both role files next to the three they already carry. Do not renumber anything already published; the thirteen `RUNTIME-ERROR` findings are already legal against the format.

**Why MEDIUM.** The format is shared by every phase and the defect recurs on every future
run, which is why it is `mandatory`; but no product artefact and no run's conclusion is
wrong, which is why it is not higher. The fix is four lines.

### VAL-122: `audit-multi-phase.md` reads a project-instructions file the repository does not have

| Field | Value |
|---|---|
| **ID** | `VAL-122` |
| **Severity** | MEDIUM |
| **Type** | `SPEC-DEVIATION` |
| **Affected Modules** | `.kilo/commands/audit/audit-multi-phase.md:43` |
| **Classification** | mandatory |

**Description.** Step 1 of the orchestrator, "Gather Base Layer Context (once)", lists
three mandatory reads: `.ai/context/commands.md` for verification commands, **`AGENTS.md`
for project guidelines**, and the documentation structure from `docs/`. The first exists and
carries the four verification commands. The third exists. **The second does not exist** —
the repository root holds no `AGENTS.md`, and none of `CLAUDE.md` or `PROJECT*.md` either.

**Evidence.** The root directory listing contains `pyproject.toml`, `uv.lock`, `README.md`,
`.env`, `.env.example`, `.gitignore`, `.python-version` and six stray working files. The
project's guidelines are not missing — they are **somewhere else**: `.kilo/rules/project.md`
(15 rules, including the production-code-is-king rule this very report is decided against)
and `.kilo/rules/commands.md`, which the agent runtime actually loads. So the command
assembles half its base context from the one file that exists, silently omits the 15 rules
that decide every severity and classification in the corpus, and reports nothing about the
miss — every executor and validator in this run received its rules through a different
channel than the one the orchestrator documents.

**Recommendation.** Change line 43 from `Read `AGENTS.md` for project guidelines.` to
`Read `.kilo/rules/project.md` and `.kilo/rules/commands.md` for project guidelines (the
runtime loads both; a root `AGENTS.md` is not used by this repository).` Nothing else in
the command needs to change.

### VAL-123: The validator gate cannot be evaluated, and the run's closing output reports its coverage unconditionally

| Field | Value |
|---|---|
| **ID** | `VAL-123` |
| **Severity** | HIGH |
| **Type** | `SPEC-DEVIATION` |
| **Affected Modules** | `.kilo/commands/audit/audit-multi-phase.md:86`, `:112-127` |
| **Classification** | mandatory |

**Description.** The phase loop's fourth step decides whether this pipeline's own
verification stage runs at all:

```
85:  ### 2.4 Launch Validator (skip for Phase 99)
86:  Launch the Validator **only** when Findings are **not trivial** ands relate to
     **significant code changes** or **architecture modifications**.
88:  In all other cases — skip.
```

"not trivial", "significant code changes" and "architecture modifications" are defined
nowhere in the command, in any role file, or in any phase handbook, and nothing in the
command evaluates them. A run of the command therefore cannot determine whether a phase is
eligible, and the decision is left to an unstated judgement at execution time. The
closing block then reports, with no gate on it:

```
117: Phases completed: {N}/{N}
118: Validated findings: {N} total
120: By severity:
121: - CRITICAL: {n}
```

A stage that never runs and a summary claiming it ran are one defect, not two, and this is
that defect.

**Evidence.** The gate did fire for this run — the validator for phase 10 is running — but
nothing evaluated the condition; the orchestrator launched it. The corpus shows both
outcomes of an unevaluated gate in the same direction: at the start of this run, eight of
eleven phases had a validation artefact and one had a findings file with none
(`.ai/audit/11-supply-chain/findings.md`), and the command has no way to notice or report
either. `AUDIT COMPLETE` would have printed the same three lines in both cases.

**Recommendation.** Either delete lines 85-88 and always launch the validator, or replace
the undefined terms with a checkable rule and print the outcome. The rule must be
mechanical — the cheapest that is true: validate every phase whose findings file contains
at least one finding of `Severity: CRITICAL` or `HIGH`. And the closing block must derive
`Validated findings` from the artefacts that exist, not from a count the loop intends.

### VAL-124: A reachability census has no exemption for the audit's own documents, the phase directory, or any worktree

| Field | Value |
|---|---|
| **ID** | `VAL-124` |
| **Severity** | MEDIUM |
| **Type** | `SPEC-DEVIATION` |
| **Affected Modules** | `.kilo/commands/audit/audit-orphaned.md:30-47`, `.kilo/worktrees/southern-bandana/**` |
| **Classification** | mandatory |

**Description.** `audit-orphaned.md` is the pipeline's "identify files that are genuinely
unused" command. Its analysis method step 1 is *"Identify files unreachable from known
entry points"*, and its protect-list at `:30-37` is categorical only: documentation,
configuration and tooling, entry points and externally invoked scripts, migrations, seeds,
fixtures and generated files, files referenced dynamically, and files required by CI,
Docker, package managers, build tools, templates or external integrations. **Nothing in the
file exempts the audit's own documents, the phase catalogue, or any agent worktree**, and
nothing else states that exemption.

**Evidence.** The repository contains a worktree at `.kilo/worktrees/southern-bandana/`
holding **214 files** (excluding `__pyc`), of which:
- **19** are a complete stale copy of a previous audit corpus — nine `findings.md` and nine
  `*-validated-findings.md` plus the template, for a nine-phase catalogue that no longer
  exists at the root;
- **28** are a stale copy of the whole audit command set, including **30 phase handbooks**
  for a different phase taxonomy (`01-audit-cli`, `07-audit-tests`, `11-audit-test-coverage`
  — numbering that means something different from the current `01`–`11`);
- **29** are a second copy of `src/vkdownloader/`, which the `.gitignore` comment already
  names: "Agent worktrees: each holds a complete second copy of src/vkdownloader/".

None of those files is a migration, a seed, a fixture, a generated file, or a file required
by CI or a package manager. Under the stated method all 214 are candidates, and the
deliverable's own table asks for `Action: Review/Delete` with
`Why Considered Unused: "No imports, no references, unreachable"`.

**Recommendation.** Add to the protect-list at `:30-37`, in the command's own words:
*"The audit's own corpus and instructions: `.ai/`, `.kilo/commands/`, `.kilo/agents/`,
`.kilo/rules/`, `.kilo/skills/`, and every `.kilo/worktrees/**` directory. A stale copy of a
previous phase catalogue inside a worktree is a previous catalogue, not an orphaned file, and
must be excluded from both the analysis and every count derived from it."* This is
recorded as a required statement rather than left implicit, because nothing else states it
and the pipeline already has one instance of the failure it prevents — the `VAL-` prefix
collision in Checkpoint 1, which exists only because the `VAL-001` identifiers in nine
sibling stores and in this one were minted independently.

### VAL-125: `TST-005` and `DEP-002` state one root cause with one remediation, on one insertion point, at two different classifications

| Field | Value |
|---|---|
| **ID** | `VAL-125` |
| **Severity** | MEDIUM |
| **Type** | `SPEC-DEVIATION` |
| **Affected Modules** | `.github/workflows/packaging-check.yml`, `.ai/audit/10-test-coverage/findings.md` (`TST-005`), `.ai/audit/11-supply-chain/findings.md` (`DEP-002`) |
| **Classification** | advisory |

**Description.** Two reports in this corpus file the same root cause, prescribe the same
change, and classify it differently.

| | `TST-005` (phase 10, this report) | `DEP-002` (phase 11) |
|---|---|---|
| Subject | `.github/workflows/packaging-check.yml:53` runs one module of 502 | the same line, cited as `packaging-check.yml:53` |
| `Type` | `BEST-PRACTICE` *(corrected to `SPEC-DEVIATION` by this run)* | `SPEC-DEVIATION` |
| `Classification` | `advisory` *(corrected to `mandatory` by this run)* | `mandatory` |
| Recommendation | "add a workflow that runs `uv run pytest tests` on `src/**` and `tests/**` changes" | "Add `uv run pytest tests/` as a step in the existing `packaging-check` job, or as a separate `tests` job on the same path filter" |

The two recommendations are one change. Both anchor on the same job's step list in the same
53-line file. Neither declares the other, and both declare that the other owns the rest of
the territory — `DEP-002` says "It files nothing about whether the tests prove anything —
that is phase 10's, cited here and not merged", and `TST-005` says "Everything else —
declaring a coverage tool, a threshold, a lint job — is `11`'s to add".

**Evidence.** `.github/workflows/packaging-check.yml:52-53` is a two-line
`- name:` / `run:` pair at the end of the job's only step list. Two fixes authored from two
reports, applied from two worktrees, in either order, produce two identical steps or a
merge conflict at the same two lines. `TST-005` adds one element `DEP-002` does not carry
and that is worth not losing in a merge: the *measurement* axis — no coverage tool is
declared in `[dependency-groups] dev` (proved in Checkpoint 1) and no coverage threshold
exists anywhere, so the 89 % figure in this report is a local observation that no artefact
records.

**Recommendation.** Let **`DEP-002` absorb** the workflow change, because it is the owner of
`.github/workflows/**` by phase-11's own boundary and it is already `SPEC-DEVIATION` /
`mandatory`. Fold into it the one element `TST-005` uniquely carries: that no coverage
measurement or threshold is declared in the repository, so the ranked gap list in phase
10's report has nothing to regress against. Then mark `TST-005` as absorbed and leave its
ranking contribution in place — it is the only place the coverage-gap ranking is written
down. **This run has not performed the merge**: it edits neither report, and phase 11's
validation has not run, so the absorbing decision is recorded here for that run to ratify
or overrule. **Do not land both fixes independently.**

---

## Checkpoint 3 — R3 Validate Each Finding

- **Stage:** R3 Validate Each Finding
- **Findings in scope:** 16
- **Evidence anchor:** this file, self-contained. Every finding's original text is retained
  below its decision; the source report is unmodified.
- **Dependencies / blockers:** none
- **Checklist against block (c), (d), (e), (f), (g), (h), (i) — one line each, so a second
  run does not re-derive them:**

| Block | Finding |
|---|---|
| (c) (a) (d) a product claim with no test that can fail on it, and a sibling phase's highest-consequence subject | `TST-001`, `TST-002`, `TST-003` |
| (c) (a) a test asserting what the test itself configured | `TST-008`, `TST-010` |
| (c) (a) a body claimed by a test and never executed | `TST-004`, `TST-007`, `TST-012`, `TST-014` |
| (c) (a) a declared verification command the automation contradicts | `TST-005` |
| (c) (a) a test's only oracle for a documented parameter is skipped on the declared platform | `TST-013` |
| (c) (a) a test asserts only its own environment | `TST-006` |
| (c) (a) a test's asserted value is the test's own stand-in | `TST-007`, `TST-012` |
| (c) (a) a test that passes for the wrong reason | `TST-004`, `TST-011` |
| (c) (a) a test whose name is wrong | `TST-001` |
| (c) (a) a test that asserts a tautology | `TST-009` |
| (c) (a) a test with a self-referential fixture | `TST-012` |
| (c) (a) mock objects that do not implement the protocol the code uses | `TST-006` |
| (d) a value that appeared to be a leak, actually an `active` flag | none found |
| (d) a test that only re-tests its own mock | `TST-012` |
| (d) a test that verifies a stand-in, not the product | `TST-001`, `TST-007` |
| (d) a claim with a filename but no line number | none found — every anchor in this report carries a line number |
| (d) a claim whose only support is a count | none found as a sole support; the two count-based claims (`TST-006`'s "0 references", `TST-016`'s 8 branches) each carry a per-statement missing-line set beside them, and both were re-measured here |
| (d) a claim about "the tests" as a whole | none found |
| (d) a test that cannot fail on the main subject | `TST-001`, `TST-002`, `TST-009`, `TST-014` |
| (e) an assertion that passes while the product is wrong | `TST-001`, `TST-002`, `TST-003` |
| (e) a tautological assertion | `TST-009` |
| (e) a self-confirming fixture | `TST-011`, `TST-014` |
| (e) an assertion a substring can satisfy | `TST-002` (`"vkvideo.ru" in result`), `TST-004` (`"traversal" in str(exc_info.value)`) |
| (e) a weaker assertion than the claim | `TST-003` |
| (f) a documented default the test hard-codes | `TST-005`, `TST-010` |
| (f) a measured result never captured or stored | `TST-010` |
| (g) a shared fixture in a test file instead of `conftest.py` | `TST-005` |
| (g) a real resource left to a per-test teardown | `TST-005` |
| (g) a test-order dependency | none found; the four skips are environment conditions, not order |
| (h) a docstring that describes the test inaccurately | `TST-004`, `TST-012` |
| (h) a comment that contradicts the code | `TST-002`, `TST-004` |
| (h) a copied-paste artefact | `TST-004` |
| (h) a reference that does not resolve | `TST-015` |
| (h) an identifier from another phase's prefix | `TST-015` |
| (i) a validator cannot attach a decision | `VAL-121` |
| (i) a report's structure makes a finding unreadable | none found; all 16 are well-formed |

- **Checklist against the `## 8` edge-case list, one line each:**

| Edge case | Finding |
|---|---|
| a test that substitutes the very thing it names | `TST-007` |
| a test that passes and would not catch a regression | `TST-001`, `TST-002`, `TST-003`, `TST-004` |
| a test whose asserted count can be satisfied from anywhere in the call graph | none found |
| a result that changes with the working directory or a file that resolves from it | **tested and not found** — Checkpoint 1's three-variable run returned 0 of 30 moved, and `tests/conftest.py:13-42` chdirs to `tmp_path` for every test |
| a result that changes when one documented environment variable is set | **tested and not found** — the same run; the finding is the *absence* of this hazard, not a filing of it |
| a guard that reports success while executing no assertion body | `TST-004` |
| a restoration mechanism layered over one the framework already provides | none found; `test_progress_display.py:283-313`'s manual `signal.signal` save-and-restore is a *second* barrier, not a duplicate |
| a test whose documentation names a subject the code no longer contains | `TST-004` |
| an identifier shared with another phase's prefix, or a form no phase uses | `TST-015` |
| a test that, to pass, required the code to be wrong | none found — and the project rule is respected throughout: no finding in this report asks for production code to change to suit a test |
| randomness and ordering dependence not yet bitten, filed as absence | none found |
| an absent coverage gate where the number looks acceptable | `TST-005` |
| a body no test names that nevertheless executes | **checked and not found** — this is the row that would turn an honest coverage number into an invented one; the missing-line sets in this run were dumped per module and every cited range was confirmed *present in the missing set*, never merely uncited |
| two runs that agree because the environment was never varied | **not committed by this run** — Checkpoint 1 varies three documented environment variables and the 89 % is unchanged, and the report's own R5 row does the same |
| an artefact the audit's own tooling leaves behind, untracked and un-ignored | not found. All scratch went to `.temp/val10/` and all `COVERAGE_FILE` values were redirected there; no `.coverage*` file exists anywhere in the tree outside the worktrees and the venv |

- **Every finding re-measured or re-read, in this order:** 16 of 16. Five were reproduced
  end-to-end against real product code (`TST-001`, `TST-002`, `TST-003`, `TST-009` by
  direct probe, `TST-005`'s workflow claim by reading both workflows), eleven were confirmed
  against this run's per-statement coverage output or a direct re-count of the named sites.
- **Every cross-phase claim opened:** `TRN-001` (05), `SEC-009` (06), `NET-001` (03),
  `CFG-003` (02), `OUT-002` (08), `ART-007` (07), `SEC-006` (06), `CON-001` (04),
  `ENT-002`/`ENT-003` (01), `DEP-001`/`DEP-002` (11), `VAL-105` (01 store). Each was read,
  not taken from the report's characterisation of it.

---

## Checkpoint 4 — R4 Dependency and Rollout-Safety Analysis

- **Stage:** R4 Dependency and Rollout-Safety Analysis
- **Findings in scope:** 16 source findings + 6 `VAL-` findings
- **Checklist against R4's four questions, answered in order:**

**1. Do the fixes break anything already in the product?** No finding in this report
proposes a change to production code, and that is the correct scope for this phase: the
project's binding rule is that production code is king and a test is never distorted to suit
it, so a test-coverage phase's fixes land in `tests/`, in `.github/workflows/`, in
`pyproject.toml`, and — for the six `VAL-` findings — in the audit's own documents. Where a
product fix is required, the owning phase filed it and this report cross-references it
rather than restating it. The two findings that read as if they touch product code do not:
`TST-001`'s recommendation changes the *assertions*, not `downloader.py:303`, and `TST-004`'s
recommendation renames a test and moves two comments.

**2. A fix that breaks something already in the product or the suite.** Three.

- **`TST-003` is not independent of `NET-001`, and applying it first changes what
  `NET-001`'s fix has to reconcile.** `TST-003`'s recommendation is to add a test that
  proves every original segment survives a failed final merge. On today's product **no such
  test can pass** — the measurement is 0 of 250 segments surviving, with only
  `final_list.txt` left. So the test must be written expecting failure, and
  `NET-001`'s product fix is what turns it green. Applying the two in the other order makes
  `NET-001`'s fix look like a behaviour change that removed a guarantee the suite had
  already stopped checking. **The order that works: `TST-003`'s test first (red), then
  `NET-001`'s fix.** Both orderings terminate safely — a red test is caught, not shipped —
  so this is a sequencing note, not a blocker.
- **`TST-002` and `SEC-009` have the same shape and the same safe order.** The host-only
  cookie test is written first and fails with `LoadError`; `SEC-009`'s fix — deriving the
  include-subdomains flag from the domain at `cookies.py:78` — turns it green. The reverse
  order makes the product fix look like it is chasing a test.
- **`TST-005` and `DEP-002` target the same two lines of the same file and prescribe the
  same step.** This is the one place where the wrong order is a *conflict* rather than a
  red test, and it is filed as `VAL-125`. **Do not land both.** `DEP-002` absorbs.

**3. A fix that cannot be ordered safely because a prerequisite of it is itself a
finding.** One candidate was raised and **withdrawn on the evidence**, and the withdrawal is
recorded so a second run does not re-file it. The candidate was `TST-001`: its recommended
real-process-crossing test targets "this specific body", and phase 05's `TRN-001` is going
to change what that body is, so the test looked order-dependent. It is not.
`TST-001`'s own recommendation is to *"assert the ffmpeg outcome, not the argv spelling"*,
which is transport-agnostic: a real-crossing test written today returns 0 only after
`TRN-001` lands, and passes unchanged after it. Both orders are correct, so no dependency
is filed. One residual is recorded without a finding: if the *demotion* half of `TST-001`'s
recommendation lands before `TRN-001`, the argfile path has no test at all in the interim.
That is an interim coverage regression, not a broken end state, and it is the validator's
note to whoever sequences the two — not a finding.

**4. A verification dependency one fix has and another lacks.** One. `VAL-121` is the
input every other verification in this pipeline depends on: without a slot for a decision in
the report format, a run's conclusions exist only in the artefact that produced them and
cannot be read back, cited or re-checked. It is the cheapest fix in this report and it
gates the value of all the others.

**Backwards compatibility.** Nothing in this report changes a public interface, a CLI
surface, a configuration key, a sdist or wheel entry, or a product behaviour. The
packaging-relevant change is confined to `test_packaging.py:177-188`, and it removes one
entry from a list a test asserts against; `BUILDER_ADDED_SDIST_ENTRIES` and
`EXPECTED_WHEEL_ENTRIES` are untouched, so the wheel manifest test is unaffected.

---

## Validation Summary

Sixteen findings in scope; sixteen decisions; six findings filed against the audit inputs.

| # | ID | Decision | Severity | Type | Classification |
|---|---|---|---|---|---|
| 1 | `TST-001` | validated | CRITICAL | `SPEC-DEVIATION` | mandatory |
| 2 | `TST-002` | validated | CRITICAL | `SPEC-DEVIATION` | mandatory |
| 3 | `TST-003` | validated | CRITICAL | `SPEC-DEVIATION` | mandatory |
| 4 | `TST-004` | **reclassified** | HIGH | `SPEC-DEVIATION` | **mandatory** *(was advisory)* |
| 5 | `TST-005` | **reclassified** | HIGH | **`SPEC-DEVIATION`** *(was `BEST-PRACTICE`)* | **mandatory** *(was advisory)* |
| 6 | `TST-006` | validated | HIGH | `SPEC-DEVIATION` | mandatory |
| 7 | `TST-007` | validated | HIGH | `BEST-PRACTICE` | advisory |
| 8 | `TST-008` | validated | HIGH | `SPEC-DEVIATION` | advisory |
| 9 | `TST-009` | validated | MEDIUM | `SPEC-DEVIATION` | advisory |
| 10 | `TST-010` | validated | MEDIUM | `SPEC-DEVIATION` | advisory |
| 11 | `TST-011` | validated | MEDIUM | `SPEC-DEVIATION` | advisory |
| 12 | `TST-012` | validated | MEDIUM | `SPEC-DEVIATION` | advisory |
| 13 | `TST-013` | validated | MEDIUM | `SPEC-DEVIATION` | advisory |
| 14 | `TST-014` | validated *(working tree only — see its note)* | MEDIUM | `SPEC-DEVIATION` | advisory |
| 15 | `TST-015` | validated | LOW | `DOC-UPDATE` | advisory |
| 16 | `TST-016` | validated | LOW | `SPEC-DEVIATION` | advisory |
| 17 | `VAL-120` | **filed** | CRITICAL | `SPEC-DEVIATION` | mandatory |
| 18 | `VAL-121` | **filed** | MEDIUM | `SPEC-DEVIATION` | mandatory |
| 19 | `VAL-122` | **filed** | MEDIUM | `SPEC-DEVIATION` | mandatory |
| 20 | `VAL-123` | **filed** | HIGH | `SPEC-DEVIATION` | mandatory |
| 21 | `VAL-124` | **filed** | MEDIUM | `SPEC-DEVIATION` | mandatory |
| 22 | `VAL-125` | **filed** | MEDIUM | `SPEC-DEVIATION` | advisory |

### Rejected Findings

**None.** No finding in this report was rejected, because none was found to be
unreproducible, stylistic, or already-correct-by-design. Every claim that could have been
dismissed as over-filing was re-derived first: `TST-014` is valid but volatile, `TST-015`
is valid but the lowest-consequence item in the report, `TST-013` is valid and its
`mandatory` promotion was considered and **declined** on the record rather than left
unexamined, and one `VAL-` candidate of this run's own (an ordering blocker between
`TST-001` and `TRN-001`) was **withdrawn** because the finding's own recommendation is
transport-agnostic.

| ID | Title | Rejection reason | Retained content |
|---|---|---|---|
| — | — | — | — |

### Merged Findings

**None.** The one merge candidate in the corpus, `TST-005` / `DEP-002`, is **not merged**
here: it spans two reports, the second report's validator has not run, and `99-audit-validate.md:349`
puts the absorbing decision in the run that can see both sides. It is filed as `VAL-125`
with its recommendation, and it is listed under Merge Candidates in Checkpoint 2.

| New ID | Title | Merged from | Inherit link |
|---|---|---|---|
| — | — | — | — |

### Reclassified Findings

| ID | Field | From | To | Why |
|---|---|---|---|---|
| `TST-004` | `Classification` | `advisory` | `mandatory` | The subject is not a missing test but a test that **asserts coverage of a security guard it never reaches**, in a class docstring that is the only record of what is covered. The template's guide puts security and correctness in `mandatory`. |
| `TST-005` | `Type` | `BEST-PRACTICE` | `SPEC-DEVIATION` | `.ai/context/commands.md:15` and `docs/01-tools/installation.md:91` declare `uv run pytest tests/` as the project's own verification; a job that runs one module of twenty-one contradicts that declaration. `BEST-PRACTICE` requires a *defensible* arrangement with a gap. |
| `TST-005` | `Classification` | `advisory` | `mandatory` | This absence is what makes all 239 missed statements and all three CRITICAL oracles permanent; it is the gate the rest of the report's fixes depend on. Converges with `DEP-002`. |

### Mandatory Fixes

Everything classified `mandatory`, in the order a maintainer should take it.

1. **`VAL-120`** — strike the log-file non-reproduction from the phase-10 report and replace
   it with the measured shape table. `OUT-002` stands. Two validated reports currently
   disagree about whether the product writes parseable JSON when it logs a failure.
2. **`TST-001`** — demote the three argv-shape assertions to the secrecy claim they actually
   check, and add one test that crosses the process boundary with the real muxer and asserts
   the **outcome**, not the argv. Phase 05's `TRN-001` owns the transport fix; do not
   duplicate it here.
3. **`TST-002`** — add the host-only domain shape to the cookie builders. This is the
   shape `tests/test_extractor.py:227` and `tests/test_hls_downloader.py:1033` already
   build and never load. Write the test before `SEC-009`'s fix; the test fails until then,
   and that is the point.
4. **`TST-003`** — one test proving every original segment survives a failed final merge.
   It cannot pass today (0 of 250 survive). Write it red, then let `NET-001` turn it green.
5. **`TST-004`** — rename `test_validate_output_path_rejects_traversal_even_if_resolved` to
   the pre-resolution guard it actually asserts, move the two misleading comments onto that
   guard, and say in the class docstring that the post-resolution guard has no oracle on
   this platform. **Do not attempt the first recommendation in the report:** `..` does not
   survive `Path.resolve()` in any of the five constructions measured here, and the symlink
   constructions need elevation.
6. **`VAL-123`** — make the validator gate evaluable and derive the closing output's counts
   from the artefacts that exist.
7. **`TST-005`** (absorbed by `DEP-002`, see `VAL-125`) — one step that runs the suite, plus
   the one element only this report carries: no coverage tool is declared in
   `[dependency-groups] dev` and no threshold exists, so the 89 % figure has nothing to
   regress against.
8. **`TST-006`** — the `aiohttp` body has **zero** references in the test tree, and it
   carries the TLS switch at `segment_downloader.py:539-543`. Substitute the
   `aiohttp.ClientSession` the module imports at its own name and the boundary is
   substitutable; the 67 missing statements are a consequence of not doing so.
9. **`TST-013`** — one platform-independent oracle for the `0o600` claim: substitute
   `os.chmod` itself and assert the call is made with `0o600`. The four POSIX-only oracles
   are honest and correct; they are simply not oracles on the platform this project
   develops on.
10. **`VAL-121`** — add the decision slot to the template and add `RUNTIME-ERROR` to both
    role files. Four lines, and 13 already-published findings become legal against the
    vocabulary the roles carry.
11. **`VAL-122`** — point the orchestrator at `.kilo/rules/project.md` and
    `.kilo/rules/commands.md` instead of a root `AGENTS.md` that does not exist.
12. **`VAL-124`** — add the audit-corpus, phase-catalogue and worktree exemption to
    `audit-orphaned.md`'s protect-list, in the command's own words, so the next census does
    not offer to delete 214 files of the audit's own history.

### Advisory Recommendations

- **`TST-007`** — the finding's own counter-example is the fix: patch
  `vkdownloader.services.downloader_throttle.asyncio.wait_for` the way
  `tests/test_downloader_throttle.py:522`, `:626` and `:642` already do, on the fixture
  model the class at `test_cli.py:1465-1473` already documents, in the same file as the 24
  `cli.Settings` patches. The capability exists; only the convention is missing.
- **`TST-008`** — six lines, copying the pattern already at `test_cli.py:935`, against a
  real module-level structlog `logger`. The cheapest HIGH in the report.
- **`TST-009`** — add one environment-file-path case: `maxretries` must suggest
  `VKDOWNLOADER_MAX_RETRIES`. The existing disjunction at `test_config.py:312` cannot fail
  and the product cannot currently pass.
- **`TST-010`** — declare `asyncio_mode` and the root directory. 174 markers currently
  depend on the installed plugin's default.
- **`TST-011`** — drop `"tests/integration/__init__.py"` from
  `test_packaging.py:118` and delete the directory, or write the tests. A tier that
  contributes 0 of 502 and is asserted into the release artefact is a promise the
  packaging gate is enforcing.
- **`TST-012`** — the two `signal.signal` read-backs become real oracles by asserting
  against a recorded previous handler, and the no-loop fallback at
  `signal_handlers.py:52-54` gets a test. What is **`UNVERIFIED`** is that real signal
  registration and real restoration work; nothing observed it fail.
- **`TST-015`** — rename the three `TST-` sites, and widen the recommendation by one line
  to cover the two `VAL-105` sites the report lists but does not prescribe for. Both point
  into `.ai/`, which the sdist forbids, so in the released artefact every one of them
  resolves to nothing.
- **`TST-016`** — eight degradation arms: the report is right that the cost/benefit is thin
  and the severity is right at LOW. Not worth a plan of its own.
- **`VAL-125`** — let `DEP-002` absorb the workflow change; do not land both.

### Doc Updates Needed

- **`TST-015`** is the only `DOC-UPDATE` in the report: the three `TST-` references in the
  test tree, plus the two `VAL-105` references its recommendation does not yet cover.
- **`VAL-122`** and **`VAL-123`** are changes to the audit pipeline's own instructions, and
  both leave the pipeline's documented behaviour different from what it does: the
  orchestrator currently claims to read a file it does not have, and to report validation
  coverage it never determines.
- No documentation in `docs/` is wrong because of any finding in this report.

---

**The source report's own `## Summary`, `## Mandatory Fixes`, `## Advisory Recommendations` and `## Doc Updates Needed` sections are not duplicated here.** Every finding-level claim they summarise is retained above, and the decision-bearing version of all four sections is the Validation Summary above. Carrying both would give the corpus two severity sets for one report.
