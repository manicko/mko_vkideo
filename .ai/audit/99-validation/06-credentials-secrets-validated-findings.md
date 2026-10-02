# Phase 06 Audit Findings — Credentials and Secrets

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/06-audit-credentials-secrets.md`
**Status:** complete
**Validated:** yes

> **Deviation from the report format, stated once here.** The template
> (`.ai/audit/templates/audit-findings.md`) defines nine mandatory fields per finding
> (`:64-74`) and none of them carries a validation decision — its finding block runs from
> the heading straight into the field table (`:19-33`). The `Validation Note` this phase is
> required to attach to **every** decided finding therefore has no slot. It is written
> directly below each `### {ID}:` heading, above the field table. The absence of the slot
> was filed as `VAL-001` by the `02` validation run and is not re-filed here. This is the
> only deviation from the format in this artifact.
>
> **How the decisions were reached.** Every finding was re-derived from the artifact it
> names and from the installed dependencies, not from the report's own wording. Ten
> findings, ten decisions, three `VAL-` findings against the audit inputs themselves. No
> source file was modified and no finding was deleted; every retained claim and every
> correction is recorded in place.

---

## R0 — Corpus map, identifier map, decision-record map

Recorded before any check, because these three are the ways this phase manufactures a clean
bill of health. Searched with `.ai/` as the scope, excluding `.kilo/worktrees/`.

**Corpus map.** The phase range is `01`–`11` plus this file.

| Phase | Handbook | Findings file | Validation store | State |
|---|---|---|---|---|
| 01 entry/architecture | `01-audit-entry-architecture.md` | `01-entry-architecture/findings.md` | present | validated |
| 02 configuration | `02-audit-config.md` | `02-config/findings.md` | present | validated |
| 03 network/resilience | `03-audit-network-resilience.md` | `03-network-resilience/findings.md` | present | validated |
| 04 concurrency/cancellation | `04-audit-concurrency-cancellation.md` | `04-concurrency-cancellation/findings.md` | present | validated |
| 05 subprocess/browser | `05-audit-subprocess-browser.md` | **absent** | — | gap: a handbook with no findings file, and no `AUDIT COMPLETE` for it. The phase was not offered to this run and is **not** validated here. |
| 06 credentials/secrets | `06-audit-credentials-secrets.md` | `06-credentials-secrets/findings.md` | — | **the file this run validates** |
| 07–11 | present | all absent | — | not yet run; out of this run's scope |
| 99 validation | `99-audit-validate.md` | — | this file | running |

No findings file exists outside the `01`–`11` range; there is no corpus drift to report.

**Identifier map.** Live prefixes in the corpus: `ENT` (01), `CFG` (02), `NET` (03), `CON`
(04), `SEC` (06), `VAL` (99). No prefix is unclaimed. Every `SEC-` identifier this run
adjudicates is owned by phase 06, and every `ENT`/`CFG`/`NET`/`CON` identifier cited in the
source report as a cross-reference was opened and confirmed to exist in the owning phase's
file.

**One collision, already filed, not re-filed.** `VAL-` is minted independently by every
per-phase validation run, and two unrelated subjects already carry the identifier
`VAL-001`: the missing decision slot (`02-config-validated-findings.md:962`) and the
cross-phase connection-ceiling conflict (`03-network-resilience-validated-findings.md:1344`).
The collision is already filed as `VAL-112` in the `01` validation store (`:1236`), and the
`04` run escaped it by switching to `VAL-4xx`. This run continues that escape and mints
**`VAL-6xx`**, so a fifth meaning is not added to `VAL-001`.

**Decision-record map.** The report format has no slot for a decision
(`.ai/audit/templates/audit-findings.md:19-33`, `:64-74`) — an **absent slot**, recorded
here and satisfied by the deviation paragraph above, not a missing decision. All ten
findings carry a `Validation Note`; the tally at the end of this artifact reconciles against
ten records.

---

## Checkpoint 1 — R1 Copy Source Findings

- **Stage:** R1 Copy Source Findings
- **Findings in scope:** 10 (SEC-001 … SEC-010)
- **Evidence anchor:** this file, self-contained — every finding's original text, evidence
  and recommendation is retained below, above its decision record. The source report
  `.ai/audit/06-credentials-secrets/findings.md` was opened read-only and is unmodified.
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 2 — R2 Cross-Finding Analysis

- **Stage:** R2 Cross-Finding Analysis
- **Findings in scope:** 10
- **Cross-phase conflicts:** 0
- **Merge candidates:** 0 — see the complement analysis in `SEC-005`'s Validation Note
- **Checkpoint status:** closed

## Checkpoint 3 — R3 Validate Each Finding

- **Stage:** R3 Validate Each Finding
- **Findings in scope:** 10 (Validated 7, Reclassified 3, Merged 0, Rejected 0)
- **Evidence anchor:** the per-finding `Validation Note` on each block below; every note
  names the artifact read and the re-derived fact
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 4 — R4 Assess Rollout Safety

- **Stage:** R4 Assess Rollout Safety
- **Unsafe-ordering count:** 1 (filed as `VAL-602`)
- **Findings added:** 3 (`VAL-601`, `VAL-602`, `VAL-603`)
- **Checkpoint status:** closed

---

## Baselines re-verified this run

Re-run, not inherited. These are the state the decisions were observed against.

| Command | Result |
|---|---|
| `uv run pytest tests` | **486 passed, 4 skipped** in 25.68s — exit 0 |
| `uv run ruff check src tests` | `All checks passed!` — exit 0 |
| `uv run ruff format --check src tests` | **exit 1** — `Would reformat: src\vkdownloader\services\downloader.py`, `Would reformat: src\vkdownloader\services\batch_downloader.py`; 50 files already formatted. Clean on the tree this run started on; broken by the in-flight fix described above. |
| `uv run mypy src` | `Success: no issues found in 30 source files` — exit 0 |
| `uv run pytest "tests/test_hls_downloader.py::TestCreateTempCookieFile" -q -rs` | 5 passed, 1 skipped — the skip is the mode oracle (`SEC-003`) |
| `uv run pytest tests/test_hls_downloader.py -q -rs -k "permissions_are_0600"` | 2 skipped, 135 deselected |
| `uv run pytest tests/test_config.py -q -rs -k "permissions"` | 2 skipped, 29 deselected |

The source report's stated baselines are exact.

**The tree changed under this run — read this before any line number in this artifact.**
The working tree was **not** the tree this run started on. Partway through, an in-flight
fix for phase 02's `CFG-001`/`CFG-002` landed in `src/vkdownloader/cli.py`,
`src/vkdownloader/services/downloader.py` and `src/vkdownloader/services/batch_downloader.py`
(this run made no source change; `git status` shows those three files and
`tests/test_batch_downloader.py` as `M` against `HEAD`, and none of them is this run's work).
Every decision below was re-verified **after** that change landed, and the two consequences
are stated here rather than left implicit:

1. **The source report's reachability gate is now stale.** It rested entirely on `CFG-001`.
   That defect is fixed in the current tree, so the gate's stated reason is false. The
   correction is in the cross-reference section below; it applies to the `Reachability`
   field of six findings and changes no decision, but it changes what a reader should
   expect.
2. **The `ruff format` baseline is no longer clean.** `src/vkdownloader/services/downloader.py`
   and `src/vkdownloader/services/batch_downloader.py` would be reformatted — the in-flight
   edit lost the parameter alignment on `settings: Settings`. `pytest`, `ruff check` and
   `mypy` are all still clean. The table above records the tree as it stands, not as the
   source report recorded it.

All `cli.py` and `batch_downloader.py` anchors in this artifact are **current-tree** line
numbers. Every anchor in `cookies.py`, `config.py`, `ytdlp_downloader.py`, `downloader.py`
(down to `:555`), `ffmpeg_utils.py`, `extractor.py`, `segment_downloader.py`, `dtos.py`,
`url_sanitizer.py` and both test files was re-measured and is unchanged from the source
report's citations.

**Environment as measured, not as declared.** Windows 11 / `os.name == "nt"`, CPython
3.12.1, `yt_dlp` 2026.07.04 (`C:\py_exp\mko_vkideo\.venv\Lib\site-packages\yt_dlp`),
`http.cookiejar` from `C:\Program Files\Python312\Lib\http\cookiejar.py`. No real credential
was used anywhere in this run and none was written to disk; every value was a `SYNTHETIC-*`
string, a `.invalid` host or a loopback address. All harnesses lived under the gitignored
`.temp/validate06/` and were removed afterwards. No production code was modified.

---

## Cross-references re-opened and confirmed this run

The source report's own cross-reference section is retained below, under its original
heading, after the finding blocks. This section is the validation record: every claim the
source report attributes to another phase was checked against that phase's file, and the
result of the check is what is written here.

Cited and re-opened, not re-filed. Each was checked for the claim this report attributes to
it, and the check is recorded so the next run does not repeat it.

- **ENT-001** (phase 01, HIGH, confirmed) — records emitted before `structlog.configure`
  reach structlog's default stdout sink. **The phase's negative result is confirmed, and
  the confirmation is the point.** The complete pre-sink window is: import time, then
  `warn_unknown_env_vars()` at `cli.py:125` / `:237`, then `Settings(...)` at `cli.py:127` /
  `:239`, and `setup_logging(settings)` at `cli.py:128` / `:240`. Exactly two records are
  emitted in that window and neither carries a credential:
  `config.py:145` `logger.debug("download_dir_empty_string_using_default")` has **no fields
  at all**, and `config.py:314-319` `logger.warning("unknown_env_var_ignored", …)` carries
  `var=<the variable name>`, `valid_vars=sorted(valid_env_vars)` (a sorted list of known
  *names*) and one static `hint` string — never a value, a path, an address or a session.
  Two further checks close the window: **no module-level `logger.*` call exists anywhere in
  `src/`**, so nothing is emitted at import; and `_log_env_file_path()` — the only other
  pre-download record — is called at `cli.py:171` / `:287`, i.e. *after* `setup_logging`
  (`cli.py:169` / `:285`), and the browser that mints cookies is started inside
  `asyncio.run(_download())` at `cli.py:172`, also after. **No credential-bearing pre-sink
  record exists, so nothing was under-filed on ENT-001.** The source report's cross-reference
  is accurate and complete.
- **CFG-001** (phase 02, validated HIGH) — `VKDOWNLOADER_SSL_VERIFY` /
  `VKDOWNLOADER_COOKIE_SOURCE` unreachable from the environment. **Its premise was true when
  this report was written and is false in the tree this validation ran on.** When the source
  report was written, `cli.py` read `settings = Settings(cookie_source=cookie_source,
  ssl_verify=ssl_verify)` at `:127` / `:239` with unconditional keyword arguments and Typer
  defaults of `CookieSource.NONE` / `True`. The current tree instead has
  `_build_settings(cookie_source=…, ssl_verify=…, max_retries=…)` at `cli.py:166` / `:282`,
  backed by options declared `CookieSource | None = typer.Option(None, …)` at `:109` / `:250`,
  so an unsupplied option occupies no configuration source. Re-measured here, both ways:
  `VKDOWNLOADER_COOKIE_SOURCE=browser` in the process environment with no `.env` yields
  `Settings().cookie_source == browser` and `ssl_verify == False`; the same two lines in a
  `.env` file with a clean environment yield the same; and through the real Typer entry point
  with a `.env` and no flags the process constructs settings and proceeds to
  `Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}`
  (exit 1) with no configuration error. **The credential path is no longer reachable only
  through a command-line flag.**

  **What this changes and what it does not.** The `Reachability` value on `SEC-001`,
  `SEC-002`, `SEC-003`, `SEC-004`, `SEC-006` and `SEC-009` — *"OPT-IN — `--cookie-source
  browser`"* — and the report's header gate that asserts it are both wrong as written: the
  trigger is now `--cookie-source browser` **or** `VKDOWNLOADER_COOKIE_SOURCE=browser` **or**
  that line in a `.env` file. The **class** of reachability is unchanged and no decision in
  this artifact moves, because the path is still opt-in in the sense that matters: an
  operator has to ask for it deliberately, and a `.env` line is at least as deliberate a
  request as a typed flag. The practical exposure is if anything marginally *higher*, not
  lower — a line in a `.env` file that has been there for months is less likely to be in
  the operator's mind at the moment of a download than a flag they just typed, and `.env` is
  a file people forget they created. A reader who wants to reproduce any OPT-IN row should
  use the `.env` route, not the flag.
- **NET-004** (phase 03) — cited in `SEC-010`'s evidence. Re-opened: the phase's own title
  is *"A refreshed signed address is used for the manifest only — every media part is still
  requested from the stale host, with the fresh cookie"* (`03-network-resilience/findings.md:242`).
  The attribution in this report is not inverted. Cited, not re-derived.
- **Phase 05** (subprocess/browser) — absent from the corpus (see the corpus map above).
  The mechanical facts `SEC-005` cites about the child's invocation convention were read at
  their source rather than taken on trust: `ffmpeg_utils.py:29-63` `iter_process_lines`
  yields raw `bytes` lines and applies no transform, and the two consumers at
  `ytdlp_downloader.py:650-655` and `:663-669` decode and hand the line straight to
  `_echo_ytdlp_line`. Because phase 05 produced no findings, nothing here is filed against
  it; the surface `SEC-005` names is a *sink* decision, which is this phase's subject.
- **Phase 09** (code quality / comment wording) — the comment texts quoted throughout are
  re-read as evidence and each is quoted verbatim in the corresponding `Validation Note`,
  because two of them turn out to decide a finding's type.
- **Phase 10** (test suite) — `SEC-003` is a missing-oracle finding about a credential
  guarantee. Its ownership is contested in the source report's own text ("the *style* of the
  guard is phase 10's subject; the missing guarantee is this phase's"). The boundary is
  stated on both sides of the `99` handbook (`## 6`) and phase 10 has not run, so the claim
  is neither confirmed nor refuted here; it is cross-referenced and no `VAL-` is filed for
  it, because a contested boundary between a phase that has not run and one that has is not
  two phases asserting incompatible facts.
- **Phase 11** (ignore coverage) — the credential artefact `vk_cookies_*.cookies.txt` is
  noted in the source report as a candidate path for phase 11. Nothing about the answer is
  filed here.

---


**Reachability gate (stated on every finding below).** `Settings.cookie_source`
defaults to `CookieSource.NONE` (`config.py:115-118`; `cli.py:71-76`, `:209-214`),
and CFG-001 (phase 02, already filed — cited, not re-filed) establishes that
`VKDOWNLOADER_COOKIE_SOURCE` can never win because `cli.py:127`/`:239` pass
`cookie_source` as an unconditional constructor keyword. Measured with R11(b):

| Credential-bearing subject | Gate |
|---|---|
| credential artefact on disk (`vk_cookies_*.cookies.txt`) | **OPT-IN** (`--cookie-source browser`) |
| credential path in the yt-dlp argv | **OPT-IN** |
| signed m3u8 + credential path in the ffmpeg argfile | **OPT-IN** |
| flat session in `headers["Cookie"]` on an ordinary segment GET | **OPT-IN** |
| flat session in `headers["Cookie"]` after a forced token refresh | **DEFAULT — reachable** |
| raw exception text carrying a signed address into the log | **DEFAULT — reachable** |
| child stderr echo reaching the terminal untransformed | **DEFAULT — reachable** |

**Platform note (Windows, the declared development platform).** The `0o600`
mode-setting call has no effect here and the effective access state is a DACL,
not a mode. Both are handled by measurement, not by assertion. The enforcement
outcome of `0o600` on a POSIX host is **UNVERIFIED** and is not claimed anywhere
in this report.

**Baselines (R11(a) — cited as the state in which findings were observed, never
filed as findings).** `uv run pytest tests` → 486 passed, 4 skipped, exit 0.
`uv run ruff check src tests` → exit 0. `uv run ruff format --check src tests`
→ 52 files already formatted, exit 0. `uv run mypy src` → no issues in 30
files, exit 0.

**Synthetic values only.** Every value used in this phase was generated for the
run (`SYNTHETIC-*` values, `vkvideo.ru` / `*.example.invalid` / `127.0.0.1`
addresses, `.invalid` hosts). No real credential was used, and none was
obtainable. Every finding below is a **route**, never an observed live token.

---

## Findings

### SEC-001: The credential artefact's requested access mode and its measured access state differ, the product's only control is a no-op on this platform, and nothing else in the tree confines it
> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** The measurements are exact and were re-taken independently; the *justification* is not, and it is the justification that carries the type. On this platform `0o600 & stat.S_IWRITE == 0o200`, and CPython's Windows `os.chmod` sets `FILE_ATTRIBUTE_READONLY` only when the write bit is **absent**. Measured on a fresh `mkstemp` file: before `os.chmod(path, 0o600)` → `mode=0o666 FILE_ATTRIBUTE_READONLY=False raw_attrs=0x20`; after → `mode=0o666 FILE_ATTRIBUTE_READONLY=False raw_attrs=0x20`. The contrast case proves the mechanism rather than asserting it: `os.chmod(path, 0o444)` → `mode=0o444 FILE_ATTRIBUTE_READONLY=True raw_attrs=0x21`. `_create_temp_cookie_file`, `_temp_argfile` (`downloader.py:111-119`) and the log-file branches (`config.py:353-356`) all measure `0o666` after their call. The exhaustive search holds: no `atexit`, no `icacls`/`setfacl`/`win32security`, no `chown`, no `umask`, no `mkdtemp`, no `0o700`, no manual `O_CREAT|O_EXCL` anywhere in `src/`; the only three `chmod` calls are the three artefacts themselves.
>   **Why the stated ground fails.** The finding rests on "its own comment claims that on Windows *os.chmod toggles only the read-only attribute*. For `0o600` that is not what happens." The comment is at `ytdlp_downloader.py:78-81` and reads in full: *"0o600 sets POSIX permission bits: on Windows os.chmod toggles only the read-only attribute, **so the owner-only guarantee is not offered there (D-11)** and the mode is requested for its POSIX effect only."* The claim is about the **scope** of what `chmod` can express on Windows, not an assertion that `0o600` produces a read-only file — and the conclusion it draws is precisely what happens. `config.py:347-352` says the same and more explicitly: *"on Windows `touch(mode=…)` ignores the mode and `chmod` toggles only the read-only attribute, so both branches leave the file readable by any local user. Confinement is not offered there (D-11); the mode is requested for its POSIX effect only, and no access control list is applied."* The comment is accurate. There is no declared rule the implementation violates, so `SPEC-DEVIATION` cannot stand.
>   **What survives, and one correction to the evidence.** The real, product-owned gap is that the artefact's confidentiality has **no** product-side control on the declared platform and rests entirely on a DACL inherited from an ambient environment variable the product never reads or validates (`TEMP`/`TMP`/`TMPDIR`; the product reads none of them). That is a defensible arrangement with a demonstrated gap — `BEST-PRACTICE` — not a spec deviation. And the R1(f) DACL claim is **incomplete on this machine**: the default `%LOCALAPPDATA%\Temp` grants FullControl to **four** principals, not the three reported — `NT AUTHORITY\SYSTEM`, `BUILTIN\Administrators`, the signed-in user, and an unresolvable domain SID `S-1-5-21-1349043128-2017649962-599581075-1764` (the domain trust failed, so `icacls` could not translate it). The direction of the claim holds — no `Everyone`, no `BUILTIN\Users`, no `Authenticated Users` — so the default path is inherited-confined, and the wide-DACL case arises only when the operator relocates `TEMP`, which is the auditor's own second experiment and the operator's own directory. On that evidence the default-path consequence is smaller than the finding's *Consequence* paragraph states.
>   **Severity re-derived from this run's own evidence: HIGH → MEDIUM** (reclassified; the decision is not the severity). Reachability is opt-in, and the observed default-path access state is confined by inheritance to a three-principal-plus-domain-SID DACL.
>   **Reachability, current tree:** the retained `Reachability` value reads *"OPT-IN — `--cookie-source browser`"*. Its stated reason (`CFG-001`) is fixed in the tree this run validated against, so the trigger is now also `VKDOWNLOADER_COOKIE_SOURCE=browser`, or that line in a `.env` file. Same class, no decision change — see the reachability-gate correction in this artifact's header.
> - **See also:** `SEC-002` — the same artefact, and the two recommendations are **not co-applicable**: see `VAL-602`. `SEC-003` — the test oracles for this same `0o600` request. `SEC-004` — the same path on a second surface. The comment-wording residue at `ytdlp_downloader.py:75-77` ("tempfile.mkstemp creates files subject to the process umask (typically 0o644 on Unix)") is inaccurate for CPython, whose `_mkstemp_inner` opens with `0o600`; that makes the `os.chmod` at `:82` redundant on POSIX. It is a wording defect owned by phase 09, not filed here.

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |
| **Reachability** | OPT-IN — `--cookie-source browser` (R11(b) GATE 1: at `cookie_source=none` the artefact is not created and `--cookies` is absent from the argv) |

**Description:** The borrowed session is written to `vk_cookies_*.cookies.txt` in
the system temp directory. The code requests mode `0o600` at
`ytdlp_downloader.py:82` (and for the sibling argfile at `downloader.py:119`),
and its own comment claims that on Windows "os.chmod toggles only the read-only
attribute". For `0o600` that is not what happens: `0o600 = S_IRUSR | S_IWUSR`,
so the write bit is **present** and Windows does not set the read-only
attribute either. The call changes nothing at all. The measured state is
whatever `tempfile.mkstemp` produced, and the only confinement is the temp
directory's inherited DACL — which the product never inspects and which the
operator can relocate with `TEMP`/`TMP`/`TMPDIR`. On POSIX the enforcement
outcome is **UNVERIFIED** and is not claimed.

**Evidence (R1 a/b/c/d/e/g, obtained out of band; requested and measured
recorded as two distinct values, never collapsed):**

```
R1(e)  0o600 & stat.S_IWRITE (0o200) = 0o200  -> the WRITE bit is PRESENT
       before chmod: mode=0o666 attrs=0x20
        after chmod: mode=0o666 attrs=0x20
       DELTA: NONE - the call changed nothing
```

| Artefact | Call site | Requested | Measured (this machine) |
|---|---|---|---|
| `vk_cookies_*.cookies.txt` (the credential) | `ytdlp_downloader.py:82` | `0o600` | `0o666` |
| `vk_ffmpeg_*.args` (signed m3u8 + credential path) | `downloader.py:119` | `0o600` | `0o666` |
| log file | `config.py:354`, `config.py:356` | `0o600` | `0o666` |

R1(c) — per-family confining-control call counts in `src/`, exhaustive:

```
os.chmod / Path.chmod (mode-based)          : 3  (config.py:356, downloader.py:119, ytdlp_downloader.py:82)
umask / creation mask                        : 1  (a comment only, ytdlp_downloader.py:76)
ACL (icacls / setfacl / win32security)       : 0
Windows security descriptor (DACL/SDDL)      : 0
ownership change (chown)                     : 0
manual O_CREAT|O_EXCL                        : 0
private-directory mode 0o700                 : 0
mkstemp / mkdtemp (O_EXCL, private creation) : 3  (all three are the artefacts themselves)
```

R1(f)/R1(d) — measured access state, i.e. the DACL, which is what actually
confines the file. Under the default `%LOCALAPPDATA%\Temp` the artefact
inherits three principals and nothing wider: `NT AUTHORITY\SYSTEM:(I)(F)`,
`BUILTIN\Administrators:(I)(F)`, `<the signed-in user>:(I)(F)`. No `Everyone`,
`Users` or `Authenticated Users` entry.

R1(g) — the confinement is inherited, not delivered, and the directory is chosen
by ambient environment. `tempfile.gettempdir()` resolves `TMPDIR`, `TEMP`, `TMP`
in that order on Windows; the product reads none of them. Driving the product's
own `_create_temp_cookie_file` after `TEMP` was pointed at a directory inside
this repository:

```
after operator sets TEMP=<repo>/.temp/out/shared_temp:
tempfile.gettempdir() = <repo>/.temp/out/shared_temp
product wrote the credential artefact to:
  <repo>/.temp/out/shared_temp/vk_cookies_lxee6skq.cookies.txt
measured mode 0o666
  icacls| <dir>  BUILTIN\Administrators:(I)(OI)(CI)(F)
  icacls| <dir>  NT AUTHORITY\SYSTEM:(I)(OI)(CI)(F)
  icacls| <dir>  BUILTIN\Users:(I)(OI)(CI)(RX)
  icacls| <dir>  NT AUTHORITY\Authenticated Users:(I)(M)
  icacls| <file> BUILTIN\Users:(I)(RX)
  icacls| <file> NT AUTHORITY\Authenticated Users:(I)(M)
content:  .vkvideo.ru  TRUE  /  FALSE  0  synthetic_session  SYNTHETIC-...
```

**Consequence.** The stated reason for the placement
(`ytdlp_downloader.py:43-47`: "the system temp directory is private and not
synced") holds only by inheritance from whatever DACL the ambient `TEMP` names.
When it is not, the borrowed session lands in a file every authenticated local
user can read, with no compensating control anywhere in the tree, and nothing in
the product detects it. The wording of the justifying comment is phase 09's
subject; the behaviour is filed here once, behaviourally.

**Documented skip (recorded, not filed):** whether `0o600` yields an owner-only
file on a POSIX host. Not executable on the declared platform and not claimed.
What is claimed is the measurement above.

**Recommendation:** confine the artefact by something the platform can honour —
create a private per-run directory (`tempfile.mkdtemp`, plus an explicit `0o700`
on POSIX) and write the file inside it, rather than relying on a mode bit Windows
cannot express; probe the chosen directory's access state once per run and fall
back to a directory the process created itself when it is wider than the owner.
Small effort; the payoff is that the credential's confidentiality stops
depending on an ambient environment variable that nothing validates.

---

### SEC-002: A borrowed session survives forcible termination on a real in-flight transfer, and no control in the tree ever notices it
> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Re-derived end to end against the real `_download_with_ytdlp`. The cleanup is correct on every interceptable end, exactly as reported: driving the real call with a stub child that exits non-zero, the cookie file was **gone** when the call returned, and the `cookie_file_cleaned_up` record was written — the `finally` at `ytdlp_downloader.py:725-728` runs, the descriptor was closed at `:67-71` before the unlink, and the write-failure path unlinks at `:73`. The absent controls are also confirmed: **no file under `src/` mentions `atexit` at all**; there is no start-up enumeration of `vk_cookies_*` and no temp reaper; `signal_handlers.py:41-53` registers `SIGINT` and `SIGTERM` only, and its handler sets the shutdown `Event` — an orderly end, not a forcible one. The residue is real and larger than reported: **257** unreclaimed `vk_cookies_*.cookies.txt` in `%TEMP%`, mtimes spanning `2026-09-04` … `2026-09-29`, **every one measured `0o666`**.
>   **Why the type changes.** A `SPEC-DEVIATION` needs a project-declared rule the code breaks. The nearest candidate is the placement docstring at `ytdlp_downloader.py:43-47` — *"the system temp directory is private and not synced, reducing the risk of live session-cookie leakage on abnormal termination"* — and it **reduces** that risk, which is what it says: the temp directory is not the cloud-synced output directory. It never promises reclamation, and an un-interceptable termination is by definition one the product cannot observe. The gap that does exist — the product names its own artefacts with a distinctive, self-advertising prefix and never reclaims an orphan — is a hardening gap, not a broken promise.
>   **Severity re-derived from this run's own evidence: HIGH → MEDIUM** (reclassified; the decision is not the severity). Reachability is opt-in; every interceptable end is already handled correctly; the platform confines the surviving file; and the enumerated residue was, as the report itself concedes, produced by the test suite's leak rather than by a product run — so it is a phase-10 subject, not evidence that a product run strands credentials.
>   **Reachability, current tree:** the retained value reads *"OPT-IN — `--cookie-source browser`"*; the `CFG-001` reason behind it is fixed in this tree, so a `.env` line or environment variable also triggers the path. Same class, no decision change — see the header.
> - **See also:** `SEC-001` — same artefact, no shared root cause (access control while it exists vs. lifecycle after it should not); complement, not merge. `VAL-602` — **rollout constraint: the `mkdtemp` recommendation in `SEC-001` and the top-level sweep recommendation here are mutually incompatible as written, and the sweep as written is unsafe under concurrency.** Neither finding names the link. Phase 10 owns the test-suite residue.

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |
| **Reachability** | OPT-IN — `--cookie-source browser` (the artefact only exists when cookies are acquired) |

**Description:** Cleanup is correct on every end the process can intercept (R3,
recorded below) but there is nothing at all for the end it cannot. No exit hook,
no handler for forcible termination, no start-up enumeration of the artefact's
own name pattern, and no stale-temp reaper. A run killed mid-transfer leaves the
borrowed session on disk, readable, indefinitely — and the next run creates and
removes only its own artefact, never touching what the previous one left. This
is the *definitional* half of the headline question ("can another local process
read the live session while the download runs, and is it gone afterwards?"); its
empirical half requires a second local identity this platform does not provide
and is recorded below as **UNVERIFIED**. The unavailability of that half does not
suppress this finding.

**Evidence (R3 a/b/c, R4 a/b/c/d/e).** R3 — every interceptable end, driven
through the real `_download_with_ytdlp` with a stub child; existence recorded
immediately after the call returns, and the path handed to the child recorded
separately:

| End driven | Returned / surfaced | Child's own status | Artefact survivors |
|---|---|---|---|
| completed run (`returncode` 0) | output path | 0, cookie file opened by the child | **NONE** |
| non-zero return (`returncode` 3) | `None` | 3, cookie file opened by the child | **NONE** |
| exception raised before any child is started (`create_subprocess_exec` → `OSError`) | `OSError: spawn failed before any child existed` | none existed | **NONE** |
| cancellation through the real call | `CancelledError` | terminated, then reaped | **NONE** |
| write of the artefact itself fails | `OSError: write failed` | none existed | **NONE** (removed at `ytdlp_downloader.py:73`, after the descriptor is closed in the `finally` at `:67-71`) |

"'Removed' and 'the child could open it' are two facts", recorded separately:
after the completed run the path the child was given
(`C:\Users\...\Temp\vk_cookies_6lp5_yb6.cookies.txt`, argv element 28 of 29) no
longer existed, and during the run the stub child had opened it and read its
contents successfully. The removal ordering is the one the platform needs: the
descriptor is closed before the unlink, and the child is reaped before the
`finally` at `ytdlp_downloader.py:725-728` runs.

R4(a) — a real transfer, in flight, ended without a chance to run cleanup.
Mechanism: `taskkill /F /PID 18100` (`TerminateProcess`, the same class of end
as `SIGKILL` on POSIX or a power loss).

```
artefacts before: vk_cookies_*=247
LIVE CREDENTIAL ARTEFACT while the transfer is in flight:
  vk_cookies_ljd5i3ma.cookies.txt   requested 0o600 | MEASURED 0o666
  .vkvideo.ru  TRUE  /  FALSE  0  synthetic_session  SYNTHETIC-NOT-A-REAL-CREDENTIAL-0004
taskkill: SUCCESS: The process with PID 18100 has been terminated.
R4(b) vk_cookies_*.cookies.txt created by this run and surviving: 1
  vk_cookies_ljd5i3ma.cookies.txt  MEASURED mode 0o666  attrs 0x20  size 138
R4(c) read back: 1 cookie line, still readable now: True
```

R4(d) — per-family counts, exhaustive search of `src/`:

```
exit hook (atexit)                                             : 0
handler for forcible termination (SIGKILL / TerminateProcess) : 0 real
    (the 2 textual hits are docstring mentions of SIGKILL for CHILD processes:
     ffmpeg_utils.py:184, ytdlp_downloader.py:578)
start-up enumeration of the artefact's own name pattern       : 0 real
    (the 2 hits are the mkstemp creation calls: downloader.py:111, ytdlp_downloader.py:58)
temp sweep / stale-temp reaper                                : 0
signal handler registration                                   : 5, all in signal_handlers.py,
    and all of them set the shutdown Event (SIGINT/SIGTERM only) — an orderly
    end, not a forcible one
```

R4(e) — a second, ordinary run:

```
pre-existing vk_cookies_ artefacts: 247
  of those, modified/removed by the second run: NONE
  of those, deleted by the second run:         NONE
```

The 247 pre-existing artefacts already in the directory span 2026-09-04 to
2026-09-29, all measured `0o666`, all readable under the same three-principal
DACL. They demonstrate the reclamation half directly: nothing reclaims them.
(That particular residue was produced by the test suite's own leak, not by a
product run — which subject that is, is phase 10's; the count of controls that
would reclaim it is this phase's and is zero.)

**Consequence.** A downloaded session is recoverable from disk after the process
is gone, for as long as nobody deletes it by hand, on a path the product itself
takes. The file is named `*.cookies.txt` — a name that advertises what it is to
anything that enumerates the temp directory.

**Documented skip (recorded, not filed).** *Whether another local process can
actually read the artefact while a live transfer is in flight.* This requires a
second local identity on a POSIX host; the declared platform provides none, so
the observation is **UNVERIFIED** and no severity is stated for it. The offline
substitute — R1's absence of any confining control plus R4's enumerated residue
with its measured mode — answers the question as a structural claim about the
code, with the platform measurement as the observed half.

**Recommendation:** register an `atexit` hook that removes any credential
artefact the process created and has not yet removed, and sweep
`vk_cookies_*.cookies.txt` / `vk_ffmpeg_*.args` older than the longest plausible
run at start-up, before any new artefact is created. Both are small, local
changes; together they convert "survives indefinitely" into "survives at most one
run", which is the difference between a residue and a lingering credential.

---

### SEC-003: The owner-only guarantee for the credential artefact has no oracle that can fail on the declared platform
> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Every cited oracle exists and every skip is reproduced exactly. `tests/test_hls_downloader.py:533-538` guards `test_file_permissions_are_0600`, `:679-684` guards `test_temp_argfile_permissions_are_0600`, `tests/test_config.py:337-342` guards `test_log_file_created_with_owner_only_permissions` and `:353-358` guards `test_existing_log_file_permissions_updated` — all four with `@pytest.mark.skipif(os.name == "nt", reason=…)` and all four with the D-11 reason. Re-run this run: `TestCreateTempCookieFile` → `5 passed, 1 skipped`; `-k "permissions_are_0600"` → `2 skipped, 135 deselected`; `test_config.py -k "permissions"` → `2 skipped, 29 deselected`. The regression argument is sound and was confirmed against the mechanism: because `os.chmod(path, 0o600)` is a measured no-op here, deleting that line changes nothing this platform can observe, and the suite stays green.
>   **Why the type changes.** The tests are not defective: each guard states its reason accurately and each reason is true, as `VAL`-free measurement in this run confirms. What the finding calls "the guarantee the product documents" is a guarantee the product **declares it does not offer on this platform** — D-11, stated at three code sites and repeated in every skip reason. A correctly reasoned platform guard that documents a real, declared platform limitation is a defensible arrangement. What is genuinely missing is an oracle **anywhere** for the confinement property, which is a best-practice gap.
>   **One correction to the recommendation.** It asks for an assertion "executable on every platform" about a directory the process owns. On the declared platform there is no observable property of that kind to assert, so the recommendation degenerates to its own fallback — "that the requested mode is recorded and surfaced" — which asserts that a constant is a constant. The executable assertion that *is* available, and is the one the finding should ask for, is the DACL/owner check behind `SEC-001`'s recommended probe.
>   **Severity:** MEDIUM, by `99-audit-validate.md:369` (a reclassified finding). The observed consequence is confined to a POSIX host nobody develops on.
>   **Reachability, current tree:** the retained value reads *"OPT-IN — `--cookie-source browser`"*; the `CFG-001` reason behind it is fixed in this tree, so a `.env` line or environment variable also triggers the path. Same class, no decision change — see the header.
> - **See also:** `SEC-001` — the guarantee this finding names an oracle for; `SEC-003`'s recommended form is anchored to `SEC-001`'s recommended design, and `SEC-003` says so, so the chain is named rather than hidden. Phase 10 owns the guard style and the test-produced residue counted in `SEC-002`.

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_hls_downloader.py`, `tests/test_config.py` |
| **Classification** | mandatory |
| **Reachability** | OPT-IN — `--cookie-source browser` |

**Description:** Four assertions exist about the `0o600` mode. Every one of them
is skipped outright on the declared platform by a
`@pytest.mark.skipif(os.name == "nt", ...)` decorator, so none of their
assertion bodies ever executes here. A green run of the containing files is
therefore not evidence of anything: the guarantee the product documents
(`ytdlp_downloader.py:75-82`, `downloader.py:114-119`, `config.py:345-352`) has
zero executable oracle on the platform where the work happens. The *style* of
the guard is phase 10's subject; the missing guarantee is this phase's, because
the guarantee is the subject.

**Evidence (R2 a/b/c/d).** R2(a)/(b) — every oracle, its guard form, and whether
the body executed:

| Oracle | File:line | Guard form | Body executed on this platform? |
|---|---|---|---|
| `test_file_permissions_are_0600` (the **credential** artefact) | `tests/test_hls_downloader.py:533-550` | `skipif(os.name == "nt")` on the test | **NO** |
| `test_temp_argfile_permissions_are_0600` | `tests/test_hls_downloader.py:678-691` | `skipif(os.name == "nt")` on the test | **NO** |
| `test_log_file_created_with_owner_only_permissions` | `tests/test_config.py:337-351` | `skipif(os.name == "nt")` on the test | **NO** |
| `test_existing_log_file_permissions_updated` | `tests/test_config.py:353-370` | `skipif(os.name == "nt")` on the test | **NO** |

R2(c) — containing files, pass/skip counts, **labelled non-evidence** because a
guarded body reports success while executing nothing:

```
uv run pytest "tests/test_hls_downloader.py::TestCreateTempCookieFile" -q -rs
  SKIPPED [1] tests\test_hls_downloader.py:533: Owner-only confinement is not
    offered on Windows: os.chmod there toggles only the read-only attribute, so
    the measured mode is 0o666 rather than the requested 0o600 (D-11).
  5 passed, 1 skipped

uv run pytest tests/test_hls_downloader.py -q -rs -k "permissions_are_0600"
  2 skipped, 135 deselected

uv run pytest tests/test_config.py -q -rs -k "permissions"
  2 skipped, 29 deselected
```

R2(d) — the same check re-run out of band, with the platform guard out of the
equation, against the artefact R1 created:

```
[vk_cookies_*.cookies.txt] requested_mode=0o600  measured_mode=0o666
[vk_ffmpeg_*.args]         requested_mode=0o600  measured_mode=0o666
```

**Consequence.** If `os.chmod` were removed from `_create_temp_cookie_file`, or
changed to a mode that did not confine the artefact on POSIX, the suite would
still report 5 passed / 1 skipped in `TestCreateTempCookieFile` and the full
suite would still report 486 passed. The regression is silent on the declared
platform and would only surface on a host nobody develops on.

**Recommendation:** replace the platform-guarded mode assertions with ones that
assert something executable on every platform — that the artefact is created
inside a directory the process owns with a verified access state (SEC-001's
recommendation), or, failing that, that the requested mode is recorded and
surfaced. Keep the POSIX mode assertion as an additional, not exclusive, check.
Trivial effort; it converts a documented intention into a check that can fail.

---

### SEC-004: The credential file's path is disclosed in the yt-dlp command line while the sibling ffmpeg transport satisfies the product's own stated intent for the same value
> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced exactly, including the indices. The command vector built by the product's own `_build_ytdlp_cli_command` is 29 elements at build time and 30 once `_download_with_ytdlp` appends the URL (`:623`): `argv[27] == '--cookies'`, `argv[28] == 'C:\Users\NMATVE~1\AppData\Local\Temp\vk_cookies_8190jfj7.cookies.txt'`, `argv[29] == 'https://vkvideo.ru/video-1_2'` — the credential file is element 28 of 30, and the path exists on disk at that moment, measured `0o666`. The sibling transport is as described: `_temp_argfile` (`downloader.py:92-124`) writes the arguments to a file and the caller invokes `ffmpeg @<argfile>`, and `downloader.py:270-273` puts the credential path *inside* that file as `…?cookies=file:<path>`. The finding's calibration is right and is kept: the yt-dlp side has no stated rationale, so the defect is the **omission**, and a disclosed path is filed below a disclosure of what the path opens.
>   **Type upheld.** `SPEC-DEVIATION` on the same ground as `SEC-006`: the product states the invariant at `downloader.py:258-261` — *"since the URL is now inside the argfile, the cookie file path is also protected from the process listing"* — and at `downloader.py:97-99`. One of two transports carrying the same value meets the stated invariant; the other does not, with no stated exception. Reachability is correctly OPT-IN as a class; see the header for the current-tree correction to the *trigger*, which changes no decision here.
>   **Severity unchanged at MEDIUM.** On the declared platform the consequence is the argv element itself: Windows publishes no third-party-readable command line, so the observer-side effect is a projection, as the report's documented skip S-7 states. The persistent risk is the combination the report names — a disclosed path over a `0o666` file that outlives the process (`SEC-001`, `SEC-002`) — which those two findings already carry.
> - **See also:** `SEC-001`, `SEC-002` (the artefact the path opens); `SEC-006` (the declared sanitisation of "cookie file paths" in child output, which this argv makes matchable-in-principle and unmatchable-in-practice).

| Field | Value |
|-------|-------|
| **ID** | SEC-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |
| **Reachability** | OPT-IN — `--cookie-source browser` |

**Description:** The product states, in two places, that the credential file's
path is kept out of the process listing. The ffmpeg transport meets that
statement; the yt-dlp transport does not, and the product never says why. Both
sides were read before this was called a contradiction: the yt-dlp side has no
stated rationale at all, so the finding is the **omission**, not a
contradiction. Both facts about a named path belong here together: what a
process-table observer would read is a *path*; what a reader of that path can
open is the *credential*. The path disclosure is not filed at the severity of a
disclosure of what the path opens.

**Evidence (R5 a/b/c/d).** R5(a) — transport 1, the yt-dlp command vector built
by the product, verbatim; the occupied element marked:

```
[27] '--cookies'  <== next element is the credential file path
[28] 'C:\\Users\\NMATVE~1\\AppData\\Local\\Temp\\vk_cookies_9rk9gk28.cookies.txt'
[29] 'https://vkvideo.ru/video-1_2'
=> the credential file is on the child command line as element 28 of 30.
```

R5(b) — transport 2, the ffmpeg invocation file, verbatim. The signed address
**and** the credential path are inside the file; the argv is only
`['ffmpeg', '@<argfile>']`:

```
-y
-progress
pipe:2
-nostats
-headers
'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) .../Chrome/120.0.0.0 Safari/537.36
Referer: https://vkvideo.ru/
'
-i
'https://synthetic-cdn.invalid/hls/seg.m3u8?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&exp=1999999999&ip=203.0.113.7&cookies=file:C:\Users\...\Temp\vk_cookies_kfd9wit3.cookies.txt'
-c
copy
SYNTHETIC-OUTPUT.mp4
```

R5(d) — every declared intent in `src/`, each read against **every** transport
carrying the same value:

| Declared intent (verbatim) | ffmpeg transport | yt-dlp transport |
|---|---|---|
| `downloader.py:97-99` — "sensitive values (e.g. signed m3u8 URLs with CDN tokens) never appear in the process command-line arguments — they are only visible inside the temp file" | **MET** (argfile) | The signed m3u8 is not in this argv, but **the credential file path is** (element 28 of 30), and no reason is given for why this transport cannot use a file-based indirection |
| `downloader.py:258-261` — "The cookie file path is appended to the m3u8 URL as a query parameter; since the URL is now inside the argfile (SEC-001), the cookie file path is also protected from the process listing." | **MET** (argfile) | **NOT MET** — the same value sits in the argv as a bare element |
| `ytdlp_downloader.py:691-693` (SEC-002) — "sanitize subprocess output to redact any signed CDN URLs **or cookie file paths** that yt-dlp may echo in error messages" | log file: URLs redacted | log file: URLs redacted; a **bare path is not matchable at all** (filed as SEC-006); the stderr echo applies nothing (SEC-005) |
| `ytdlp_downloader.py:43-47` — "the system temp directory is private and not synced" | n/a | default `%TEMP%`: holds by inherited DACL; the product never checks it (SEC-001) |

R5(c) — every outbound request path and the form a session takes in it:

| Transport | Form a secret takes | Carrier marking |
|---|---|---|
| yt-dlp subprocess | argv element `--cookies` `<path>` | n/a — a file, not a header |
| ffmpeg subprocess | argfile line: `<signed m3u8>?cookies=file:<path>` | n/a — a file, not a header |
| aiohttp segment / playlist GET | `headers["Cookie"]` | **UNMARKED** plain `dict[str, str]` (SEC-008) |
| aiohttp after a forced token refresh | `headers["Cookie"]` reassigned in place | **UNMARKED** plain `dict[str, str]` (SEC-008) |
| yt-dlp library mode (`_extract_with_ytdlp`) | `ydl_opts` carries no cookie key at all | n/a — no session carried |
| Playwright `page.goto` | the context's own jar, never set by the product | n/a |

**Consequence.** On the route the product takes, a value that identifies the
credential is a plain element of a child process's argument vector for the whole
duration of the transfer. The consequence of that on a POSIX host, where
`/proc/<pid>/cmdline` is world-readable, is a **clearly-labelled projection, not
an observation** — see the documented skip below. What is portable and observed
is the element itself, and the combination with SEC-001/SEC-002: the disclosed
path opens a file that is world-readable whenever the temp directory's DACL is
wider than the owner, and that survives the process.

**Documented skip (recorded, not filed).** *Process-table exposure as an
observer would see it.* The declared platform publishes no readable command line
for a third-party observer, so the observation is **UNVERIFIED**. The portable
half — that the credential's path is an element of the vector — is the finding;
its consequence on a POSIX host is a projection.

**Recommendation:** where the third-party tool supports it, move the cookie file
out of argv the way the ffmpeg route already does. For yt-dlp the practical
options are to pass the cookies through the browser-context export the extractor
already performs, or to accept the disclosure explicitly and record it as a
known trade-off rather than leaving the sibling transport's guarantee to imply
the other one shares it. Medium effort at most; the benefit is that the
product's stated invariant stops depending on which transport happens to be
selected.

---

### SEC-005: The same child-output bytes reach the terminal untransformed and the log file redacted in one and the same run
> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced end to end, both surfaces captured separately in one run of the real `_download_with_ytdlp` against a stub child, with a real cookie file and a real log file. **CAPTURE A — `sys.stderr`, no transform at the surface:** `[download] Destination is unavailable` / `ERROR: unable to download video data: https://synthetic-cdn.invalid/seg/00042.ts?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&exp=1999999999`. **CAPTURE B — the same run's log file:** the same two lines with `https://synthetic-cdn.invalid/***REDACTED***`. `token in CAPTURE A = True`; `token in CAPTURE B = False`; the redacted form appears in the log and **never** in the terminal. The admission predicate is as stated at `ytdlp_downloader.py:221` (`_parse_ytdlp_progress(line) is not None`) and the untransformed write is at `:227`; the transform is at `:695`, applied only to the accumulated buffer on the failure branch. Type upheld as `SPEC-DEVIATION` on the same ground as `SEC-004`: the product declares a sanitisation rule for child output (`ytdlp_downloader.py:691-693`) and one of the two sinks carrying those bytes does not apply it, with no stated exception. Severity unchanged at HIGH: the echo is unconditional, the path is the default configuration, and the value class is one the product itself treats as sensitive two lines away.
>   **One correction to the evidence, which widens the class rather than narrowing it.** The R6(a) surface denominator claims to enumerate the surfaces before anything is driven to them, and it is incomplete: **`ffmpeg_utils.py:309-311` (`batch_merge_failed`) and `ffmpeg_utils.py:363` (`final_merge_failed`) write raw `stderr.decode()` into the log file with no transform at all** — the same class as the sites this finding names, on the *log* surface rather than the terminal, and reachable whenever a segment merge runs. The finding's claim is unaffected and its consequence is unaffected; the class is larger than the table shows. This is recorded here rather than filed as a new finding, because per `99-audit-validate.md:340` (`## 10`) a product-code finding belongs to the phase that owns its subject and this phase never re-files one.
> - **See also:** `SEC-006` and `SEC-007` are the same defect class seen from three sides — a terminal sink, a shape the transform cannot match, and third-party exception text. **They are complements, not a merge** (`99-audit-validate.md:200`): different sinks, different controls, different reachability (`SEC-005` DEFAULT, `SEC-006` and `SEC-007` differing again), and three independent fix locations. Both retained, cross-referenced, no content merged. `SEC-004` — the value the sanitisation claim is supposed to cover. Phase 08 owns what the rich live display renders; it is not in the corpus, so nothing is filed about it.

| Field | Value |
|-------|-------|
| **ID** | SEC-005 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |
| **Reachability** | DEFAULT — reachable at `cookie_source=none`; the echo is unconditional |

**Description:** A line the yt-dlp child prints is written to `sys.stderr`
verbatim by `_echo_ytdlp_line`, and the *same bytes* are transformed by
`sanitize_text_for_log` before they are written to the log. Inside a single run
the identical input is treated two ways. The escalation mechanism, not the
inference, is the subject: the admission predicate is
`_parse_ytdlp_progress(line) is not None` (`ytdlp_downloader.py:221`), and every
line that fails to match the progress regex is passed straight to
`sys.stderr.write(line)` at `:227` with nothing applied to it. This is a leak
finding, not merely an inconsistency: the capture below shows the token-shaped
value surviving verbatim on one surface while the same record on the other
surface has it removed.

**Evidence (R6 a/c/d).** R6(a) — the surface denominator, enumerated before
anything was driven to it:

| Surface | Written at | Transform |
|---|---|---|
| log file (JSONRenderer → FileHandler) | `config.py:363-377` | none at the surface |
| console renderer (ConsoleRenderer → StreamHandler stderr) | `config.py:362`, `:376-377` | none at the surface |
| **yt-dlp child output echoed to `sys.stderr`** | `ytdlp_downloader.py:198-228` | **none at the surface** |
| yt-dlp child output accumulated, then logged on failure | `ytdlp_downloader.py:684-701` | `sanitize_text_for_log` applied |
| ffmpeg child stderr accumulated, then logged on failure | `downloader.py:373-396` | `sanitize_text_for_log` applied |
| rich live display | `progress_display.py` | rendering is phase 08's; whether a secret appears in it is this phase's |
| CLI messages (`typer.echo`) | `cli.py:140-296` | `sanitize_url_for_log` on the `url` argument only |
| batch summary writer | `batch_downloader.py:405-474` | `typer.echo` of raw `url` strings from the input file |
| exception text sites | see SEC-007 | nothing applied at 11 sites |
| in-memory buffers that become text | `output_chunks`, `stderr_chunks` | become text only at the two log sites above |

R6(c) — one real run of `_download_with_ytdlp` against a stub child that printed
a signed-address-shaped line, with the two surfaces captured separately and
diffed:

```
CAPTURE A - sys.stderr echo (no transform at the surface):
    [download] Destination is unavailable
    ERROR: unable to download video data: https://synthetic-cdn.invalid/seg/00042.ts?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&exp=1999999999

CAPTURE B - the same bytes after sanitize_text_for_log:
    [download] Destination is unavailable
    ERROR: unable to download video data: https://synthetic-cdn.invalid/***REDACTED***

identical?                 : False
token in CAPTURE A (stderr): True
token in CAPTURE B (log)   : False
```

R6(d) — per surface, whether it applies a transform, and whether whatever
produced its input did: the echo surface applies none, and the echo function's
producer (`iter_process_lines`, `ffmpeg_utils.py:29-63`) applies none either.
The log surface applies `sanitize_text_for_log` to the accumulated buffer.
(Which streams the child's capture path reads, whether it invokes a transform on
each, and whether it uses the return value are phase 05's mechanical facts and
are cited, not re-derived; nothing is filed here about a missing call.)

**Consequence.** On the failure path the product takes, whatever the child
chooses to print — including a media address carrying a signed token — is
written to the operator's terminal unchanged, in the same run in which the same
bytes are redacted for the log file. Terminal output is the surface least likely
to be protected and most likely to be captured: scrollback, terminal recording, a
shared screen, a redirected session log.

**Documented skip (recorded, not filed).** *Whether a real yt-dlp or a real
ffmpeg actually prints a signed address.* The internal behaviour of a
third-party tool is out of scope by design; no token is named in this finding
and no severity is assigned that depends on it. What is filed is the
**unredacted emission route**, verified by the captured bytes above.

**Recommendation:** apply `sanitize_text_for_log` inside `_echo_ytdlp_line`
before anything reaches `sys.stderr`, exactly as the log site already does. That
is a one-line change at `ytdlp_downloader.py:222-227` and it makes the two
surfaces agree by construction rather than by two separate call sites
remembering to. Consider the same at `_drain_stderr` and the ffmpeg progress
writer for symmetry, so the rule "nothing a child prints reaches a terminal
untransformed" holds in one place.

---

### SEC-006: The child-output transform cannot match a filesystem path, so the credential file's path would pass through it untouched if a child ever named it
> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived against the product's own transform, one shape at a time, with the result recorded per shape. `sanitize_text_for_log` (`url_sanitizer.py:33-47`, a single `_URL_REGEX = re.compile(r"https?://[^\s'\"<>]+")` substitution): a signed media address → changed, secret removed, `https://synthetic-cdn.invalid/***REDACTED***`; a refreshed signed address → changed, secret removed; **a Windows filesystem path (`C:\Users\Someone\AppData\Local\Temp\vk_cookies_abcd1234.cookies.txt`) → returned byte-identical, artefact name intact**; a bare session pair (`Cookie: synthetic_session=…`) → byte-identical, value intact; a whole header line → byte-identical, value intact. The fallback the finding says already exists does exist and is verified here: `sanitize_url_for_log` reduces the same path to `***REDACTED***`, and it is applied only to the product's own `url=` fields. Type upheld as `SPEC-DEVIATION` and this is the cleanest instance of it in the report: the code says it redacts "any signed CDN URLs **or cookie file paths**" (`ytdlp_downloader.py:691-693`, `downloader.py:385-387`) and the function it calls cannot match a path — a stated behaviour the implementation does not have. Reachability correctly split: OPT-IN for the credential-file path, unconditional for the transform gap itself.
>   **Reachability, current tree:** the retained value reads *"OPT-IN — `--cookie-source browser`"*; the `CFG-001` reason behind it is fixed in this tree, so a `.env` line or environment variable also triggers the path. Same class, no decision change — see the header.
>   **Severity unchanged at MEDIUM.** The route is filed, not the observation: whether a real child names the cookie file is a third-party-behaviour question this platform cannot answer, and the report's documented skip S-4 says so without letting it suppress the route.
> - **See also:** `SEC-007` — the other two thirds of the same class. `SEC-004` — the argv value whose shape this transform cannot match. `SEC-005` — the sink that applies the transform and the sink that does not.

| Field | Value |
|-------|-------|
| **ID** | SEC-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/utils/url_sanitizer.py` |
| **Classification** | mandatory |
| **Reachability** | OPT-IN for the credential-file path; the transform gap itself is unconditional |

**Description:** The product states that subprocess output is sanitized to redact
"any signed CDN URLs **or cookie file paths**" (`ytdlp_downloader.py:691-693`;
the same claim at `downloader.py:385-387`). The only transform applied to that
text is `sanitize_text_for_log`, which matches `https?://...` and nothing else.
A bare filesystem path — which is exactly the shape of the credential file's
name, and exactly the shape of the value the product itself places in the yt-dlp
argv (SEC-004) — is **not matchable** by it. This finding is filed against the
credential that takes the shape, in this phase; the transform's own coverage is
not restated as this phase's finding.

**Evidence (R6 b/e/f).** The fixed corpus, each shape passed through every
transform reachable at the surfaces, output recorded per shape:

| Corpus shape | `sanitize_text_for_log` output | Changed the value? |
|---|---|---|
| signed media address (with token) | `https://synthetic-cdn.invalid/***REDACTED***` | **YES** |
| refreshed signed address (new token, same shape) | `https://synthetic-cdn.invalid/***REDACTED***` | **YES** |
| **filesystem path, this platform's shape** (`C:\Users\...\Temp\vk_cookies_8chars.cookies.txt`) | **returned byte-identical** | **NO** |
| bare session pair (`name=value`) | returned byte-identical | **NO** |
| whole header value (`Cookie: name=value`) | returned byte-identical | **NO** |

The transform that *would* match a path does exist and is already in the
package: `sanitize_url_for_log` reduces a non-URL argument to `***REDACTED***`
(verified in the same run). It is applied only to the product's own `url=`
fields and never to child output — so the capability is present and simply not
pointed at the surface that needs it.

R6(f) — the admission predicates on the surfaces, whole-match versus part-match.
The two admission predicates that decide what reaches a surface are
`_parse_ytdlp_progress(line) is not None` (which admits **any** non-progress
line, whole, unexamined) and the `download_failed` / `ffmpeg_download_failed`
log sites, which admit the entire decoded child buffer. A value carrying a token
in a part the predicate never inspects is therefore admitted whole — which is
correct behaviour for a log record and is the reason a transform, not a
predicate, has to be the control.

**Consequence.** The product's declared protection for the credential file's
path is not delivered by the code that claims to deliver it. A child that names
the cookie file it was given — in an error message, a warning, a verbose line —
produces output that reaches the log file with the path intact, while the
sibling line in the same buffer has its address redacted, so the redaction
looks like it worked.

**Documented skip (recorded, not filed).** *Whether a real child actually prints
the cookie file path.* This requires a live origin and a real third-party tool;
the observation is **UNVERIFIED** and no severity is assigned that depends on
it. What is filed is the route and the transform's inability to match the shape,
both measured.

**Recommendation:** widen the transform applied to child output to cover the
product's own artefact-name patterns — a regex over `vk_cookies_[^\s'"]+` and
`vk_ffmpeg_[^\s'"]+` alongside the URL rule — or route the whole decoded buffer
through a helper that falls back to `sanitize_url_for_log` for any
whitespace-delimited token the URL rule does not match. Small effort, and it
makes the SEC-002 claim in the code true instead of aspirational.

---

### SEC-007: Caught-exception text reaches the log untransformed at 11 sites, and one of them demonstrably carries a signed media address while its sibling field in the same record is redacted
> **Validation Note:**
> - **Action:** validated
> - **Detail:** Driven through the product's real handler with a real exception class. `yt_dlp.YoutubeDL.extract_info` was made to raise a genuine `yt_dlp.utils.DownloadError`; `VKVideoExtractor._extract_with_ytdlp` (`extractor.py:225-233`) caught it and logged `ytdlp_extraction_error` with `error='Unable to download webpage: HTTP Error 403: Forbidden (https://synthetic-cdn.invalid/hls/seg.m3u8?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&exp=1999999999)'` — verbatim, token present — beside `url='https://vkvideo.ru/***REDACTED***'`. The raised `ExtractionError` message carries the address too, because `extractor.py:231-233` interpolates the raw `e`. All eleven cited sites were re-opened and each is what the table says: `infrastructure/browser.py:45` (`exc_info=True`), `services/downloader_throttle.py:261-263`, `services/extractor.py:226-228`, `:291`, `:341`, `services/ffmpeg_utils.py:422`, `services/segment_downloader.py:302`, `:462`, `services/ytdlp_downloader.py:547-552`, `:553-558`, `:709-713`. The two candidates most likely to be false positives were checked and correctly excluded: `network_monitor.py:95` and `:120` log `str(e.__class__.__name__)` — the class **name**, never the message.
>   **Correction — the count is an under-count, and the omitted sites are the worst three.** The finding's own definition covers "a caught exception's own text — **or its `exc_info` traceback**". `logger.exception()` sets `exc_info=True` implicitly and therefore qualifies. Three such sites are not in the eleven: **`cli.py:221-222` (`download_failed`), `cli.py:333-338` (`batch_download_failed`) and `batch_downloader.py:285-291` (`unexpected_error_in_batch_download`)** — all three re-measured on the current tree, because the entry layer shifted while this run was in progress. These are the top-level handlers, the last place a failure surfaces, and they are materially worse than the eleven because the extractor raises with `from e` (`extractor.py:231-233`) — a `logger.exception` there renders the **chained cause**, so the yt-dlp `DownloadError` is printed in full beneath the `ExtractionError`. The class is **fourteen** sites, not eleven.
>   **Severity re-derived from this run's own evidence: MEDIUM → HIGH.** Three grounds, each from this run's own verification: the sink is the **log file**, which persists after the terminal scrolls away, while `SEC-005`'s is the terminal; reachability is **DEFAULT** (`ytdlp_extraction_error` sits on the ordinary extraction path at `cookie_source=none`); and the exposure was **observed in a real record** rather than routed. A finding that demonstrated the leak landing in a persistent log on the default path should not sit below one that only demonstrates a route to a terminal, and the enumeration correction above adds the two handlers most likely to print the address. `SEC-005` and `SEC-007` are now consistent with each other, which they were not before.
> - **See also:** `SEC-005`, `SEC-006` — the same class, three surfaces; complements, not a merge. `NET-004` (phase 03) — the refreshed-address behaviour that makes a signed address in a log record worth caring about; cited, not re-derived.

| Field | Value |
|-------|-------|
| **ID** | SEC-007 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |
| **Reachability** | DEFAULT — reachable at `cookie_source=none`; `ytdlp_extraction_error` sits on the ordinary extraction path |

**Description:** Eleven sites write a caught exception's own text — or its
`exc_info` traceback — into a sink with nothing applied to it. The **class** is
the finding; no specific token in a specific message is claimed. One of the
eleven is on the default extraction path, and driving a real
`yt_dlp.utils.DownloadError` carrying a synthetic signed address through the
product's real `except Exception as e` handler produces a log record in which the
product's own `url` field is redacted and the `error` field beside it is verbatim.

**Evidence (R8 a/b/c).** R8(a) — the per-site list and count:

| # | Site | What is written | Transform applied |
|---|---|---|---|
| 1 | `infrastructure/browser.py:45` | `exc_info=True` | none |
| 2 | `services/downloader_throttle.py:263` | `error=str(e)` | none |
| 3 | `services/extractor.py:228` | `error=str(e)` | **none** |
| 4 | `services/extractor.py:291` | `error=str(e)` (DEBUG) | none |
| 5 | `services/extractor.py:341` | `exc_info=True` (DEBUG) | none |
| 6 | `services/ffmpeg_utils.py:422` | `error=str(exc)` | none |
| 7 | `services/segment_downloader.py:302` | `error=str(e)` | none |
| 8 | `services/segment_downloader.py:462` | `error=str(e)` | none |
| 9 | `services/ytdlp_downloader.py:551` | `error=str(e)` | none |
| 10 | `services/ytdlp_downloader.py:557` | `error=str(e)` | none |
| 11 | `services/ytdlp_downloader.py:712` | `exc_info=True` | none |

R8(c) — driven through the product's real handler
(`VKVideoExtractor._extract_with_ytdlp`, `extractor.py:225-233`) with a real
`yt_dlp.utils.DownloadError` carrying a synthetic signed address:

```
str(real yt_dlp.utils.DownloadError), verbatim:
  'Unable to download webpage: HTTP Error 403: Forbidden (https://synthetic-cdn.invalid/hls/seg.m3u8?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&exp=1999999999)'

surfaced exception: ExtractionError
  str(), verbatim: 'Extraction failed for https://vkvideo.ru/***REDACTED***: Unable to
                    download webpage: HTTP Error 403: Forbidden (https://synthetic-cdn.invalid/
                    hls/seg.m3u8?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&exp=1999999999)'
  address carried in the exception text? True

LOGGED  ytdlp_extraction_error
  error field, verbatim: 'Unable to download webpage: HTTP Error 403: Forbidden (https://synthetic-cdn.invalid/hls/seg.m3u8?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&exp=1999999999)'
  address carried in the log record? True
  url field (the sibling, transformed): 'https://vkvideo.ru/***REDACTED***'
```

The same untransformed text is also interpolated into the raised
`ExtractionError`'s message at `extractor.py:231-233`, so it survives into
whichever layer reports the failure.

**Observed NOT carrying — recorded as a skip, not a finding.** The two aiohttp
request sites were driven against a local stub origin that aborts the body
mid-transfer, and neither message carried a request address:

```
segment path   : error = "Response payload is not completed: <ContentLengthError: 400,
                  message='Not enough data to satisfy content length header (received 176 of
                  4096 bytes).'>"   -> carries the request address? False
playlist path  : no error field logged; the 404 is reported as a status
ClientPayloadError  str() = 'Response payload is not completed'  -> False
ClientConnectorError str() = 'Cannot connect to 127.0.0.1'        -> False
ServerTimeoutError   str() = ''                                  -> False
```

`aiohttp.ClientResponseError` is the one aiohttp class whose message embeds the
full request URL, and the product's request sites check `response.status`
directly and never call `raise_for_status()`, so that class is never raised on
these paths. The two aiohttp sites are therefore a documented skip with a stated
reason; the class-level defect is filed from the site where the address was
actually observed to land.

**Documented skip (recorded, not filed).** *Whether a real yt-dlp run produces
an error message containing a real signed address.* The exception **class** and
the product's handler are real; the message content used above was constructed
for this run, because contacting a real origin is out of scope. That half is
**UNVERIFIED**, and the severity above is composed from the structural fact
(nothing is applied to exception text at 11 sites) plus the observed capability
of the class, not from a claimed live token.

**Consequence.** A message a third-party library composes is trusted verbatim
by the log layer, on the ordinary extraction path, at the default configuration.
The product redacts its own `url` field two keys away in the same record, so the
log looks protected while the address sits in the adjacent field.

**Recommendation:** route exception text through the same helper the URL fields
use — `sanitize_text_for_log` is already the right function and is one call away
at all eleven sites. A single wrapper that transforms `error=str(e)` centrally
keeps the rule in one place instead of eleven. Small effort; it removes a whole
class of "the library changed its message format" regressions.

---

### SEC-008: Both in-process objects that carry the session declare nothing sensitive and render it in full
> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from the declarations, then from the rendered forms. `HLSDownloadRequest` (`models/dtos.py:11-24`) declares `cookies: str | None` — the annotation resolves to `str | None`, a plain `str`, with no `SecretStr`, no `repr=False`, no `exclude=True` on any field. Rendered: `repr()` emits `cookies='synthetic_session=SYNTHETIC-SESSION-VALUE-0000-NOT-REAL'` and the full signed `m3u8_url`; `model_dump_json()` emits both in clear. `DownloadPolicy` (`services/segment_downloader.py:52-72`) declares `headers: dict[str, str]` on a `@dataclass` with no `field(repr=False)`; the generated `repr()` prints the whole dict including `'Cookie': 'synthetic_session=…'`. The present-call-site claim is also re-derived and holds: `HLSDownloadRequest` is constructed at exactly two sites (`downloader.py:555`, `ytdlp_downloader.py:534`) plus the definition, `DownloadPolicy` at one (`segment_downloader.py:825`), and a repository-wide search for `model_dump` and for a logger call taking the request or the policy found none. The finding is right that the subject is the **carrier**, not the call site, and right to say so.
>   **Type and severity unchanged.** `BEST-PRACTICE` / `advisory` / `MEDIUM` is the correct reading of a well-formed type that is unmarked: the field is exactly what it should be for its use, and the gap is that nothing in the type, the linter or the suite would object to a careless `logger.debug(policy)`. The recommendation is small, local, and aligned with a pattern the project already uses for the same property on a different carrier, so no new abstraction is introduced.
> - **See also:** `SEC-010` — the same session, carried twice, in two different forms, one of which has lost its domain. `NET-004` (phase 03) — where the `Cookie` header built from this flat string is sent.

| Field | Value |
|-------|-------|
| **ID** | SEC-008 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/dtos.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |
| **Reachability** | `HLSDownloadRequest.cookies` — OPT-IN; `DownloadPolicy.headers` — DEFAULT after a forced token refresh |

**Description:** Two objects carry a session between steps, and neither says so.
`HLSDownloadRequest.cookies` is a plain `str` on a Pydantic model, and
`DownloadPolicy.headers` is a plain `dict[str, str]` on a dataclass. Both render
the session value — and, in the DTO's case, the signed media address — in full
through `repr()`, `str()` and `model_dump_json()`. The fact that **no present
call site writes either object to a sink** is recorded separately below and is
not the reason for the finding: the finding is about the carriers themselves,
and the day one of them reaches a `logger.info(**request.model_dump())` or a
`%r` in a message, nothing in the type stops it.

**Evidence (R7 a/b/c/d).** R7(a)/(b) — every rendered form, verbatim, and the
marking status read **from the declaration**:

```
HLSDownloadRequest  (models/dtos.py:11-24)
  declared sensitive : NO - `cookies: str | None`, a plain str
  declared exclusions: none (no repr=False, no exclude=True, no SecretStr)
  repr()             : HLSDownloadRequest(video_url='https://vkvideo.ru/video-1_2',
                       m3u8_url='https://synthetic-cdn.invalid/hls/seg.m3u8?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&exp=1999999999&ip=203.0.113.7',
                       output_file=WindowsPath('SYNTHETIC-OUTPUT.mp4'), quality='720',
                       cookies='synthetic_session=SYNTHETIC-SESSION-VALUE-0000-NOT-REAL',
                       progress_callback=None)
  model_dump_json()  : {"video_url":"https://vkvideo.ru/video-1_2","m3u8_url":"https://
                       synthetic-cdn.invalid/hls/seg.m3u8?sig=SYNTHETIC-SIGNED-TOKEN-ABCD&...",
                       "output_file":"SYNTHETIC-OUTPUT.mp4","quality":"720",
                       "cookies":"synthetic_session=SYNTHETIC-SESSION-VALUE-0000-NOT-REAL",
                       "progress_callback":null}

DownloadPolicy  (services/segment_downloader.py:52-72)
  declared sensitive : NO - `headers: dict[str, str]`, a plain dict
  repr() (dataclass-generated) exposes the whole header dict:
    DownloadPolicy(session=None, semaphore=None,
      headers={'User-Agent': 'Mozilla/5.0 ...', 'Referer': 'https://vkvideo.ru/',
               'Cookie': 'synthetic_session=SYNTHETIC-SESSION-VALUE-0000-NOT-REAL'},
      max_concurrent_downloads=4, backoff_coordinator=None,
      video_url='https://vkvideo.ru/video-1_2', max_retries=3, download_timeout=300,
      is_bounded_batch=False, m3u8_url='', segments_dir=WindowsPath('.'),
      progress_callback=None)
```

R7(c) — per-object call-site counts, compared against the R6(a) surface list:

| Object | Construction / reference sites in `src/` | Sites that write, log, interpolate or format it into a sink |
|---|---|---|
| `HLSDownloadRequest` | 3 (definition `dtos.py:11`, constructed `downloader.py:555`, `ytdlp_downloader.py:534`) | **0** |
| `DownloadPolicy` | 23 references, all internal field access in `segment_downloader.py` | **0** |
| the `headers` dict itself | 4 pass-through sites (`downloader_throttle.py:214`, `segment_downloader.py:230`, `:457`, `:828`) | 0 |

R7(d) — the comparison against R6(a)'s surface list: ten surfaces exist, and
neither object reaches any of them today. That is a fact about the present call
sites, not a guarantee about the types.

**Consequence.** A carrier that renders its secret in `repr()`, `str()` and
`model_dump_json()` with no marker is one careless `logger.debug(policy)` away
from writing a live session to a log file, and nothing in the type system, the
linter or the test suite would object. The session is also carried twice in two
different forms — a flat `name=value; ...` string on the DTO, and a `Cookie`
header entry inside an ordinary header dict on the policy — so a reviewer
scanning a call site has no signal that either one is a credential.

**Recommendation:** declare the fields as what they are. `cookies: SecretStr` on
`HLSDownloadRequest` makes `repr()` and `model_dump_json()` render
`**********` by default while leaving the plain value one `get_secret_value()`
away at the two construction sites; a `SecretStr` header value, or a
`field(repr=False)` plus a custom `__repr__` for `DownloadPolicy.headers`, does
the same for the policy. Both are small, local, and make the sensitive field
self-describing — which is the property the finding is actually about.

---

### SEC-009: The serialiser writes a constant into the `include_subdomains` column, and a host-only domain makes the consumer reject the whole file
> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived against the installed consumer, not argued from the format. `yt_dlp` 2026.07.04; `YoutubeDLCookieJar.__mro__` is `[YoutubeDLCookieJar, MozillaCookieJar, FileCookieJar, CookieJar]`, so the file is parsed by `http.cookiejar.MozillaCookieJar._really_load`. The assert is at **`http/cookiejar.py:2051`** exactly as cited: `assert domain_specified == initial_dot`, preceded by `domain_specified = (domain_specified == "TRUE")` and `initial_dot = domain.startswith(".")`. Written with the product's own `_create_temp_cookie_file` and read back with the real parser, four domain shapes: `.vkvideo.ru` → `KEPT ['synthetic_session']`; `vkvideo.ru` → `REJECTED http.cookiejar.LoadError: invalid Netscape format cookies file '<path>': 'vkvideo.ru\tTRUE\t/\tFALSE\t0\tsynthetic_session\t…'`; `a.example.invalid` → same `LoadError`; `.a.example.invalid` → kept. **All-or-nothing confirmed:** a three-entry file whose only defect is one dotless middle entry lost **all three**, including the two well-formed ones. Through the product's actual consumer, `yt_dlp.cookies.load_cookies` wraps it as `yt_dlp.cookies.CookieLoadError: failed to load cookies` — naming neither the file nor the entry, exactly as reported. The proposed one-line fix was itself verified: `"TRUE" if domain.startswith(".") else "FALSE"` loads **both** shapes. The one-character claim is real and the blast radius on the host-only path is total.
>   **Type upheld** as `RUNTIME-ERROR` — the definition's "anything observed failing", and it was observed, not argued. Severity unchanged at HIGH: the product goes to the cost of acquiring a session and then cannot deliver it, on the path the operator explicitly opted into, with a diagnostic that names nothing and a `--no-warnings` flag (`ytdlp_downloader.py:273`) suppressing the consumer's own.
>   **Reachability, current tree:** the retained value reads *"OPT-IN — `--cookie-source browser`"*; the `CFG-001` reason behind it is fixed in this tree, so a `.env` line or environment variable also triggers the path. Same class, no decision change — and the one-word defect now costs a session the operator may have arranged months ago in a `.env` file, which is a slightly worse story than the retained text tells.
>   **One correction to the recommendation, which changes the diagnosis rather than the conclusion.** The finding says "the existing tests in `tests/test_cookies.py` assert on substrings and never load the result." That is false on both clauses, and the truth is better evidence than the claim. `tests/test_cookies.py` is 166 lines whose module docstring states: *"Every test below drives the product's real writer, `vkdownloader.services.ytdlp_downloader._create_temp_cookie_file`, and asserts on what the real consumer parsed out of the resulting file. Assertions are made against the jar, never against the file's text."* Four tests do exactly that, importing the real `yt_dlp.cookies.YoutubeDLCookieJar` and calling `jar.load()`. **The defect escaped because all four build their cookie through a single helper, `_cookie()`, that hard-codes one module constant, `_DOMAIN = ".vkvideo.ru"`** — the dotted shape, and only the dotted shape. The recommendation stands and becomes more precise: the missing case is a **dotless** domain in the existing round-trip class, which is a two-line addition to a class that already does the right kind of assertion. What does not stand is the implication that no consumer-verified test exists.
>   **Reachability, re-stated with the boundary made explicit.** The defect is confined to the `list[Cookie]` branch at `cookies.py:78`. The legacy `str` branch at `:87` writes `.vkvideo.ru\tTRUE` and is **correct**; the `domain` default at `:67` is also dotted. So the failure needs the browser path to hand the serialiser a host-only cookie — which is the shape Chromium reports for a cookie set without a `Domain` attribute, and the shape the product's own fixture uses at `tests/test_hls_downloader.py:1030-1035` (`domain="vkvideo.ru"`). That the product's own test fixture is the shape that breaks the product is the sharpest single line of evidence in the report, and it is why documented skip S-6 is the right disposition for the *live-harvest* half while the route itself needs no further assumption.
> - **See also:** `SEC-001`, `SEC-002` — the artefact this file is written into. `SEC-004` — the consumer that is handed the path. `SEC-005` — the surface on which the resulting `download_failed` is reported with no transform beyond URL redaction.

| Field | Value |
|-------|-------|
| **ID** | SEC-009 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/cookies.py` |
| **Classification** | mandatory |
| **Reachability** | OPT-IN — `--cookie-source browser` |

**Description:** `_cookies_to_netscape` writes the literal `TRUE` into the
second Netscape column for every entry, taken from no input attribute. That
column is the "include subdomains" flag, and the consumer cross-checks it
against the domain's own leading dot (`http/cookiejar.py:2051`:
`assert domain_specified == initial_dot`). A cookie whose domain has no leading
dot — the host-only shape a browser reports for a cookie set without a `Domain`
attribute, and the shape the product's own test fixture uses at
`tests/test_hls_downloader.py:1033` (`domain="vkvideo.ru"`) — therefore makes
the consumer refuse the **entire file**, not just the offending entry. The
written credential does not contain the credential.

**Evidence (R9 a/b/c/d, using the installed consumer: yt_dlp 2026.07.04,
`yt_dlp.cookies.YoutubeDLCookieJar`).** R9(a)/(b) — written with the product's
own `_create_temp_cookie_file`, read back with the real parser, per domain
shape:

```
input domain='.vkvideo.ru'
  written : .vkvideo.ru  TRUE  /  FALSE  0  synthetic_session  SYNTHETIC-...
  KEPT    : ['synthetic_session']      consumer said: <no diagnostics>

input domain='vkvideo.ru'
  written : vkvideo.ru   TRUE  /  FALSE  0  synthetic_session  SYNTHETIC-...
  KEPT    : NOTHING - the whole file was refused
  consumer said: http.cookiejar.LoadError: invalid Netscape format cookies file
    'C:\Users\...\Temp\vk_cookies_89axyi6v.cookies.txt':
    'vkvideo.ru\tTRUE\t/\tFALSE\t0\tsynthetic_session\tSYNTHETIC-...'

input domain='a.example.invalid'  ->  same LoadError, whole file refused
input domain='.a.example.invalid' ->  kept
```

R9(b), one dotless entry among dotted ones — the well-formed entries die with it:

```
written file:
  .vkvideo.ru  TRUE  /       FALSE  0             a  SYNTHETIC-...
  vkvideo.ru   TRUE  /hls    TRUE  0             b  SYNTHETIC-...
  .ads.example.invalid TRUE /  FALSE  0           c  SYNTHETIC-...
consumer KEPT : NOTHING
consumer said : http.cookiejar.LoadError: invalid Netscape format cookies file ...:
  'vkvideo.ru\tTRUE\t/hls\tTRUE\t0\tb\tSYNTHETIC-...'
```

What the consumer then does with it — read from the installed
`yt_dlp.cookies.load_cookies`, not inferred:

```
jar = YoutubeDLCookieJar(cookie_file)
jar.load()                        <- raises http.cookiejar.LoadError
except Exception: raise CookieLoadError('failed to load cookies')
```

The message names neither the file nor the offending line, and the product
passes `--no-warnings` (`ytdlp_downloader.py:273`), so no diagnostic is
emitted; the product's own handler reports it as a generic `download_failed`
(`ytdlp_downloader.py:690-702`).

R9(d) — every written field against the corresponding input attribute, with the
constant flagged:

```
input  : {name, value, domain, path, secure, expires, httpOnly, sameSite}
written: D.example.invalid  TRUE  P/sub  TRUE  12345  N  V
  domain             input='D.example.invalid'  output='D.example.invalid'  MATCHES INPUT
  include_subdomains input=<no such attribute>   output='TRUE'               WRITTEN FROM A CONSTANT
  path               input='P/sub'                output='P/sub'              MATCHES INPUT
  secure             input='True'                 output='TRUE'               DIFFERS (case only, by design)
  expires            input='12345'                output='12345'              MATCHES INPUT
  name / value       input='N' / 'V'              output='N' / 'V'            MATCHES INPUT
  attributes DROPPED entirely: ['httpOnly', 'sameSite']
```

R9(c) — the three-expiry comparison, so that only this one shape is at issue:
a session cookie (`expires` written as `0`) is **kept** and sent; a future expiry
is **kept** and sent; an already-past expiry is kept in the jar but **not sent**
to the origin. All three are written correctly; the expiry column is not the
defect.

R9(e) — control characters: a CRLF pair in `name`, `value`, `domain` or `path`
produces exactly one entry line with exactly seven fields in every case, so no
record is injected. A CRLF in `domain` produces a domain the consumer rejects
(LoadError), which is the same all-or-nothing behaviour as above, not an
injection.

R9(f) — input shapes and reachability: `list[Cookie]` and the legacy `str`
branch both serialise correctly. The `str` branch is **unreachable** from a real
caller — `extract_streams_with_cookies` returns `cookies_str` and `raw_cookies`
from one call, both `None` together on failure (`extractor.py:290-291`), and
`cookies_str` is empty only when `raw_cookies` is non-empty and takes priority
(`ytdlp_downloader.py:303`, `downloader.py:263`). Recorded as unreachable, not
filed.

R9(g) — other readers of a file of this kind: yt-dlp via `--cookies`
(`ytdlp_downloader.py:305`, `:308`) and ffmpeg via `cookies=file:`
(`downloader.py:273`). The ffmpeg half is **UNVERIFIED** — it needs a real
muxer's own run to see whether it accepts the same expiry — and is recorded as
a skip below.

R9(h) — the refresh path: neither route re-enters the serialiser.
`segment_downloader.py:440` discards `_raw_cookies` and reuses only the flat
string; `ytdlp_downloader.py:498` keeps `raw_cookies` but hands them to
`download_hls_with_resume`, which also takes only the string
(`segment_downloader.py:905` sets `headers["Cookie"]`). The refreshed set
therefore never re-enters the Netscape writer and inherits none of the rows
above. Recorded as a fact; it is also why the refresh path is not exposed to
this failure.

**Consequence.** A harvest that contains any host-only cookie produces a file
yt-dlp cannot open, so the borrowed session is lost for the whole transfer and
the download fails with a message that names neither the file, nor the reason,
nor the entry. The failure looks like a network or format problem, not a
serialisation problem, and the diagnostic the consumer does emit is suppressed
by `--no-warnings`.

**Documented skip (recorded, not filed).** *Whether a real harvest contains a
host-only cookie.* No claim is made about which cookies the origin sets, and
none was counted. The structural fact — a dotless domain rejects the whole file —
is measured directly against the installed consumer, and the product's own test
fixture already uses that shape, so the route itself needs no further assumption.

**Recommendation:** derive the column from the attribute the consumer checks —
`"TRUE" if domain.startswith(".") else "FALSE"` — one line at `cookies.py:78`.
That alone removes the rejection. Worth pairing with a unit test that writes a
dotted and a dotless domain and loads both with the real `YoutubeDLCookieJar`,
so the serialiser is verified against its consumer rather than against string
matching; the existing tests in `tests/test_cookies.py` assert on substrings and
never load the result. Trivial effort, and it turns a silent, misdiagnosed
failure into one that cannot occur.

---

### SEC-010: The harvest is unfiltered and the set is composed whole, while the stated reason names no dependency that requires it
> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from the two call sites the finding names. `extractor.py:288` is `raw_cookies = await page.context.cookies()` — no argument, the whole context store, and the only such call in `src/`. `extractor.py:309-320` `_format_cookies_for_ffmpeg` builds the flat header by joining `f"{name}={value}"` over the whole list with no filter of any kind; driven with a three-cookie set spanning `.synthetic-cdn.invalid`, `vkvideo.ru` and `.third-party.example.invalid` it produced `cdn_auth=SYNTHETIC-CDN; sess=SYNTHETIC-SESSION-VALUE-0000-NOT-REAL; third_party=SYNTHETIC-3P` — **all three, with the domain information gone**, while the Netscape writer given the identical set preserved all three domains. The stated reason is verbatim at `extractor.py:312-313`: *"Strips CRLF characters from cookie names and values to prevent header injection. Includes all cookies to ensure proper CDN authentication."* The per-family count is confirmed: no allowlist, no cookie-name filter, no domain filter at the harvest, no minimum-necessary wording.
>   **Type and severity unchanged.** `BEST-PRACTICE` / `advisory` / `LOW` is the right calibration, and the report earns it by supplying the bounding fact that keeps it there: the harvest runs in a context the product creates itself with no `storage_state` and no persistent profile (`browser.py:103-108`), so the store being read is the one this run's page populated, not the operator's saved browser profile. A judgement recorded as a judgement, with the dependency it rests on named as missing, is the correct finding — and the report is explicit that "if the CDN genuinely needs every element, say so at `extractor.py:313` and leave the code alone" is a legitimate answer, which is what makes it actionable rather than a preference.
>   **The one substantive row is confirmed as written.** `segment_downloader.py:683-687` resolves each segment with `urljoin(policy.m3u8_url, task.segment_url)` when the segment URL is relative, so a segment that resolves against the refreshed base is joined onto whatever `policy.m3u8_url` holds, and `segment_downloader.py:900-905` attaches `headers["Cookie"] = request.cookies` — a string with no domain scoping — to whatever host that resolves to. The consequence attributed to phase 03 (NET-004) is correctly attributed and correctly not re-derived here.
> - **See also:** `SEC-008` — the same session carried twice, unmarked. `SEC-001`/`SEC-002`/`SEC-004` — the wider on-disk artefact, the residue and the argv value that the standing breadth of the harvest feeds.

| Field | Value |
|-------|-------|
| **ID** | SEC-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |
| **Reachability** | OPT-IN for the harvest itself; the forced-refresh harvest is DEFAULT-reachable |

**Description:** The harvest takes the whole store and nothing narrows it between
capture and use. A **reason is stated** — "Includes all cookies to ensure proper
CDN authentication" (`extractor.py:313`) — so this is a judgement to be recorded
rather than an assumed defect; what is missing is the *dependency*: no statement
says which consumer needs a cookie for a domain other than the CDN's, and no
code asks. Both the per-consumer arrival and the named dependency were checked
before calling it a finding.

**Evidence (R10 a/c/d/e).** R10(a) — the harvest, verbatim, with no filter at
the call:

```
extractor.py:287   try:
extractor.py:288       raw_cookies = await page.context.cookies()
extractor.py:289       cookies_str = self._format_cookies_for_ffmpeg(raw_cookies)
extractor.py:290   except Exception as e:
extractor.py:291       logger.debug("failed_to_capture_cookies", error=str(e))
```

`page.context.cookies()` is called with **no argument**, so the whole context's
store is taken. It is the only such call in `src/`.

R10(e) — narrowing symbols, counted per family over the whole package:

```
allowlist / whitelist                    : 0
cookie-name filter                       : 0  (the one textual hit, config.py:244, is
                                               an env-var prefix builder, unrelated)
domain filter at the harvest             : 0
minimum-necessary wording                : 0
```

R10(c) — per consumer, whether the whole set arrives:

| Consumer | Form | Whole set? | What actually depends on the whole set |
|---|---|---|---|
| yt-dlp | Netscape file, `--cookies` (`ytdlp_downloader.py:305`) | **yes**, every element written | **YES** — the file format is per-cookie, so a subset is expressible and would still work |
| ffmpeg | `<m3u8>?cookies=file:<path>` (`downloader.py:273`) | **yes**, via the same file | **YES** — same |
| aiohttp `Cookie` header | `"; ".join` of every `name=value` (`extractor.py:315-320`) | **yes**, one flat string, all domains | **NO** — an HTTP `Cookie` header has no domain scoping, so cookies set for a third-party domain are sent to whatever host the segment request resolves to |

That last row is the substantive part: the flat composition at
`extractor.py:315-320` drops the `domain` attribute that the Netscape writer
preserves, and `segment_downloader.py:684` resolves each segment against
`policy.m3u8_url` before the header is attached. (The separate question of
whether a refreshed address and a refreshed cookie end up aimed at different
hosts is NET-004, phase 03's; cited, not re-derived.)

R10(d) — the stated reason, verbatim, and the two other places that assert a
purpose:

```
extractor.py:312-313  "Strips CRLF characters from cookie names and values to prevent
                       header injection. Includes all cookies to ensure proper CDN
                       authentication."
cookies.py:42-43      "Accepts either a pre-formatted cookies string or a list of Cookie
                       objects. When given Cookie objects, preserves the actual domain
                       attribute."
ytdlp_downloader.py:250/343/590  "preserves domain" (the reason raw_cookies is carried)
```

The reason names a consumer ("CDN authentication") but not a dependency: nothing
identifies *which* cookies the CDN needs beyond the ones scoped to it, and
nothing states why the third-party-domain entries must travel.

**Bounding fact, so the finding is calibrated rather than inflated.** The
harvest runs in a context the product creates itself, with no `storage_state`
and no persistent profile (`browser.py:103-108`: `new_context(viewport=…,
user_agent=…, locale=…, timezone_id=…)`). The store being read is the one this
run's page populated — not the operator's saved browser profile. This bounds the
blast radius considerably and is why the finding is LOW and advisory rather than
anything higher.

**Consequence.** Every element the context holds travels to every consumer, and
to the one consumer that cannot scope them it travels in a form that has lost
its domain. The exposure is bounded by the ephemeral context, but the product
pays a standing cost — a wider on-disk artefact (SEC-001/SEC-002), a wider argv
value (SEC-004), a wider `Cookie` header (SEC-008) — for a dependency it never
states.

**Recommendation:** decide the dependency and write it down, then narrow to it.
If the CDN genuinely needs every element, say so at `extractor.py:313` and
leave the code alone — that is a legitimate answer. If it does not, filter the
harvest at `extractor.py:288` to the domains actually requested, and build the
`Cookie` header from that same filtered set so the flat composition cannot
outrun the file. Small effort either way; the gain is a credential whose scope
is decided by the product rather than by whatever the page happened to set.

---

## Documented skips

Recorded as skips, not as clean results. Each is UNVERIFIED because the
platform, the tools or the origin make the observation unavailable in this
environment — **not** because the route was found to be safe. Where a route
exists, the route is filed separately and this entry records only the part that
could not be observed.

| # | What could not be observed | Why | How the definition is answered anyway |
|---|---|---|---|
| S-1 | Real permission enforcement on a POSIX host | The declared platform is Windows; `0o600` has no enforcement there | Structural facts verified by R1/R2: requested `0o600`, measured `0o666`, `os.chmod` a no-op, 0 ACL/DACL/security-descriptor/ownership/creation-mask calls, 0 executable oracles. Not converted into "no finding" — it is filed as SEC-001 and SEC-003 |
| S-2 | Whether another local process can read the artefact **during** a live transfer | Requires a second local identity on a POSIX host | Offline substitute: R1's absence of any confining control plus R4's enumerated residue with its measured mode. Filed as SEC-002 |
| S-3 | Whether ffmpeg's own cookie reader accepts the serialiser's expiry | Needs a real muxer's run | The yt-dlp half of the same file **was** exercised against the installed parser (`YoutubeDLCookieJar`); the yt-dlp result is SEC-009 |
| S-4 | Whether a real yt-dlp or ffmpeg prints a signed address or the credential path | Third-party tool behaviour, and a live origin | The unredacted emission route is filed as SEC-005; the unmatchable shape is filed as SEC-006 |
| S-5 | Whether an exception message from a real origin embeds a request address | Needs a live origin | The two aiohttp sites were driven against a local stub origin and observed **not** to carry one; the yt-dlp site was proven capable with the real exception class. The class is filed as SEC-007 |
| S-6 | Browser-side acquisition, and the contents of a real cookie store | No live origin | Explicitly out of scope. The unfiltered-harvest structural fact is filed as SEC-010; no cookie the origin sets is named or counted anywhere in this report |
| S-7 | Process-table exposure as an observer would see it | The declared platform publishes no readable third-party command line | The portable half — the path is an element of the vector — is filed as SEC-004; the POSIX consequence is labelled a projection, not an observation |
| S-8 | The `str` input branch of the serialiser | **Unreachable from any real caller** (R9(f)) | Routed to edge cases and recorded, not filed as a live defect |

---

## Cross-references to findings owned by other phases

Cited, not re-filed.

- **ENT-001** (phase 01, HIGH, confirmed) — records emitted before
  `structlog.configure` reach structlog's default stdout sink. Checked here
  rather than assumed: the pre-sink emissions in `src/` are
  `config.py:145` (`download_dir_empty_string_using_default`) and the
  `unknown_env_var_ignored` record emitted from `cli.py:125` before
  `setup_logging` at `cli.py:128`. Neither carries a session value, a signed
  address, or a credential path — `unknown_env_var_ignored` logs the variable
  **name** and the valid-name set, never a value. So no credential-bearing
  record is a pre-sink emission on this phase's subjects, and nothing is filed.
  Had one been found, it would have been cross-referenced to ENT-001 rather
  than re-filed.
- **CFG-001** (phase 02, validated HIGH) — `VKDOWNLOADER_COOKIE_SOURCE` can
  never reach `Settings.cookie_source`. Cited once, in the reachability gate,
  and used to set the gate. No credential exposure rooted in it is filed here.
- **CFG-008** (phase 02, LOW) — the resolved `.env` path is logged at DEBUG only.
  Not a credential route; noted and not filed.
- **NET-002** (phase 03) — no retry policy on 429/5xx in the manifest layer. Not
  a credential subject; not examined.
- **NET-004** (phase 03) — a 403 refresh rewrites the manifest address while
  media parts still resolve against the original base on the old host carrying
  the fresh cookie. This is a credential-forwarding finding and phase 03 owns
  it. It is cited in SEC-010's evidence where the two subjects touch, and is
  **not** re-derived here.
- **Phase 05** — the child's invocation convention, including which streams the
  capture path reads and whether it uses a transform's return value. Those
  mechanical facts are cited inside SEC-005 and not re-derived; nothing is
  filed here about a missing call.
- **Phase 08** — what the rich live display renders. The surface is listed in
  SEC-005's denominator; whether a secret appears in the rendering is phase
  08's to answer from that list.
- **Phase 09** — the wording of comments and docstrings. The claims quoted here
  (`ytdlp_downloader.py:43-47`, `:75-82`, `:691-693`; `downloader.py:97-99`,
  `:258-261`, `:385-387`) were read as evidence for the behaviours filed, and
  each behaviour is filed here once, behaviourally, not as a wording defect.
- **Phase 10** — the test suite. SEC-003's oracle gap is filed here because the
  guarantee is the subject; the guard *style* and the 247 test-produced
  artefacts noted in SEC-002 are phase 10's.
- **Phase 11** — ignore coverage. The credential artefact
  (`vk_cookies_*.cookies.txt`) is recorded here among the candidate paths for
  phase 11, per the template's instruction that this phase records the artefact
  and files nothing about the answer.

---

## Verification commands run in this phase

All under `.temp/` (gitignored), all harnesses removed afterwards. No
production code was modified; `git status` reports only the added findings file
and the pre-existing untracked entries.

| Command | Result |
|---|---|
| `uv run pytest tests` | 486 passed, 4 skipped — exit 0 |
| `uv run ruff check src tests` | exit 0 |
| `uv run ruff format --check src tests` | 52 files already formatted — exit 0 |
| `uv run mypy src` | no issues in 30 files — exit 0 |
| `uv run pytest "tests/test_hls_downloader.py::TestCreateTempCookieFile" -q -rs` | 5 passed, 1 skipped — **labelled non-evidence** (the skip is the mode oracle) |
| `uv run pytest tests/test_hls_downloader.py -q -rs -k "permissions_are_0600"` | 2 skipped, 135 deselected |
| `uv run pytest tests/test_config.py -q -rs -k "permissions"` | 2 skipped, 29 deselected |

Out-of-band harnesses (scratch, under `.temp/`, since deleted):
requested-vs-measured mode and DACL measurement; a real in-flight transfer ended
with `taskkill /F`; a real `_download_with_ytdlp` driven against a stub child on
four ends; a local aiohttp stub origin; a real `yt_dlp.utils.DownloadError`
through the product's extractor handler; the Netscape serialiser loaded by the
installed `YoutubeDLCookieJar`; a reachability probe of `_build_ytdlp_cli_command`,
`_resolve_cookies` and `download_hls_with_resume`.

---

## Rollout-safety findings and pipeline-document defects

Defects in the audit inputs themselves — constraints over the fixes this report accepts,
and defects of the pipeline's own documents. Per `99-audit-validate.md:340` and `## 10`,
this phase files no product-code finding; each of the three below is a conflict of shape,
an ordering constraint, or a defect of a document this phase owns.

### VAL-601: The severity table the validation stage must compose from has no row for a finding that passes verification, so the instruction to re-derive one is unexecutable

| Field | Value |
|-------|-------|
| **ID** | VAL-601 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/phases/99-audit-validate.md` |
| **Classification** | mandatory |

**Description:** The validation stage is told to re-derive every severity from its own
verification, and is given a four-row table to re-derive it from. The table has no row for
the outcome that verification most often produces.

`99-audit-validate.md:365-370`, the whole table:

| Severity | Condition in this phase |
|---|---|
| CRITICAL | a cross-phase conflict, or a rollout-safety blocker |
| HIGH | a finding whose technical correctness or current applicability **failed** verification; or a rejected finding whose rejection changes a conclusion |
| MEDIUM | a **reclassified** finding (its `Type` changed) or a **merged** finding |
| LOW | a `DOC-UPDATE` candidate; any advisory finding with no security, data-loss or correctness consequence |

And `99-audit-validate.md:382`, the instruction that table is supposed to serve:

> **Validated** | Keep as-is. **The severity is re-derived from this phase's own verification,
> and is not changed by this decision.**

A finding that is **validated** matches none of the four conditions. HIGH is reserved for
verification that *failed*; MEDIUM is reserved for a *reclassified* or *merged* finding;
LOW is reserved for a documentation candidate or an advisory finding with no consequence;
CRITICAL is reserved for a cross-phase conflict or a rollout blocker. There is no row, and
`## 8` adds no fifth word (`:362`).

**Exact consequence.** The instruction at `:382` cannot be executed for the largest class of
decision the phase takes, and the four tables in this pipeline are not independent of it:
`99-audit-validate.md:373-377` and `:482` both rest on the claim that a decision never
changes a severity, which only holds if the severity has a defined source for every
decision. The `02` validation run met this and improvised — it re-derived `CFG-001` from
CRITICAL to HIGH and said so inline (`02-config-validated-findings.md:61`) although
`CFG-001` was **validated**, and under `:368` a validated finding is not a HIGH candidate.
That run's severity for that finding is therefore unsourced in the document that is supposed
to source it. This run faced the same gap on seven findings and had to choose a rule the
document does not state: that a confirmed finding keeps its severity unless this run's own
evidence moves it, which is recorded on each block. Two runs have now invented the same rule
independently, which is how a document that never said it acquires a practice nobody wrote
down.

**Evidence:** `:365-370` and `:382` were read against each other. The table's four conditions
were each tested against the decision vocabulary `## 11` defines (`validated | reclassified |
merged | rejected`); only three of the four decisions have a matching condition. The prior
artifacts were opened and the improvisation at `02-config-validated-findings.md:61` is the
same one this run had to make.

**Recommendation:** add a fifth **row** — not a fifth word — to the table, e.g. *HIGH or
MEDIUM | a validated finding, composed from the consequence observed on the declared
platform and not from the decision.* Then the instruction at `:382` has a source, and the
next run stops inventing one. One line; no behaviour changes.

---

### VAL-602: `SEC-001` and `SEC-002` prescribe incompatible fixes to the same function, and the sweep `SEC-002` recommends is unsafe under concurrency

| Field | Value |
|-------|-------|
| **ID** | VAL-602 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/ytdlp_downloader.py` (`_create_temp_cookie_file`, `:42-83`) |
| **Classification** | mandatory |

**Description:** Two accepted findings recommend changes to the same function that cannot
both be applied in the form written, and neither names the other.

- `SEC-001` — *"create a private per-run directory (`tempfile.mkdtemp`, plus an explicit
  `0o700` on POSIX) and write the file inside it"*. After this, the artefact lives at
  `<tempdir>/<mkdtemp-name>/vk_cookies_*.cookies.txt`.
- `SEC-002` — *"sweep `vk_cookies_*.cookies.txt` / `vk_ffmpeg_*.args` older than the longest
  plausible run at start-up, before any new artefact is created"*. This is a top-level glob
  over `<tempdir>`.

**Exact consequence, in the order that is dangerous.** If `SEC-001` lands first and `SEC-002`
is applied as written, the sweep matches **nothing** — the new artefacts are one directory
level down — and the reaper is a silent no-op on every future run. A cleanup control that
silently never fires is the worst failure mode available here, because the residue it was
added to remove keeps accumulating and nothing reports the miss. The reverse order is safe
but wasteful: the sweep still reaches old top-level residue while the new artefacts never
appear there at all. Neither finding states an order, and neither states that the other's
recommendation changes where the artefact lives.

**The concurrency hazard neither finding names.** The sweep as written has no per-run marker
and no lock, and the product has no single-instance lock — nothing in `src/` prevents a
second process from starting while a first is mid-transfer. A start-up sweep keyed only on
name and age will therefore delete a **live** credential file belonging to a concurrently
running instance: a batch in one terminal and a single download in another is enough. The
*"older than the longest plausible run"* bound mitigates this but does not eliminate it, and
neither finding defines the bound, so a fixer must invent a duration and cannot tell whether
it is safe.

**A residue class neither recommendation closes.** `SEC-001`'s `mkdtemp` creates a directory
per run. Nothing in either recommendation removes that directory, and it is removed only if
the whole process tree exits cleanly. `SEC-001` would trade one unbounded residue
(a growing list of `vk_cookies_*` files) for another (a growing list of empty per-run
directories) unless the private directory's lifetime is stated in the same change.

**Evidence:** both recommendations quoted verbatim from this artifact's `SEC-001` and
`SEC-002` blocks. `tempfile.mkdtemp` and `tempfile.mkstemp` call sites enumerated across
`src/` — the only three are `ytdlp_downloader.py:58` and `downloader.py:111` (both
`mkstemp`, the artefacts themselves) and none is a directory. No lock, no `fcntl`, no
`msvcrt.locking`, no PID file anywhere in `src/`. `signal_handlers.py:41-53` registers
`SIGINT`/`SIGTERM` per process and confers nothing between processes.

**Recommendation:** land both in one change, in this order: **(1)** give the artefact a
per-run private directory and record the owning PID in it; **(2)** make the reaper a sweep
of *those* directories, deleting one only when its recorded PID is no longer live — which
solves the concurrency hazard structurally rather than with a guessed duration; **(3)**
remove the directory in the same `finally` that unlinks the file, and sweep empty
directories in step 2. A fixer who lands the `mkdtemp` half first and the glob half second
gets a reaper that never fires and never says so.

---

### VAL-603: The report format supplies a pre-answered summary and three placeholder action lists, and every phase in this catalogue has deleted rather than filled them

| Field | Value |
|-------|-------|
| **ID** | VAL-603 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.ai/audit/templates/audit-findings.md` (`:37-56`) |
| **Classification** | advisory |

**Description:** The finding block of the format is sound — nine mandatory fields, four
legal type labels, four legal severities, two legal classifications, and this run
adjudicated ten findings against it without finding an illegal label. The **tail** of the
format is not. `.ai/audit/templates/audit-findings.md:37-56` supplies four sections:

```markdown
## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |

## Mandatory Fixes

{List all findings classified as mandatory}

## Advisory Recommendations

{List all findings classified as advisory}

## Doc Updates Needed

{List all findings classified as DOC-UPDATE type}
```

The `## Summary` table arrives **pre-answered with zeros** — a report that emits it verbatim
claims to have found nothing, which is the one thing `problems-only` forbids. The three
sections after it are unfilled placeholders. All five validation artifacts now in the tree
delete or replace the summary table and omit the other three entirely: `01`, `02`, `03` and
`04` end at a `## Validation Summary` that the format does not supply, and this artifact
does the same. Nothing in the format says a phase may do this, and nothing in it says what
should replace them.

**Exact consequence.** The format's only consolidated action list — *Mandatory Fixes*,
*Advisory Recommendations*, *Doc Updates Needed* — does not exist in any report the pipeline
has produced. A reader of this artifact must reconstruct it by reading ten decision records
and filtering a `Classification` column, and a reader of the four sibling artifacts must do
the same. The three-way split is the one that matters most for a run whose whole output is
a list of things to do, and it is the one the format drops.

**Evidence:** the template was read in full (79 lines); `:37-56` is the tail. All five
artifacts under `.ai/audit/99-validation/` were opened and none carries a `## Summary`
severity table, a `## Mandatory Fixes`, an `## Advisory Recommendations` or a
`## Doc Updates Needed` section. `99-audit-validate.md:314` names this check and states that
"a section every phase must delete is a defect of the format" — executed here, with the
consequence observed.

**Recommendation:** either delete `:41-44` (a zero-filled table is a report that has already
answered itself, and this pipeline's binding rule forbids exactly that) or make the section
a template the phase fills, and give the three action lists real headings so a phase has
somewhere to put them. As it stands the format asks for four sections and the pipeline
supplies none of them, and the phase that removed them was right to and wrong to have had to.

---

## Findings summary after validation

Ten source findings, ten decisions. Every one was re-derived from the artifact it names
and from the installed dependencies; the decision record for each is the `Validation Note`
on its block above, and the retained original text is that block's own content.

| Action | Count | IDs |
|---|---|---|
| Validated (unchanged) | 7 | SEC-004, SEC-005, SEC-006, SEC-007, SEC-008, SEC-009, SEC-010 |
| Reclassified | 3 | SEC-001, SEC-002, SEC-003 |
| Merged | 0 | — |
| Rejected | 0 | — |
| VAL- (rollout / pipeline-document) | 3 | VAL-601, VAL-602, VAL-603 |

Severity after this run's own re-derivation: **HIGH 3** (SEC-005, SEC-007, SEC-009),
**MEDIUM 6** (SEC-001, SEC-002, SEC-003, SEC-004, SEC-006, SEC-008), **LOW 1** (SEC-010).
Three source severities moved, all recorded inline on their blocks: SEC-001 HIGH → MEDIUM,
SEC-002 HIGH → MEDIUM, SEC-007 MEDIUM → HIGH. None moved because of its decision.

`SEC-009` is the only finding in this report whose subject is a failure rather than an
exposure, and it is the only one that was **observed** end to end against the real
consumer rather than routed: one character at `cookies.py:78` makes `yt_dlp` reject the
entire credential file on the host-only domain path, so the session the product went to the
trouble of acquiring is lost for the whole transfer, and the diagnostic that says so names
neither the file, the reason, nor the entry.

`SEC-001` … `SEC-004` are one chain on one artefact and are kept as four, because they are
four different controls on four different layers (access state, lifecycle, oracle, argv) —
not one defect stated four times. `SEC-005` … `SEC-007` are one class on three surfaces and
are likewise kept as three, cross-referenced and **not** merged, for the reason recorded in
`SEC-005`'s Validation Note.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 7 | SEC-004, SEC-005, SEC-006, SEC-007, SEC-008, SEC-009, SEC-010 |
| Reclassified | 3 | SEC-001, SEC-002, SEC-003 |
| Merged | 0 | — |
| Rejected | 0 | — |
| VAL- (cross-phase / rollout) | 3 | VAL-601, VAL-602, VAL-603 |

10 findings in scope. 7 validated, 3 reclassified, 0 merged, 0 rejected. Cross-phase
conflicts: 0 — every cross-phase claim this report makes (`ENT-001`, `CFG-001`, `NET-004`)
was opened in the owning phase's file and confirmed, and the one negative result that
mattered was confirmed rather than assumed. Baselines re-verified, not inherited: `pytest
tests` 486 passed / 4 skipped, `ruff check` clean, `ruff format --check` was clean on the tree this run started on and is **not** clean on the tree
it finished on (`downloader.py`, `batch_downloader.py` — an in-flight `CFG-002` fix landed
mid-run; see the header). `mypy src` clean in 30 files. Re-derived evidence, all on synthetic
values, in the gitignored `.temp/` tree: the installed `yt_dlp` 2026.07.04 cookie parser
against the product's own serialiser; Windows `os.chmod` semantics with a `0o444` positive
control; the DACL of the default temp directory and of a product-created artefact; the real
`_download_with_ytdlp` driven against a stub child with both sinks captured; a real
`yt_dlp.utils.DownloadError` through the product's real extraction handler; and a live
reachability probe of `VKDOWNLOADER_COOKIE_SOURCE` by process environment, by `.env` and
through the real Typer entry point, which is how the tree change was caught.

Nothing was rejected, so nothing is retained as a rejected claim. The three reclassifications
are corrections of **framing**, not of fact: every measurement the source report took
reproduced. The largest single correction is to `SEC-001`'s justification, which rested on
reading a code comment as asserting something it does not assert — the comment
(`ytdlp_downloader.py:78-81`) states the Windows limitation and draws the correct conclusion
from it, and the finding's own two headline measurements (requested `0o600`, measured
`0o666`, `chmod` a no-op) are exactly right. The subject survives as a hardening gap; the
spec deviation does not. This is the reason `VAL-601` exists: the handbook gave this stage no
rule for composing a severity for a finding that passed verification, so three severities
moved on a judgement the document does not contain.

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | None. No finding met a rejection ground (already implemented, stale, duplicate, low value at this scale, architecture-breaking, operationally unsafe, overly complex, against project direction). `SEC-001` came closest and was **reclassified, not rejected**: its measurements are correct, so discarding it would lose the evidence, and its residual — a credential whose confidentiality depends on an ambient environment variable the product never inspects — is real and worth acting on. What fails is the type, not the subject. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| — | — | None. Three merge candidates were examined and all three are genuine complements, not restatements (`99-audit-validate.md:200`): `SEC-001`/`SEC-002` are access-state and lifecycle on one artefact; `SEC-002`/`SEC-004` are the file's lifetime and its path's exposure; `SEC-005`/`SEC-006`/`SEC-007` are three sinks of one class. Each pair differs in the control it would install and in the file it would change, so collapsing any of them would lose content. All retained, cross-referenced in place. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SEC-001 | SPEC-DEVIATION | BEST-PRACTICE | The behaviour is a **declared, documented design decision**, not a violation of one: `ytdlp_downloader.py:78-81` and `config.py:347-352` both state that Windows confinement is not offered (D-11), and `os.chmod(path, 0o600)` is a measured no-op here — which is the stated reason, not a contradiction of it. The subject that survives is real and product-owned: the artefact's confidentiality has no product-side control and rests on a DACL inherited from an ambient `TEMP`/`TMP`/`TMPDIR` the product never reads. Defensible arrangement, demonstrated gap. Severity HIGH → MEDIUM on the same evidence. |
| SEC-002 | SPEC-DEVIATION | BEST-PRACTICE | No declared rule is broken. The placement docstring (`ytdlp_downloader.py:43-47`) promises the temp directory *reduces* leakage risk on abnormal termination, which is true, and it never promises reclamation; an un-interceptable termination is one no process can observe. The real gap is that the product names its own artefacts with a distinctive prefix and never reclaims an orphan — hardening, not a broken promise. Cleanup on every interceptable end was re-verified correct. Severity HIGH → MEDIUM. |
| SEC-003 | SPEC-DEVIATION | BEST-PRACTICE | Each of the four guards is accurate and each stated reason is true, as measurement confirms — the tests are not defective. The guarantee they would assert is a guarantee the product declares it does not offer on this platform, so what is genuinely missing is an oracle anywhere for it. Correctly reasoned platform guard plus a coverage gap. Severity MEDIUM, per `99-audit-validate.md:369`. |

### Severity movements recorded in place

| ID | Source | Re-derived | Basis for the movement |
|----|--------|-------------|------------------------|
| SEC-001 | HIGH | MEDIUM | Reclassification, per `:369`. Reachability opt-in; default-path access state confined by inheritance. |
| SEC-002 | HIGH | MEDIUM | Reclassification, per `:369`. Reachability opt-in; every interceptable end already handled; residue is test-produced. |
| SEC-007 | MEDIUM | HIGH | Observed landing in a persistent sink (the log file) on the DEFAULT extraction path, in a real record driven through the product's real handler — against `SEC-005`'s MEDIUM, which only demonstrates a route to a terminal. The enumeration correction (fourteen sites, not eleven) adds the two top-level handlers whose `logger.exception` renders the chained `DownloadError` cause. |
