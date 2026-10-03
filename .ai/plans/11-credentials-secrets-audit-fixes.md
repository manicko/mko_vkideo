---
phase: 06-credentials-secrets
status: ready-for-implementation
spec: .ai/audit/99-validation/06-credentials-secrets-validated-findings.md
validated_against: 0a8fa97
baseline_audit_head: 4bf9efb
baseline_reverified_at: 2026-10-03
baseline_head: 58bb7ce          # re-baselined; loader removal (d572d96) has landed
owner_decision_A: "yt-dlp is the loader; ffmpeg is NOT a download transport, but segment download stays and ffmpeg stays as the permanent segment merge engine"
owner_decision_B: "dedicated exit code 3 for configuration error — recorded only, belongs to plan 13"
owner_decision_C: "supported Python floor is 3.14 — recorded only, belongs to plan 16"
supersedes_precedent: .ai/plans/10-subprocess-browser-audit-fixes.md  # INVALID as precedent: written against a live ffmpeg loader transport
---

# Execution Plan 11 — Phase 06 (Credentials & Secrets)

**Findings store:** `.ai/audit/99-validation/06-credentials-secrets-validated-findings.md`

> **Product shape after Decision A (binding).** **yt-dlp is the loader. ffmpeg is not a download/loader transport.** The `--method ffmpeg` transport is **deleted permanently** (landed as `d572d96`). **But segment download stays, and ffmpeg stays as the segment merge engine.** `services/ffmpeg_utils.py` is **permanent product code and can never be deleted whole**; its merge stages are the only merge path the product has.
>
> **Correction to an earlier draft of this plan.** That draft filed `_merge_batch_segments` and `_perform_final_merge` in a "dies with the transport" group. **That was wrong** and it contradicted the same draft's own `§1.3`. Resolved in favour of `§1.3`: the two merge functions are permanent product surface. Every statement in this file has been brought into line; see `§1.4`.
>
> **Precedent warning.** `.ai/plans/10-subprocess-browser-audit-fixes.md` was written against a live ffmpeg loader transport and is **INVALID precedent** for anything about the loader. Its `B10` landed the deletion correctly.

---

## 1. Scope

### 1.1 How this scope was derived

The scope is the validated findings store's own disposition table, filtered through three binding owner decisions. Nothing was added that the store does not carry, and nothing the store carries as mandatory or advisory was dropped except where an owner decision retires it.

Disposition carried forward, per finding:

| ID | Store severity / class | In this plan | Where |
|---|---|---|---|
| `SEC-001` | MEDIUM · BEST-PRACTICE · mandatory | yes — **scope narrowed** by Decision A | `B2` |
| `SEC-002` | MEDIUM · BEST-PRACTICE · mandatory | yes — **scope narrowed** by Decision A | `B2` |
| `SEC-003` | MEDIUM · BEST-PRACTICE · mandatory | yes — **three oracles, not four** | `B3` |
| `SEC-004` | MEDIUM · SPEC-DEVIATION · mandatory | **no — retired by Decision A, now confirmed** | §1.4, §5.7 |
| `SEC-005` | HIGH · SPEC-DEVIATION · mandatory | yes | `B5` |
| `SEC-006` | MEDIUM · SPEC-DEVIATION · mandatory | yes — **raised priority**, now the whole leak surface | `B4` |
| `SEC-007` | HIGH · SPEC-DEVIATION · mandatory | yes — **raised priority, now the whole leak surface** | `B6` |
| `SEC-008` | MEDIUM · BEST-PRACTICE · advisory | yes | `B7` |
| `SEC-009` | HIGH · RUNTIME-ERROR · mandatory | yes | `B1` |
| `SEC-010` | MEDIUM · BEST-PRACTICE · advisory | yes | `B8` |
| `VAL-601` | MEDIUM · SPEC-DEVIATION · mandatory | yes — **audit pipeline only, not exit codes** | `B9` |
| `VAL-602` | MEDIUM · SPEC-DEVIATION · mandatory | yes — **as a constraint on `B2`, not a separate block** | `B2`, §4.1 |
| `VAL-603` | LOW · DOC-UPDATE · advisory | yes — **audit pipeline only, not exit codes** | `B10` |

`VAL-602` is not a defect with its own remedy site: it states that `SEC-001`'s and `SEC-002`'s prescribed fixes are mutually incompatible on one function. It is therefore discharged *inside* `B2` as a design constraint, exactly as the store prescribes, and verified in `B2`'s acceptance criteria.

**Decision A narrowed two findings and raised two others.** Recorded here because it changes what the remaining work *is*:

- `SEC-001` and `SEC-002` are now scoped to the **yt-dlp cookie file and the log file only**. The ffmpeg transport was the one path where signed CDN URL material and cookie material sat in a **file on disk** (`_temp_argfile`) *and* in the child's argv. That path is gone permanently, so there is nothing left to confine there.
- `SEC-006` and `SEC-007` are **unchanged in substance and raised in priority**. With the loader gone, they are no longer three sinks among four — they are the **whole of the remaining leak surface**. See §1.4's security consequence note.

**Decisions B and C are recorded, not implemented.** `VAL-601`, `VAL-602` and `VAL-603` are findings about the **audit pipeline**. They are **not** about exit codes and this plan does **not** widen them. Decision B belongs to plan 13 and Decision C to plan 16; both are recorded as constraints in §1.3 and §2.3 where they touch a block, and implemented in neither.

### 1.2 IN

1. Credential-artefact confinement and lifecycle in `services/ytdlp_downloader.py` — `_create_temp_cookie_file` and `_download_with_ytdlp`'s `finally`.
2. The three remaining D-11 permission oracles in `tests/test_hls_downloader.py` and `tests/test_config.py` — turned into executable oracles. The fourth, `test_temp_argfile_permissions_are_0600`, was **already retired with its subject** by the landed loader removal and is not this plan's work.
3. The redaction transform in `utils/url_sanitizer.py` — widened from URL-only to the artefact shapes the product's own comments already claim.
4. The terminal echo in `services/ytdlp_downloader.py::_echo_ytdlp_line`.
5. The structlog processor chain in `config.setup_logging`, plus the enumerated exception-text records.
6. The two in-process session carriers: `models/dtos.py::HLSDownloadRequest.cookies` and `services/segment_downloader.py::DownloadPolicy.headers`.
7. The Netscape serialiser's `include_subdomains` column in `services/cookies.py::_cookies_to_netscape`.
8. The browser-context cookie harvest in `services/extractor.py::VKVideoExtractor._extract_with_browser`.
9. Two pipeline documents: the severity table in `.kilo/commands/audit/phases/99-audit-validate.md` and the tail of `.ai/audit/templates/audit-findings.md`.

### 1.3 OUT

1. **The ffmpeg transport.** Not hardened, not repaired, not documented. See §1.4.
2. **`downloader._temp_argfile` and `downloader._format_argfile`.** Both exist only to serve the ffmpeg transport. `B3` retires the oracle that covers `_temp_argfile`; it does not touch the function. Phase 07 `ART-007` also names `_temp_argfile` — that collision is a *deletion* collision, not a repair one, and belongs to the removal track.
3. **`ffmpeg_download_failed`, `batch_merge_failed`, `final_merge_failed`.** Assigned to plan 10 `B14`. `B6` must not re-claim them. **Correction to an earlier draft of this plan:** two of these are **not** casualties of the loader removal — `batch_merge_failed` and `final_merge_failed` belong to `_merge_batch_segments` and `_perform_final_merge`, which are **permanent product surface** under Decision A (see §1.4). Only the loader-framed `ffmpeg_download_failed` died. `B6` still touches none of the three.
4. **Any new dependency.** No `psutil`, no `pywin32`/`win32security`, no `portalocker`. House rule 7 plus the packaging manifest argue against it; where a capability is unavailable without one, the plan records the gap rather than adding it.
5. **A shared-constants module.** None exists and none is created. All domain enums live in `models/enums.py`.
6. **Polars.** House rule 11 says "all data processing must use Polars". This project has **no Polars and no dependency for it**, and this phase's subject needs none. **Recorded divergence — do not introduce Polars.**
7. **A standalone documentation block.** This plan creates no new documentation file. Its documentation obligation is in-block: the `SEC-001:`/`SEC-002:`/`SEC-003:` code comments and the docstrings whose claims change. The three ffmpeg-framed documentation sites belong to the removal track (§2.4).
8. **The stdlib-`logging` module form.** House rule 12 names stdlib `logging`; the entire codebase uses `structlog.get_logger(__name__)`. Recorded divergence — new code uses structlog.

### 1.4 Deferred and retired

#### 1.4.1 `SEC-004` — RETIRED, NOT FIXED, NOW CONFIRMED

Decision A settles `SEC-004`: with one loader there is no argv asymmetry left to breach, and the transport that carried the asymmetry is deleted permanently (`d572d96`, landed). **No block plans work on it.** Recorded as **superseded by Decision A**.

**Its removal surface, re-derived against the current tree** (the source report called it "ten public surfaces and eight documentation files"; this is the corrected list, split by what actually happened):

**Deleted permanently — the loader-only surface:**

| Symbol | Status |
|---|---|
| `DownloadMethod.FFMPEG` | deleted; `DownloadMethod` now dispatches `YTDLP` / `AUTO` only |
| `HLSDownloader.download_with_ffmpeg` | deleted |
| `downloader._temp_argfile` | deleted |
| `downloader._format_argfile` | deleted |
| `FfmpegProgress` | deleted |
| `ProgressParser`, `read_progress`, `_PROGRESS_KEY_HANDLERS` | deleted |
| the `--method ffmpeg` value and its Typer option help | deleted |

**Permanent product surface — ffmpeg stays as the segment merge engine:**

| Symbol | Why it stays |
|---|---|
| `services/ffmpeg_utils.py` | **the module itself can never be deleted whole.** It is permanent product code. |
| `_merge_batch_segments` | a **merge stage on the only merge path the product has.** It and `_perform_final_merge` are the two stages of that path. **Correction: an earlier draft of this plan filed both of these in a "dies with the transport" group. That was wrong and it contradicted its own §1.3; resolved in favour of §1.3.** |
| `_perform_final_merge` | the second merge stage of the same permanent path |
| `_merge_segments_batched` | the batched merge the segment layer needs |
| `check_ffmpeg_available` | **confirmed correct to keep** by Decision A. Two plans disagreed; the ruling is settled in favour of keeping it. **No longer an open question in any block of this plan.** |
| `_check_merge_space`, `_required_merge_bytes`, `_build_ffmpeg_concat_command`, `_await_ffmpeg_with_timeout` | the merge engine's supporting surface — permanent |
| `iter_process_lines`, `cancel_subprocess`, `cancel_ffmpeg_process` | **the yt-dlp transport's** stdout draining and cancellation. yt-dlp is the loader that remains, so these stay. `B5` reads through `iter_process_lines` and must not change its contract. |

**Documentation sites for the loader's removal** (owned by the removal track, not by this plan): `docs/01-tools/vkdownloader-overview.md`, `docs/01-tools/api-reference.md`, `docs/01-tools/quality-selection.md`, `docs/11-guides/configuration.md`, `docs/11-guides/vkdownloader-limitations.md`, `docs/99-reference/cli-reference.md`, `docs/99-reference/cli-reference-clean.md` (the duplicate), and the ffmpeg row of the download-method comparison.

**What Decision A reduces.** `SEC-003` by **exactly one of its four oracles** — `test_temp_argfile_permissions_are_0600`, deleted with its subject (already landed). `SEC-004`'s justification entirely. And documented skip **S-3** — whether ffmpeg's own cookie reader accepts the Netscape expiry column — **stays permanently unanswerable**: with the loader gone there is no consumer of the Netscape expiry column for ffmpeg, so the question has nothing to attach to. **Re-record S-3 as retired, not answered.**

**What Decision A does not reduce.** `SEC-001`, `SEC-002`, `SEC-005`, `SEC-006`, `SEC-007`, `SEC-008`, `SEC-010`, `VAL-602` — none by more than a fraction, and the first two only in *scope*, not in substance.

#### 1.4.2 The security consequence of Decision A — recorded because it runs in this plan's favour

The ffmpeg loader transport was the one path in the product where **signed CDN URL material and cookie material sat simultaneously in a file on disk** (`_temp_argfile`, with the cookie-file path appended to the m3u8 as a query parameter) **and in the child's argv**. That path is gone permanently. Two consequences, both of which narrow this plan's remaining work and are stated here so they are not argued again later:

1. **`SEC-001`/`SEC-002` artefact confinement is now scoped to two artefacts only:** the **yt-dlp cookie file** (`ytdlp_downloader._create_temp_cookie_file`) and the **log file** (`config.setup_logging`). There is no third artefact to confine, no second consumer of `_create_temp_cookie_file` outside `_build_ytdlp_cli_command`, and no argfile whose path needed the same treatment. `B2` is correspondingly smaller and its test surface is correspondingly smaller — but the *defect* is unchanged on both surviving artefacts, and `os.chmod(…, 0o600)` is still a measured no-op on Windows for both.
2. **`SEC-006` and `SEC-007` are now the whole remaining leak surface.** Before Decision A there were four surfaces carrying child output and exception text. The loader's two are gone with it. What remains is exactly: (a) the transform, which cannot match a filesystem path or a header value (`SEC-006`), and (b) the exception-text and `exc_info` records that carry untransformed text into the persisted log (`SEC-007`). **Neither is a nice-to-have. Together they are the entire remaining exposure, which is why `B4` and `B6` keep their HIGH/MEDIUM mandatory weight and why `B6` remains the highest-risk and highest-priority block in this plan.**

**A new instance of exactly this surface appeared after this plan's original baseline**, which is evidence the surface is live rather than theoretical: `ytdlp_downloader`'s `finally:` now records `cookie_file_cleanup_failed` with **`path=str(cookie_file)`** — the cookie artefact's path written to the log **verbatim** — alongside `error=str(exc)`. That single record is simultaneously a `SEC-006` instance (a path the transform cannot match) and a `SEC-007` instance (untransformed exception text). It is counted in `B6`'s enumeration and is named in `B4`'s scope.

**The residue an Implementor must not mistake for closure.** The yt-dlp loader still passes `--cookies <path>` as a bare argv element. That is correct behaviour — yt-dlp has no response-file mechanism for option values — and the artefact now sits in a per-run private directory (`B2`), so the exposure `B2` addresses is the file's **confidentiality**, not its **process-listing** visibility. **Do not invent a transport-level fix for `SEC-004`**: the correct action was deletion, it has landed, and it is permanent.

#### 1.4.3 Deferred capability inside `B2`

The DACL-probe half of `SEC-001`'s recommendation. See `D-2` in §3.2.

---

## 2. Baseline

### 2.1 Verification commands — re-run, not inherited

Every command below was executed against the live tree at **`HEAD = 58bb7ce`**, after the loader removal landed. Results are measurements, not inherited claims. **This section supersedes the `4bf9efb` measurements an earlier draft carried; that draft predated the loader removal and three of its numbers are now wrong.**

| Command | Measured result | Exit | Role |
|---|---|---|---|
| `uv run pytest -q -rs` | **752 passed, 3 skipped, 1 warning in 44.91s** | 0 | full-suite gate |
| `uv run ruff check src tests` | **All checks passed!** | 0 | lint gate |
| `uv run ruff format --check src tests` | **Would reformat: `tests/test_hls_downloader.py`** — 1 file would be reformatted, 53 already formatted | **1** | **RED at baseline — see below** |
| `uv run mypy src` | **Success: no issues found in 31 source files** | 0 | types gate |
| `uv run mypy src tests` | **Found 86 errors in 8 files (checked 54 source files)** | 1 | **delta gate only** — never a pass/fail gate |
| `uv run pytest tests/test_config.py tests/test_hls_downloader.py -q -rs -k "…"` | **3 skipped**, all three with the D-11 reason | 0 | the skip-set identity check |

**The skip floor is 3, not 4.** Re-derived by running them:

- `tests/test_config.py::…::test_log_file_created_with_owner_only_permissions`
- `tests/test_config.py::…::test_existing_log_file_permissions_updated`
- `tests/test_hls_downloader.py::TestCreateTempCookieFile::test_file_permissions_are_0600`

`test_temp_argfile_permissions_are_0600` and its subject `_temp_argfile` were deleted with the loader in an already-landed commit.

> **Corrected skip rule.** The floor is **3**. A **fourth** skip anywhere is review-blocking; **more than 4** is a hard stop. The earlier draft's "strictly lower than 4" and "a fifth skip is review-blocking" framing is **withdrawn as stale** — the floor fell because of the loader removal, not because of anything this plan did, and `B3` must be measured against the **3-skip** baseline instead. `B3`'s rewritten criteria are in §3.3; the rule they now enforce is "**strictly lower than 3, or an explicit, justified, named conversion**".

> **New red gate at baseline: `ruff format --check src tests` exits 1** on `tests/test_hls_downloader.py`. This is **pre-existing at `58bb7ce`**, not caused by this plan, and it is recorded rather than hidden. Three blocks edit that file (`B2`, `B3`, `B5`). Whoever touches it must either reformat it — a formatting-only change, committable on its own or folded into the block that already opens the file — or state in the block's commit message that the pre-existing red was left untouched. **No block may silently absorb the reformat into an unrelated change.** Re-measure the file count before citing it; it moves with every commit.

**mypy is a usable `src`-only gate.** `strict = true` with exactly one override (`pyproject.toml`, `module = "vkdownloader.cli"`, `disallow_untyped_decorators = false`), `ignore_missing_imports = true`. **Consequence for `B7`:** `ignore_missing_imports = true` will hide an undeclared import from mypy, so `B7` must verify its `SecretStr` import resolves against the declared `pydantic` dependency by inspection, not by a green gate.

**The delta gate moved: 79 → 86 errors in 8 files.** `tests/test_hls_downloader.py` and `tests/test_downloader.py` changed substantially with the loader removal. The dominant new class is `Module "vkdownloader.services.downloader" does not explicitly export attribute …` — the backward-compat re-export block in `downloader.py` is marked `# noqa: F401` for ruff but mypy's `--no-implicit-reexport` still rejects the private names. **These 86 are the baseline; a block may not push the count above it.** Re-measure before citing; the number moves with every commit.

**Invalid or forbidden invocations.**

- `uv run ruff check .` is **RED** on untracked `tmp/` scratch and is **not a gate**.
- `uv run mypy` with no path is an invalid invocation.
- `uv run mypy src tests` is a delta gate: the count may not rise above **86**; the exit code is meaningless.

**Measured machine facts.** Point-in-time machine facts are evidence, never repo facts: the `%TEMP%` residue count, the DACL of the temp root, and the `0o444` positive control. A future Implementor may **re-measure** them; no block may **assert** them.

### 2.2 Anchor discipline — no `file:line` from the store

**No `file:line` from the validated artifact is used anywhere in this plan.** Every anchor is a symbol name, re-derived against the live tree in this session.

The store's own claim that "every anchor was re-measured and is unchanged" is **falsified**. Measured drift is `+1…+34` in the six service modules and `+63…+87` in the test files. **Two cited constructs do not exist at all**: `config.py` has **zero** `logger.` calls, and neither `download_dir_empty_string_using_default` nor `unknown_env_var_ignored` exists anywhere in the tree. A future Implementor who reaches for a line number from the store is reading a citation that was never true.

### 2.3 Binding project rules and repository constraints

1. **Commit shape** `{type}({scope}): {description}`. Stage by **explicit path**. Never `git add -A`, `.`, or `-u`. Never amend, never force-push.
2. **`tests/test_packaging.py` pins the artefact entry sets.** Measured: `EXPECTED_SDIST_ENTRIES` = **73** entries, `EXPECTED_WHEEL_ENTRIES` = **32** entries, `BUILDER_ADDED_SDIST_ENTRIES` = **2**. Both frozensets are asserted against a **real build**. **Any new file under `src/`, `tests/`, or `docs/` requires editing the relevant frozenset in the same commit.** Re-measure before citing; the counts move. *This plan is designed to add no file at all* — see the per-block `files` lists, all of which are existing paths.
3. **`_create_temp_cookie_file` now has one production call site and one backward-compat re-export.** The loader's use is gone. The **two** remaining call sites are both in `ytdlp_downloader._build_ytdlp_cli_command` — its `raw_cookies` branch and its `cookies` branch. `downloader.py` re-exports the name under `# noqa: F401` for backward compatibility but does not call it. One test module imports it directly. **Re-derive this count at execution time; it is the number `B2`'s sweep must cover, and an undiscovered third call site is an `Auditor` finding.**
4. **The `mkstemp` prefix `vk_cookies_` and suffix `.cookies.txt` are load-bearing beyond this phase.** `.gitignore` matches the suffix (`*_cookies.txt`); `B2`'s reaper is keyed on the prefix. **Renaming either breaks ignore coverage silently** and orphans every in-flight artefact. Both strings are frozen by `B2`.
5. **No `print()`; no `Any`; Pydantic v2 only; English only.**
6. **Layer rules** (`docs/STRUCT.md`): the entry layer (`cli.py`, `__main__.py`) may not import private symbols from the service or utils layers. `config.py` is entry-adjacent and today imports only from `vkdownloader.models.enums`; `B6` adds its first `utils` import and must take a **public** symbol name. `services/` may import private `utils` symbols internally — that is how `ytdlp_downloader.py` already imports `_strip_auth_params`.
7. **structlog, not stdlib logging, for all new log calls** (`logger = get_logger(__name__)`), despite house rule 12's stdlib wording.
8. **The two CLI commands' option blocks must stay byte-identical** except the `--max-retries` help string. No block here edits a Typer option block. **`DownloadMethod` now dispatches `YTDLP` / `AUTO` only** — the `--method` option lost its `ffmpeg` value with the loader, and no block restores it.
9. **The patch target `vkdownloader.cli.warn_unknown_env_vars` must survive.** Untouched here.
10. **All domain enums live in `models/enums.py`. There is no shared-constants module and none may be created.**
11. **Decision B — the four-code exit contract. Recorded, not implemented.** `3` is a dedicated configuration-error code; `1` is download-failure-only; `2` is usage error; `4` and above are unallocated. **Implemented by plan 13, not here.** This plan produces **no** status code and documents **no** exit-code table. One constraint is binding on `B6` specifically: `cli.py` currently raises `typer.Exit(code=1)` for `_PreambleFailure` (the configuration-error carrier) as well as for download failures, so **plan 13's re-code of that arm will change the log records `B6`'s processor renders**. `B6` must therefore keep its processor **key-agnostic and event-name-agnostic** — it must not special-case `download_failed` or any other event name on the assumption that its meaning is fixed. Plan 13 owns the doc site (`docs/99-reference/cli-reference.md`'s exit-code table), not this plan. **No `VAL-` finding in this plan is an exit-code finding and none is widened to become one.**
12. **Decision C — the Python floor. Recorded, not implemented.** The supported floor is **3.14**; `requires-python` becomes `>=3.14`. **Implemented by plan 16, not here.** Checked against every block in this plan: **no block depends on any Python version below 3.14, and no block uses a construct that 3.14 removes.** Specifically — no reliance on deprecated `typing` aliases, no `distutils`, no `imp`, no removed `locale`/`cgi`/`crypt` surface, and nothing version-gated. The one construct that moves is in `B2`'s liveness probe (`ctypes` `OpenProcess`/`GetExitCodeProcess`) and it is **more** robust on 3.14, not less. `B2`'s POSIX branch (`os.kill(pid, 0)`) is unchanged by the floor. **Recorded answer: no dependency, no action.**
13. **`AGENTS.md` does not exist** in this repository. Any instruction that references it is void; the binding rules are the house rules and this file.

### 2.4 Documentation sites and their owners

| Site | Claim at risk | Owner |
|---|---|---|
| `docs/01-tools/vkdownloader-overview.md` — "Secret-safe ffmpeg argument passing" | `0o600` / D-11 confinement; the ffmpeg `@argfile` mechanism | removal track (landed) |
| `docs/01-tools/vkdownloader-overview.md` — "Secret-safe cookie passing" | `0o600` / D-11 on the cookie file, ffmpeg-framed | removal track (landed) |
| `docs/01-tools/api-reference.md` — `download_with_ffmpeg` behaviour note | same | removal track (landed) |
| `docs/11-guides/vkdownloader-limitations.md` — CDN-cookie workaround | same | removal track (landed) |
| `docs/11-guides/configuration.md`, `docs/01-tools/quality-selection.md`, `docs/99-reference/cli-reference.md`, `docs/99-reference/cli-reference-clean.md` | `--method ffmpeg`, the ffmpeg row of the method comparison | removal track (landed) |
| `docs/11-guides/vkdownloader-limitations.md` — the segment-merge disk-space section and `docs/01-tools/api-reference.md`'s reference to it | describes the **merge engine**, which **stays** under Decision A | **not this plan's** — must **survive** the loader removal; a removal track that deleted it would be deleting live documentation |
| `config.setup_logging` — the `SEC-003:` comment above the log-file `touch`/`chmod` branches | the D-11 caveat's wording | **`B3`** |
| `services/ytdlp_downloader.py` — the `DF-007:` comment above `os.chmod(path, 0o600)` | the artefact's confinement claim | **`B2`** |
| `services/ytdlp_downloader.py` — the `SEC-002:` comment above the `download_failed` sanitisation | "redact … cookie file paths" — only true after `B4` | **`B4`** (claim half ceded to us by plan 10 `B7`) |
| `services/ytdlp_downloader.py` — the `cookie_file_cleanup_failed` record's `path=str(cookie_file)` | a cookie-artefact path written to the log verbatim | **`B4`** (the path becomes matchable) + **`B6`** (the record joins the covered set) |
| `utils/url_sanitizer.py::sanitize_text_for_log` docstring | "preventing signed CDN tokens or cookie file paths … from leaking" — only true after `B4` | **`B4`** (wording ownership recorded in §4.3) |

No documentation file is created or deleted by this plan.

### 2.5 The landing rule

One commit per block. A block's commit contains everything that block needs to be independently correct: its product change, its tests, its own documentation corrections, and — if and only if it adds a file — the `tests/test_packaging.py` frozenset edit for that file. **No block's commit may be red** and no block may leave the tree in a state where a later block's tests fail. A block that cannot be landed alone does not get its own block; it gets merged into one that can.

Two consequences:

- `B2` lands `SEC-001`, `SEC-002` **and** `VAL-602` together. This is not a bundling convenience; `VAL-602` exists precisely because those two are not separately landable.
- `B3` may **not** be folded into `B2`, because its acceptance criterion is "an oracle runs on the declared platform and would fail if `B2` were reverted" — which is only a meaningful statement once `B2` is on the branch.

### 2.6 Test layout for these subjects

| File | Owns | Blocks that extend it |
|---|---|---|
| `tests/test_cookies.py` | The only file that drives the serialiser through the **real** `YoutubeDLCookieJar`. Module-level `_DOMAIN = ".vkvideo.ru"` hard-coded in `_cookie`, `_cookie_without_expiry_key`, `_cookie_with_null_expiry`. **No dotless case exists.** | `B1` |
| `tests/test_url_sanitizer.py` | `TestStripAuthParams` (8 tests) and `TestSanitizeTextForLog` (4 tests). **No path-shaped and no header-shaped input.** | `B4` |
| `tests/test_hls_downloader.py` | Both D-11 artefact oracles; `TestCreateTempCookieFile`; the `_echo_ytdlp_line` contract tests (`test_…_echo_false_suppresses_stderr_while_callback_fires`, `test_…_echo_false_no_callback_stderr_empty`, `test_…_echo_false_progress_emits_debug_log`, `test_…_echo_false_non_progress_line_no_output_no_log`, and the progress/non-progress rewrite tests); the dotless `Cookie(domain="vkvideo.ru")` fixture in `test_cli_command_creates_cookie_file_for_cookies`, which asserts `--cookies` presence and **never loads the file** | `B2`, `B3`, `B5` |
| `tests/test_config.py` | Both D-11 log-file oracles; `setup_logging` tests | `B3`, `B6` |
| `tests/test_packaging.py` | The two pinned entry sets | none (no block adds a file) |
| `tests/test_security.py` | `validate_output_path`, `sanitize_title` — path traversal, **not** a credential subject | none |
| `tests/test_extractor.py` | builds `{"domain": "vkvideo.ru"}` and asserts on a substring | `B8` |

**A test that pins behaviour the block is changing must be updated in the same commit, and the update must be visible as a change in the expectation — never a relaxation.** `B5`'s most relevant existing contract is the assertion that a **non-progress** line is passed through **unchanged**; that contract stays true for benign input and gains a redacting sibling case.

### 2.7 Reachability — measured, not assumed

The credential-artefact and harvest paths are reachable **without** the operator passing `--cookie-source browser`. `VKDOWNLOADER_COOKIE_SOURCE=browser` in the process environment yields `Settings().cookie_source == browser`, and a `.env` line does the same. The source report's header correction holds: `.env` and the process environment are triggers **in addition to** the flag.

`echo` is an **undocumented reachability switch**. `batch_downloader._download_one_video`'s caller sets `echo = not reporter.is_enabled`, so **batch mode never reaches the untransformed terminal sink** that `SEC-005` describes. `B5`'s contract therefore has three live clauses, all pinned by existing tests: the `\r` rewrite for progress lines, `echo=False` writing **nothing** at all, and the DEBUG-only `ytdlp_progress_suppressed` record.

---

## 3. Execution blocks

### 3.0 Block header conventions

Every block states: goal, findings carried, exact semantic scope (symbols, never line numbers), files, alternatives where genuine technical uncertainty exists, acceptance criteria, out-of-scope, required agent roster, and commit shape.

**Agent roster meanings.**

- **Auditor** — deeper code/architecture investigation is required before the block can be written; the mechanism or the enumeration is not yet certain.
- **Researcher** — platform or library behaviour must be settled against authoritative sources before code is written (Windows API semantics, structlog processor contracts).
- **Planner** — the block needs a detailed pre-implementation design; more than one coherent design exists and the sequence inside the block matters.
- **Validator** — independent review before landing; implementation risk is high enough that a second reader must confirm the finding is actually closed and nothing else broke.

**Open decisions** are carried as `D-n` and are deliberately **not** resolved in this plan wherever the choice changes behaviour or depends on an unmeasured platform fact. Each carries its default and its decision criterion so an Implementor is never blocked, only informed.

### 3.1 `B1` — Derive the Netscape `include_subdomains` column from the domain instead of hard-coding it

**Findings carried:** `SEC-009` — **HIGH** · `RUNTIME-ERROR` · mandatory. Half of phase 10 `TST-002` (CRITICAL).

**Goal.** A cookie whose domain is host-only (`vkvideo.ru`, no leading dot) currently produces a line whose `include_subdomains` column says `TRUE`, and `http.cookiejar.MozillaCookieJar._really_load` then rejects the **entire file** with an `assert domain_specified == initial_dot`. One host-only cookie therefore discards every cookie in the file. The column must be derived from the domain.

**Exact semantic scope.**

- `services/cookies.py::_cookies_to_netscape` — the `list[Cookie]` branch, the single f-string that emits the Netscape row. The literal `TRUE` in the `include_subdomains` position becomes an expression derived from `domain`.
- The decision rule: **leading dot ⇒ `TRUE`, no leading dot ⇒ `FALSE`.** This is the inverse of the assertion `MozillaCookieJar` applies, so a derived column and the assertion cannot disagree.
- The legacy `str` branch writes `.vkvideo.ru\tTRUE` and is **already correct**. Do not "unify" it with the derived expression; it is a separate format branch with a fixed domain.

**Files.** `src/vkdownloader/services/cookies.py`, `tests/test_cookies.py`. **No new file.**

**Not in scope.** `_normalize_expiry` (D-02, correct and already covered). `_sanitize_cookie_value` (CRLF strip, correct). The legacy `str` branch.

**Alternatives where uncertainty exists.**

- **Alt A (default): derive the column from the domain string.** One expression, one line. Matches the consumer's assertion by construction.
- **Alt B: always write `FALSE`.** Simpler, and it is correct for a host-only domain — but it *loses* sub-domain scope for a genuine `.vkvideo.ru` cookie, changing behaviour for the case that currently works. Rejected on regression grounds.
- **Alt C: drop the row and let the consumer re-derive.** Not expressible in the Netscape format. Not available.

**Acceptance criteria.**

1. A dotless-domain cookie survives a **real** `YoutubeDLCookieJar` round trip: written by `_create_temp_cookie_file`, read by `jar.load()`, present in the jar with its value intact. This is the round-trip harness `tests/test_cookies.py::TestCookieRoundTripThroughConsumer` already provides — the new test joins that class, it does not invent a harness.
2. The existing dotted-domain case still round-trips, and the existing three-expiry cases are untouched.
3. A mixed file — one dotted cookie **and** one host-only cookie, written in that order — survives `jar.load()` with **both** cookies present. This is the case the defect actually destroys, and a single-host-only test would not have caught it.
4. `uv run mypy src` clean; `uv run ruff check src tests` clean; `uv run pytest tests/test_cookies.py -q` green.

**Test-pinning hazard.** `tests/test_cookies.py` has module-level `_DOMAIN = ".vkvideo.ru"` hard-coded into **three** fixture builders. A dotless case needs either a new builder that takes a domain or a domain parameter on the existing ones. Changing `_DOMAIN` itself would silently re-aim every existing case. **Add, do not retarget.**

**Collision.** Phase 10 `TST-002` (CRITICAL) owns the *test* for the identical `cookies.py` mechanism and wants the failing test written first. `TST-002` has not executed. See §4.3 for the reconciliation rule.

**Required agents:** **Auditor** (confirm the enumeration of Netscape-row emitters — that there is no fourth branch, and that no other writer of this format exists in `src/`), **Validator** (the finding was filed `observed` with a live reproduction; the closure must be re-observed, not reasoned about). **Researcher and Planner not required** — the fix is one expression and the alternatives are settled by the consumer's own assertion.

**Commit:** `fix(cookies): derive Netscape include_subdomains from the cookie domain`

---

### 3.2 `B2` — Give the credential artefact a per-run private directory and a lifecycle that survives a hard kill

**Findings carried:** `SEC-001` (MEDIUM · BEST-PRACTICE · mandatory), `SEC-002` (MEDIUM · BEST-PRACTICE · mandatory), `VAL-602` (MEDIUM · SPEC-DEVIATION · mandatory — **discharged here as a constraint, not as separate work**).

**Goal.** Two defects on one function, prescribed incompatibly by the store, which is itself finding `VAL-602`.

- `SEC-001`: the artefact's confidentiality has **no product-side control** at all. `os.chmod(path, 0o600)` is a measured no-op on Windows — `0o600 & stat.S_IWRITE == 0o200`, so the requested mode clears exactly the bit the platform honours. The file inherits the temp root's ACL, which the environment measurement showed carries **four** principals.
- `SEC-002`: a borrowed session survives `taskkill /F` indefinitely. There is no `atexit` hook, no forcible-termination handler, and no orphan sweep anywhere in `src/`. A sweep is what makes the residue reclaimable **by the next run** rather than only by the operator.

`VAL-602` states the two prescribed fixes are incompatible and that the glob sweep is unsafe under concurrency, and prescribes the reconciled form. **This block implements that reconciled form.** It is one commit because `VAL-602` says it must be.

**Scope narrowed by Decision A.** The block's scope is now the **yt-dlp cookie file and the log file only**. The ffmpeg loader transport — the one path where cookie material sat in a second file on disk *and* in the child's argv — is gone permanently (§1.4.2). `_create_temp_cookie_file` has **one** production call site (`_build_ytdlp_cli_command`, two branches) plus a backward-compat re-export in `downloader.py`. There is no argfile left to confine and no second artefact consumer. **The defects on the two surviving artefacts are unchanged** — `os.chmod(…, 0o600)` is still a no-op for both — so the block is smaller, not weaker.

**Exact semantic scope.**

- `services/ytdlp_downloader.py::_create_temp_cookie_file` — the artefact's location and the owning-process record. The `mkstemp` call moves from the shared temp root into a per-run private directory; the directory records the owning PID.
- `services/ytdlp_downloader.py::_download_with_ytdlp` — the `finally:` block. It becomes directory-level teardown. **Every interceptable end is already correct today.** The sequence has since gained an `OSError` arm — `cookie_file.unlink(missing_ok=True)` inside a `try`, a failed destroy recorded as `cookie_file_cleanup_failed`, and `cookie_file_cleaned_up` on the `else` branch — so that a failed destroy cannot replace the download's outcome. **That arm is the current correct state and `B2` preserves it exactly**, adding directory teardown after it. It also means `B2` is not a two-line edit to a three-line `finally`.
- A **sweep** that runs before this process creates any artefact, and only over **this product's own artefact directories**, deleting a directory only when its recorded PID is no longer live.
- An **`atexit`** registration for the orderly-exit path.
- The `DF-007:` comment above the `os.chmod` call — its claim changes and must be corrected in the same commit (§2.4).

**Frozen strings — renaming either breaks coverage silently.** The `mkstemp` **prefix `vk_cookies_`** and **suffix `.cookies.txt`** stay exactly as they are. `.gitignore` matches the suffix; this block's sweep is keyed on the prefix. The `os.chmod(path, 0o600)` call **stays** for its POSIX effect.

**Files.** `src/vkdownloader/services/ytdlp_downloader.py`, `tests/test_hls_downloader.py`. **No new file** — deliberately. A new `utils/` or `services/` module would require a `tests/test_packaging.py` frozenset edit, and §2.5 forbids that unless the block needs it. This block keeps the lifecycle in the module that already owns the artefact, which is also the module every consumer already imports.

**Out of scope.** `downloader._temp_argfile` (transported away). The log file's own `touch`/`chmod` branches in `config.setup_logging` — a **different** artefact, chosen by the operator in a directory the operator chose; its confinement is `SEC-003`'s subject, not this block's. `signal_handlers` (its handled-signal set and its shutdown-`Event` behaviour are correct as they stand).

**Open decisions.**

- **`D-1` — the Windows PID-liveness probe.** Default: `ctypes` `kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, …)` + `GetExitCodeProcess`, treating `STILL_ACTIVE` (259) as alive; on POSIX, `os.kill(pid, 0)`. **Criterion:** confirm against the installed CPython 3.12 whether `os.kill(pid, 0)` **terminates** the target on Windows. The documented Windows behaviour of `os.kill` is that a signal value other than the two console-control values causes `TerminateProcess` to be called — if that holds for `0`, then `os.kill(pid, 0)` is **prohibited on the Windows branch** and a reader must not "simplify" the `ctypes` probe away. **Do not test this against a live process.** Verify it from the CPython source or the documentation, and record the citation in the commit message. Alternative: an exclusive OS lock held on a marker file for the process lifetime (`msvcrt.locking` on Windows, `fcntl.flock` on POSIX) — no liveness syscall at all, but it holds a descriptor open for the process lifetime and is a larger behavioural change. Default is the probe.
- **`D-2` — the DACL-probe half of `SEC-001`'s recommendation is deferred.** `SEC-001`'s remedy has two halves: (i) create the artefact in a per-run private directory; (ii) probe the parent directory's DACL and fall back when it is wider than the owner. Half (ii) needs `win32security` (pywin32, **not a dependency**) or hand-rolled `ctypes` ACL reading. **Default: ship half (i) only**, which is the structural change that also resolves `VAL-602`'s ordering trap, and record half (ii) as a named deferred capability with its dependency named. **Criterion to revive it:** an owner decision to accept a `ctypes` ACL reader, or a decision to add `pywin32`. Adding a dependency unilaterally is prohibited (§1.3.4).
- **`D-3` — where the sweep is anchored.** Default: a module-level guard in `ytdlp_downloader.py`, invoked on first artefact creation, that (a) sweeps stale directories and (b) creates and records this run's directory. Rationale: it is the earliest point at which the process has committed to creating an artefact, it needs no wiring in `cli.py` or `config.py`, and it cannot be bypassed by a caller. Alternative: register at `cli.py`'s command preamble — rejected, because it makes the guarantee depend on an entry-layer call that a library consumer would not make, and it puts a `services` import obligation on the entry layer.

**Alternatives for the confinement mechanism as a whole.**

- **Alt A (default): per-run private directory + PID record + liveness-gated sweep + `atexit`.** Directly implements `VAL-602`'s reconciled prescription. Closes `SEC-001`'s structural gap (the artefact is confined by *where it is*, not by a mode bit that does nothing on the declared platform) and `SEC-002`'s residue problem (the next run reclaims it).
- **Alt B: `atexit` only.** Narrower. Closes orderly exits, leaves `taskkill /F` residue forever. Does not close `SEC-002` as filed.
- **Alt C: age-based sweep over a top-level glob.** **Rejected** — `VAL-602` rules it unsafe under concurrency, and it is unsafe in a second way: it would sweep artefacts belonging to other tools in a shared temp root.
- **Alt D: a Windows-specific DACL setter on the file.** Rejected: needs pywin32 or a hand-rolled `ctypes` ACL write, changes the artefact's ACL rather than its location, and leaves the directory itself shared.

**Acceptance criteria.**

1. The artefact is created **inside a directory this process created**, and that directory is removed on every interceptable end (the `finally:`), not only the file.
2. The `mkstemp` prefix `vk_cookies_` and suffix `.cookies.txt` are **unchanged**.
3. The existing `cookie_file.exists()` → `unlink(missing_ok=True)` → `logger.debug("cookie_file_cleaned_up")` sequence is **still present** in the `finally:` and still logged under the same event name. Existing tests that pin it are green unchanged.
4. A test creates a stale artefact directory carrying a recorded PID that is **not live**, invokes the sweep, and asserts the directory is gone. This runs on Windows — it is not an oracle about a mode bit.
5. A test creates a stale artefact directory carrying a **live** PID, invokes the sweep, and asserts the directory **survives**. This is the concurrency-safety half of `VAL-602` and is the test that makes the sweep's design claim checkable rather than asserted.
6. A test records the owning directory and asserts the artefact's parent is that directory and not the shared temp root.
7. `atexit` is registered exactly once per process (repeat artefact creation must not register a second hook).
8. `tests/test_hls_downloader.py::TestCreateTempCookieFile` and every existing `test_cli_command_creates_cookie_file_for_cookies` case is green **without a change in expectation** — only additions. If an existing expectation must change, that is a design failure, not a test update.
9. `uv run pytest -q -rs` green with the skip count **not above** 4. `uv run mypy src` clean. `uv run ruff check src tests` and `uv run ruff format --check src tests` clean.

**Test-pinning hazard — the one this plan cannot delegate.** The remaining D-11 oracles skip on Windows, so **the current suite cannot see a lifecycle regression here at all.** Criteria 4–6 are therefore not optional: they are the only executable evidence `B2` produces on the declared platform.

**Collision.** Plan 10 `B1` claims the same `finally:` block. See §4.3. This block also touches the `DF-007:` comment.

**Required agents:** **Researcher** (`D-1`'s `os.kill`-on-Windows semantics must be settled from authoritative sources before code is written — this is a correctness-of-safety question, not a style question), **Planner** (the sweep's guard structure, the teardown order in `finally:`, and the `atexit` registration point interact; more than one coherent internal sequence exists), **Auditor** (confirm no second artefact writer or second temp-path consumer exists that the sweep would miss), **Validator** (HIGH implementation risk: this adds a filesystem lifecycle with concurrency semantics to a path the visible test suite cannot currently observe).

**Commit:** `fix(cookies): confine the credential artefact to a per-run private directory with a liveness-gated sweep`

---

### 3.3 `B3` — Replace the platform-skipped permission oracles with oracles that actually execute

**Findings carried:** `SEC-003` — **MEDIUM** · BEST-PRACTICE · mandatory.

> **This block was rewritten after re-baselining.** The earlier draft had four oracles and two acceptance criteria that are now **unsatisfiable**: one required a skip count "strictly lower than 4", which an unrelated landed commit has already satisfied; the other required `tests/test_hls_downloader.py` to be co-edited with the removal of `_temp_argfile`, which happened in a **separate, already-landed** commit. Both are corrected below. **`B3` is now UNBLOCKED** — it no longer waits on the removal track. **The finding is real; only its framing was stale.** `B3` is not weakened into a no-op: it now converts **three** oracles and measures its effect against the **3-skip** baseline.

**Goal.** All remaining D-11 oracles are `skipif(os.name == "nt")`. Re-running them gives **3 skipped** — the owner-only guarantee has **zero executable oracle** on the platform the product declares support for. This block converts what can be converted, with an explicit and justified position on what cannot.

**Exact semantic scope — three oracles, not four.**

| Oracle | Subject | Disposition |
|---|---|---|
| `test_file_permissions_are_0600` (`tests/test_hls_downloader.py::TestCreateTempCookieFile`) | the yt-dlp cookie artefact | **Convert.** Assert the property `B2` actually delivers: the artefact's parent is the per-run private directory this process created, and that directory is removable. Executable on Windows, fails if `B2` is reverted. The POSIX mode assertion may be **kept as an additional, non-exclusive** check — additive, never a replacement that loses coverage. |
| `test_log_file_created_with_owner_only_permissions` (`tests/test_config.py`) | `config.setup_logging`, new log file | **Convert or reframe — `D-4`.** |
| `test_existing_log_file_permissions_updated` (`tests/test_config.py`) | `config.setup_logging`, existing log file | Same as above. |
| ~~`test_temp_argfile_permissions_are_0600`~~ | ~~`_temp_argfile`~~ | **Already retired — not this block's work.** Deleted with its subject in the landed loader removal. `B3` does not delete it and does not wait for it. |

**`D-4` — what the log-file oracles can honestly assert on Windows.** A real uncertainty with no clean answer, so it is carried, not decided.

- **Alt A (default): assert the requested mode, not the granted one.** On Windows, assert that `setup_logging` *requested* `0o600` (observable via the branch taken and the mode argument), and keep the granted-mode assertion POSIX-only. **Known weakness, stated rather than hidden:** this is close to the degenerate "assert a constant is a constant" shape the source report criticises. It is still better than a skip, because it pins that the branch and the intent survive.
- **Alt B: assert the file's read-only attribute is clear** — the `FILE_ATTRIBUTE_READONLY` bit is absent from `os.stat(...).st_file_attributes`. This is a real, Windows-meaningful assertion (it is what `os.chmod(…, 0o600)` actually computes to), and it is what the `0o444` positive control proves the platform can report. **Preferred if the Implementor accepts that it asserts "the mode request reached the platform" rather than "other principals cannot read the file".** It does not claim confinement.
- **Alt C: read the DACL** and assert the owner is the only principal — **rejected**: needs `pywin32` or a hand-rolled `ctypes` ACL reader, which §1.3.4 and `D-2` both prohibit.

**Criterion for the Implementor:** pick `B` if a Windows-meaningful assertion is wanted at acceptable cost; pick `A` if the smallest honest change is wanted. **Neither may assert owner-only confinement on Windows** — that would re-file the unverified claim the finding exists to retire. If both are unsatisfying, the honest outcome is to keep the POSIX assertion gated and add a Windows-side test that pins the **branch and the request**, plus a docstring that says plainly what is and is not guaranteed.

**Alternatives for the block as a whole.** Converting all three (rejected: two have no honest Windows-side assertion beyond `A`/`B`); converting none (rejected: that is the finding); converting one and leaving two skipped with no note (rejected: it would leave a silent 2-skip the reviewer cannot account for).

**Acceptance criteria — rewritten to what `B3` can actually demonstrate.**

1. **Each of the three surviving oracles has a Windows-executable assertion.** "Windows-executable" means the test body runs and asserts on this platform — not that it is gated. A converted oracle must fail if the property it claims is removed.
2. **`B3` demonstrates its own effect, which is now a *named conversion*, not a skip-count delta.** The earlier criterion "strictly lower than 4" is **withdrawn**: an unrelated landed commit already lowered the count, so a count delta is no longer evidence of this block's effect. `B3`'s effect is instead demonstrated by: **the count of D-11-guarded oracles drops from 3 to 0, or to whatever remains only with a per-oracle justification recorded in the commit message.** The commit message must name every oracle it converted, every oracle it left gated **and why**, and the resulting skip count. **If `B3` leaves all three gated, it has closed nothing** and must be reported as not-landed rather than landed.
3. **Every remaining skip in the suite is named in the commit message with the oracle it corresponds to.** A **fourth** D-11 skip is review-blocking; more than 4 is a hard stop. Non-D-11 skips, if any appear, must also be named and justified — the count is the reviewer's only evidence.
4. **No surviving oracle asserts owner-only confinement on Windows.** Stated positively: the docstrings say which platform each assertion holds on.
5. **The credential-artefact oracle is coupled to `B2`:** it asserts a property `B2` introduces. If `B2` has not landed, `B3` **must not** land an artefact oracle — the other two log-file oracles are independent of `B2` and may land first. Record which is which.
6. **The retired `_temp_argfile` oracle is acknowledged, not silently absent.** The commit message states that it and its subject were deleted by the landed loader removal and that `B3` neither deleted it nor reverted it. **No co-edit with that removal is required or possible** — it is a separate landed commit.
7. `config.setup_logging`'s `SEC-003:` comment matches the new reality — it no longer implies a confinement Windows does not deliver, and it no longer mentions an argfile.
8. `tests/test_hls_downloader.py` is **already red on `ruff format --check` at baseline** (§2.1). `B3` opens that file; it must either reformat it or state in the commit message that the pre-existing red was left for a separate formatting commit. **It must not fold an unrelated reformat into a test-semantics change.**

**Required agents:** **Planner** (`D-4` must be resolved with the actual `os.stat` attribute surface measured, and the resolution changes what three test bodies assert), **Auditor** (confirm the skip set is still the three D-11 oracles at execution time and that no fourth skip has appeared), **Validator** (a test-only block whose acceptance is "the evidence now runs" — an independent reader must confirm the new oracles fail when the property they claim is removed). **Researcher required only if `D-4` resolves toward `B`**, in which case the `FILE_ATTRIBUTE_READONLY` contract should be checked against authoritative Windows documentation first.

**Commit:** `test(logging): replace the skipped permission oracles with ones that execute on Windows`

---

### 3.4 `B4` — Widen the redaction transform to the artefact shapes the product's own comments already claim

**Findings carried:** `SEC-006` — **MEDIUM** · `SPEC-DEVIATION` · mandatory. **This block owns the exposure judgement** (plan 10 ceded it here — §4.3).

**Goal.** `sanitize_text_for_log` matches only `https?://`. A filesystem path and a `Cookie:` header value therefore pass through **byte-identical**. Reproduced live: the path capability (`sanitize_url_for_log`, a public alias of `_strip_auth_params`) **already exists** and is pointed elsewhere. Meanwhile three comments in `src/` and one docstring in `utils/url_sanitizer.py` already claim the transform prevents "cookie file paths" from leaking — a claim the regex cannot deliver. The block makes the claim true or removes it; it does not leave it standing.

**Exact semantic scope.**

- `utils/url_sanitizer.py::_URL_REGEX` and `sanitize_text_for_log` — the transform gains the artefact shapes. `sanitize_text_for_log` currently is a single `.sub()` with no alternative branch; widening it means adding named, individually testable rules.
- `utils/url_sanitizer.py::sanitize_text_for_log` docstring — its claim changes; corrected **in this commit**.
- `services/ytdlp_downloader.py` — the `SEC-002:` comment above the `download_failed` sanitisation ("redact … cookie file paths"). Only true once this block lands. Corrected here.
- **The live instance that proves the defect is live.** `ytdlp_downloader._download_with_ytdlp`'s `finally:` records `cookie_file_cleanup_failed` with **`path=str(cookie_file)`** — the cookie artefact's own path, written to the persisted log verbatim, on every failed destroy. That is a real `SEC-006` instance produced by the product's own code, present since the loader-removal commits. It is the sharpest available demonstration that the transform's gap is not theoretical. **No change to that record is required** — the point is that once the path rule exists, the path becomes matchable by the pipeline (`B6`) like any other text. It is named here so the next reader knows the case was seen and reasoned about, not missed.
- `utils/__init__.py` — **only if** a new public symbol is exported. Today it exports `sanitize_url_for_log` and `_strip_auth_params`. `sanitize_text_for_log` is deliberately **not** re-exported (it is imported by services directly, which the layer rules permit). Prefer no change.

**Files.** `src/vkdownloader/utils/url_sanitizer.py`, `tests/test_url_sanitizer.py`, plus the one comment in `services/ytdlp_downloader.py`. **No new file.**

**The load-bearing constraint that decides this block.** The transform's current output — `scheme://host/***REDACTED***` — is what makes `download_failed`'s `error` field **readable at all**. A token-wise fallback (the source report's second option, which routes every unmatched token through `sanitize_url_for_log`) would redact the benign portion of **every** child line and turn a useful failure record into noise. **That option is rejected.** Whatever is added must be **additive and narrowly anchored**, and must preserve the host-visibility that operators depend on.

**`D-5` — which shapes the widened transform matches.**

- **Alt A (default): artefact-name patterns only.** Match the product's own artefact naming — `vk_cookies_*.cookies.txt` and `vk_ffmpeg_*.args` — and replace the matched token with `***REDACTED***`, reusing the existing output vocabulary so the two rules read the same. This is exactly what the code's own comments claim, so it makes the existing claim true with the smallest possible change and the smallest possible false-positive surface.
- **Alt B: Alt A plus a header-value rule** (`Cookie:` / `Set-Cookie:` value redaction). Closes the second half of the measured reproduction. **But it goes beyond the product's declared intent** and introduces a rule that could match a benign line mentioning a cookie header. Adopting it is a scope increase, not a bug fix.
- **Alt C (rejected): token-wise fallback.** See the constraint above.

**Criterion:** adopt `B` only if a sink in `src/` is measured to receive a `Cookie:`/`Set-Cookie:` header **from a child process** — not from the product's own request-building code, where the value is the product's and the log site is a different problem. Default is `A`.

**The replacement shape — a decision, stated once.** Replace the matched artefact token with `***REDACTED***` rather than preserving a basename or a parent directory. A path's parent can itself be identifying (`C:\Users\<name>\AppData\…`), and preserving it buys an operator nothing they do not already have from the surrounding log line. **Criterion:** if an Implementor wants the basename preserved for triage, that is a defensible alternative — but it must be a stated decision, not a silent choice, and the matching rule must be tight enough that a benign path cannot match.

**Idempotency is a hard acceptance criterion, not a nicety.** The transform will be applied at more than one place after `B5` and `B6` land — once at a call site and once in the log pipeline. Applying it twice must be a no-op. For the URL rule that already holds (the replacement keeps `scheme://host/`, so a second pass reproduces it). **The new rules must be proved idempotent**, and `***REDACTED***` must not itself match any rule.

**Acceptance criteria.**

1. A `vk_cookies_*` artefact path in free text is redacted; the same text with no artefact-shaped token is **byte-identical** to its input.
2. A signed CDN URL still reduces to `scheme://host/***REDACTED***` — the existing four `TestSanitizeTextForLog` cases pass **unchanged**.
3. Applying the transform twice equals applying it once, for every rule, including on text that already contains `***REDACTED***`.
4. The docstring states precisely which shapes are matched and which are not. No unmatched shape is claimed.
5. If `D-5` resolved to `A`, a `Cookie:` header value is **documented as not covered** in the docstring, so the next reader is not misled — the block closes the finding by making the claim true, not by implying coverage that does not exist.
6. `tests/test_url_sanitizer.py` has **no path-shaped and no header-shaped input today**; this block adds both, as separate cases with separate names.
7. `uv run mypy src` clean; `uv run ruff check src tests` and `uv run ruff format --check src tests` clean; `tests/test_url_sanitizer.py` green.

**Collision — two, both recorded.** Plan 10 `B7` claims this function's **docstring wording** plus the yt-dlp `SEC-002:` comment; plan 10 `B14` lists the `return _URL_REGEX.sub(...)` matcher as a semantic anchor it owns **while its own body is `AWAITING DECISION` and self-contradictory**. See §4.3.

**Required agents:** **Auditor** (confirm the complete call-site set of `sanitize_text_for_log` — the measured enumeration is three call classes, and a missed sink means the block closes the finding only partially), **Researcher** (regex-design discipline for a rule that must be tight enough not to match benign child output, and idempotent under repeated application — a known-hard property worth checking against authoritative guidance on substitution-based redaction), **Planner** (`D-5`'s resolution and the interaction with the load-bearing readability constraint), **Validator** (the transform is on the path that makes failures diagnosable; an over-broad rule is a regression that no existing test would catch).

**Commit:** `fix(logging): redact the product's own artefact paths in sanitised child output`

---

### 3.5 `B5` — Apply the transform at the terminal echo, without touching the `echo` contract

**Findings carried:** `SEC-005` — **HIGH** · `SPEC-DEVIATION** · mandatory. **This block owns the yt-dlp terminal echo** (plan 10 `B14` ceded it — §4.3).

**Goal.** `_echo_ytdlp_line` writes child bytes to `sys.stderr` **untransformed** while the log file redacts the same bytes. The same child output therefore reaches the operator's terminal with a signed CDN address intact, and the persisted log with it removed.

**Reachability — measured narrower than the source report claims.** Two corrections, both re-derived here:

1. `echo` is a **keyword parameter**. `batch_downloader._download_one_video`'s caller sets `echo = not reporter.is_enabled`, so **batch mode never reaches this sink**. The defect is on the **single-download** path and anywhere else `echo=True` survives.
2. The admission predicate is **`_is_ytdlp_progress_line(line)`** — which decides whether a line takes the `\r`-rewrite branch or the raw-write branch. The source report names `_parse_ytdlp_progress(line) is not None`, which is a **different function** added later (`_is_ytdlp_progress_line` arrived with `7d02a30`, after the report was written). Any fix that reasons from the source report's predicate will reason about the wrong branch.

**Exact semantic scope.**

- `services/ytdlp_downloader.py::_echo_ytdlp_line` — the transform is applied to what reaches `sys.stderr`. Both write branches are in scope: the progress branch's `text` and the non-progress branch's `line`.
- `services/ytdlp_downloader.py::_download_with_ytdlp` — the two call sites inside `_monitor_progress` and `_drain_output` pass the **raw decoded line** for two different purposes: the echo and the `output_chunks` buffer. **The buffer must stay raw** — `B6`/`plan 10` transform it downstream, and a double transform here would break the readability the buffer exists for. Only the value handed to `_echo_ytdlp_line` changes.
- `services/ytdlp_downloader.py::_echo_ytdlp_line`'s docstring — it currently describes no transform; it will.

**Files.** `src/vkdownloader/services/ytdlp_downloader.py`, `tests/test_hls_downloader.py`. **No new file.**

**The three clauses that must survive — re-examined against the Product Owner's ruling, because one of them has changed direction.**

The Product Owner has ruled that **non-progress child output becomes one log record per line, with stderr kept clean.** That is plan 13's `OUT-007`. It is **closer to the new ruling than to the clause this plan originally pinned**, so the clause is corrected here rather than left as a contradiction for an Implementor to trip over.

| Clause | Earlier draft pinned | Status now | Reason |
|---|---|---|---|
| The `\r`-rewrite for progress lines | live, non-weakened | **stands** | Nothing in the ruling touches progress rendering. |
| `echo=False` on a **progress** line emits exactly one DEBUG `ytdlp_progress_suppressed` record carrying `downloaded`/`total` | live, non-weakened | **stands, with a caveat** | The ruling replaces **stderr** output with **log records**. The DEBUG record is already a log record, so it is compatible — but see the caveat below. |
| `echo=False` on a **non-progress** line writes nothing **and emits no record** | live, non-weakened | **WITHDRAWN — replaced** | **Directly contradicted by the ruling.** The new behaviour is one log record per line; "emits no record" is now the opposite of what is wanted. |

**Declared test change, with its reason.** `B5` **changes one existing test**: the test asserting that `echo=False` on a non-progress line "writes nothing and emits no debug log" must be **rewritten**, not deleted and not relaxed. Its new form asserts the owner's ruling: with stderr clean, the non-progress line is emitted as **one log record**. This is a deliberate, owner-directed behaviour change, not a test weakened to let a block land. **The other clauses in that test — that stderr receives nothing — remain asserted**, because "stderr clean" is half of the ruling and is the half `B5` must not break.

**Sequencing consequence, and it is a real one.** `B5` now implements **part of** plan 13's ruling rather than only the redaction. That means `B5` and plan 13 touch the same function. **Recommendation: `B5` lands the redaction only, and plan 13 lands the record-per-line change** — because the record-per-line change is a *product behaviour* decision with its own documentation and its own review, and folding it into a security block would make neither reviewable. If plan 13's `OUT-007` lands **first**, `B5` must be written against the new shape and its redaction must be applied to the **record's field**, not to the stderr write. **Check which before starting.**

**`D-6` — whether the transform runs before or after the progress predicate.** Unchanged by the ruling and still resolved with the same reason, because the progress callback's arithmetic does not move:

- **Alt A: transform the line first, then classify and write.** One transform, both branches inherit it. **Hazard:** `_parse_ytdlp_progress` reads `pct` and `size` out of the line, and a rule that touched those characters would compute the callback's `downloaded`/`total` from redacted text.
- **Alt B (default): classify and parse on the raw line, transform only what is written or logged.** The predicate must see the **raw** line, so **Alt B is the resolution** — recorded with its reason, not deferred. The Implementor must still verify it with a test that the transform never runs before the parser sees the line; `test_ytdlp_echo_false_progress_emits_debug_log`'s `downloaded`/`total` assertions are the natural place.

**`D-10` — what `B5` redacts, once the ruling is in force.** New, and dependent on the sequencing above:

- **If the ruling has not landed (default):** `B5` applies the transform to what reaches `sys.stderr`, exactly as scoped. `sanitize_text_for_log` is imported and called at the echo.
- **If the ruling has landed:** there is no stderr write for a non-progress line to sanitise. `B5` applies the transform to the **value handed to the log call** instead. The idempotency requirement then interacts with `B6`'s pipeline processor (§3.6), because the record would be sanitised at the call site *and* on the pipeline. That interaction is already covered by `B6`'s existing idempotency criterion — **this is exactly the case it was written for.**

**Alternatives at the sink itself.**

- **Alt A′ (default): transform inside `_echo_ytdlp_line`.** One place, and it is the function whose entire job is "what reaches the console".
- **Alt B′: transform at the two call sites.** Rejected — duplicates the rule at two sites and can drift.
- **Alt C′: stop echoing child output entirely.** **Superseded by the ruling** — the ruling already moves non-progress output off stderr. `C′` is no longer a decision to make.
- **Alt D′: redact only at the log-pipeline level and leave the console alone.** Rejected — that leaves the operator's terminal with the signed URL, which is the finding.

**Acceptance criteria.**

1. A non-progress line carrying a signed CDN URL reaches `sys.stderr` **redacted** (or, if the ruling has already landed, is emitted as a log record with the URL **redacted** in its field). This is the block's core assertion and it has no test today.
2. The existing assertion that a benign non-progress line passes through **unchanged** stays green. A new sibling case asserts the redacting half. **The existing case is not weakened.**
3. A progress line's `\r` rewrite and terminal-width padding are unchanged, and `downloaded`/`total` still come from the **raw** line (`D-6`).
4. **`echo=False` writes nothing to stderr** — no partial line, no flush. **This clause stands** and is half of the owner's ruling.
5. **The rewritten non-progress test asserts the ruling:** with stderr clean, the line is emitted as **one log record**. This is the one existing expectation `B5` changes, declared here with its reason (§the clause table above). It is a rewrite, not a deletion and not a relaxation.
6. The `echo` gate is evaluated **before** any transform, so `echo=False` never leaks through a transform side effect.
7. If `D-10` resolved to the record-field variant, `B5`'s redaction composes with `B6`'s pipeline processor without double-application — evidenced by `B6`'s idempotency test, which `B5` must not weaken.
8. The docstring states that what reaches the console is the transformed line, and that the buffer downstream receives the raw one.
9. `tests/test_hls_downloader.py` is **already red on `ruff format --check` at baseline** (§2.1). `B5` opens that file and must either reformat it or state that the pre-existing red was left untouched.

**Collision.** Plan 10 `B2` and `B6` both rewrite the drain loop this block's call sites live in (§4.3).

**Required agents:** **Auditor** (re-derive the full set of `_echo_ytdlp_line` call sites and every caller that sets `echo` — an undiscovered `echo=True` in another code path changes the block's blast radius), **Validator** (the three pinned clauses are exactly the kind of behaviour an over-eager redaction silently breaks, and the live tests are the only thing standing between this block and a broken console). **Researcher and Planner not required** — the design is settled by `D-6`'s reason; no external platform or library behaviour is in question.

**Commit:** `fix(download): redact child output before it reaches the console`

---

### 3.6 `B6` — Put one redaction transform on the log pipeline so every exception-text record is covered, including the ones a call site cannot reach

**Findings carried:** `SEC-007` — **HIGH** · `SPEC-DEVIATION** · mandatory.

**Goal.** Caught-exception text and `exc_info` reach the log untransformed across **18 records**, re-counted and re-verified against the current tree. The count was 16 at this plan's original baseline and has **risen by two**, both added by the landed loader-removal commits:

| File | Record | Carrier |
|---|---|---|
| `infrastructure/browser.py` | `browser_launch_failed` | `exc_info=True` |
| `infrastructure/browser.py` | `browser_close_failed` | `error=str(exc)` **and** `exc_info=True` |
| `infrastructure/browser.py` | `playwright_stop_failed` | `error=str(exc)` **and** `exc_info=True` |
| `cli.py` | `download_failed` | `logger.exception` |
| `cli.py` | `batch_download_failed` | `logger.exception` |
| `services/batch_downloader.py` | `unexpected_error_in_batch_download` | `logger.exception` |
| `services/extractor.py` | `ytdlp_extraction_error` | `error=str(e)` |
| `services/extractor.py` | `failed_to_capture_cookies` | `error=str(e)` (DEBUG) |
| `services/extractor.py` | `video_player_click_failed` | `exc_info=True` (DEBUG) |
| `services/ytdlp_downloader.py` | **`subprocess_reader_failed`** | `error=str(exc)` — **new** |
| `services/ytdlp_downloader.py` | **`cookie_file_cleanup_failed`** | `path=str(cookie_file)` **and** `error=str(exc)` — **new** |
| `services/ytdlp_downloader.py` | `failed_to_refresh_token` | `error=str(e)` |
| `services/ytdlp_downloader.py` | `invalid_quality_for_browser_streams` | `error=str(e)` |
| `services/ytdlp_downloader.py` | `yt_dlp_not_found` | `exc_info=True` |
| `services/downloader_throttle.py` | `segment_download_error` | `error=str(e)` |
| `services/ffmpeg_utils.py` | `merge_space_probe_failed` | `error=str(exc)` |
| `services/segment_downloader.py` | `segment_download_error` | `error=str(e)` |
| `services/segment_downloader.py` | `playlist_fetch_failed` | `error=str(e)` |

> **The count has moved twice in this project's history** — 11 in the source report, 14 after validation, 16 at this plan's original baseline, **18 now**. That is not noise; it is the direct consequence of the central-processor design below being necessary in the first place: a call-site enumeration is a snapshot, a processor is not. **`B6`'s enumeration must be re-verified at execution time, and a count that differs from 18 is an `Auditor` finding that changes the closure claim — not an implementer's discretion.**

**The two new records matter disproportionately.** `cookie_file_cleanup_failed` carries `path=str(cookie_file)` — the credential artefact's own path — **and** `error=str(exc)`. It is simultaneously this finding and `SEC-006`'s, and it was introduced *after* both findings were filed. It is the clearest possible evidence that both findings describe live behaviour and not a historical shape.

**The count is 18 and the decisive structural fact decides the remedy.** `format_exc_info` **is** in the processor chain, so any `exc_info=True` or `logger.exception` renders a full traceback into the record — and there is **currently no central transform anywhere on that chain**. **Five** of the eighteen records carry a traceback that a call-site edit cannot touch: `exc_info` takes an exception or traceback object, not text, so there is no text to wrap at the call site. **A call-site-only remedy is structurally incapable of closing this finding.**

**The remedy.** One processor on the structlog chain, positioned **after `format_exc_info`** (so the rendered traceback string exists to transform) and **before the renderer**. It then covers all eighteen records — and every future one — without touching any call site.

**Priority, stated because Decision A raised it.** With the ffmpeg loader gone, `SEC-006` and `SEC-007` are **the whole of the remaining leak surface** (§1.4.2). There is no second transport carrying child output and no second class of artefact on disk. This block changes the rendering of **every** log record in the product, which is exactly why it carries the highest implementation risk in this plan — and it is worth that risk, because it is now the only central control the product has.

**Alternatives, with the reason each loses.**

- **Alt A (default): central processor after `format_exc_info`.** Covers all 16 including the six `exc_info` records; survives future call sites; **no edit to any of the 16 sites**.
- **Alt B: wrap `error=str(e)` at all 16 sites.** **Rejected — structurally incomplete.** It cannot reach the six traceback records, so the finding would be reported closed with the largest leak still open. This is the decisive argument.
- **Alt C: central processor *plus* per-site wrapping.** Rejected — the per-site wrapping is redundant once the processor exists, and it means two transforms in the path (which must then be idempotent; see `B4`).
- **Alt D: a stdlib `logging.Filter`.** Rejected — structlog bypasses handler-level filters for its own rendering; the filter would not see the event dict at the right point in the chain.

**Where the processor lives — a file decision.**

- **Default: extend `utils/url_sanitizer.py`.** The module's stated purpose is already "URL sanitization utilities for **secure logging**", and a redaction processor for log records is the same concern. **No new file, therefore no `tests/test_packaging.py` frozenset edit** (§2.3.2).
- **Alternative: a new `utils/log_redaction.py`.** Cleaner separation of concerns (house rules 3 and 4 favour it), but it adds a file under `src/` and therefore a frozenset edit in the same commit, and it splits one redaction policy across two modules. **Criterion:** prefer the existing module unless the Implementor finds the mixed responsibility genuinely hard to state in one docstring. If the new module is chosen, the frozenset edit is **mandatory in the same commit** and `utils/__init__.py`'s `__all__` is the decision point for what is public.

**`config.setup_logging` — the layer constraint and the collision.** `config.py` is entry-adjacent and today imports **only** from `vkdownloader.models.enums`; it has **zero** `logger.` calls. This block adds its first `utils` import. The layer rule forbids the entry layer from importing **private** symbols, so the processor must be reachable under a **public** name — either exported from `utils/__init__.py` or imported from the module path as a public symbol. Importing `_strip_auth_params`-style private names from `config.py` would break the layer rule. **This is also the file plan 12's `ART-007` writes** — see §4.2 and §4.3.

**`D-7` — the processor's scope: key allowlist vs. every string value.** Genuinely undecided, because it depends on `D-5`.

- **If `B4` landed as `D-5` Alt A (narrow artefact patterns):** the rules match almost nothing, so transforming **every string value** in the event dict is both safe and complete. **Default in this case.**
- **If `B4` landed as `D-5` Alt B (header-value rule added):** an all-strings transform risks over-redacting benign fields. Use a **key allowlist** — the keys observed above (`error`, `exception`, and the rendered-traceback key `format_exc_info` produces) — and **record the residual explicitly**: a future record using a novel text-bearing key would be unsanitised.

**Criterion:** resolve `D-7` *after* `B4` has landed and its rule set is final, by asking whether the rule set can match a field the product logs for benign purposes. Do not decide this in advance. Whichever way it resolves, the block states in its commit message which scope it chose and what residual remains.

**Idempotency — inherited from `B4` and re-asserted here.** After `B5` lands, a record's field may already be sanitised at the call site. The processor must not double-apply. `B4`'s idempotency acceptance criterion is the shared proof; `B6` adds a test that asserts a record which passed through a sanitising call site and then through the processor is identical to one that passed only through the processor.

**Records explicitly NOT in scope.**

- `network_monitor`'s exception sites log `str(e.__class__.__name__)` only — already correct, four sites, not findings.
- `batch_merge_failed` / `final_merge_failed` — **assigned to plan 10 `B14`.** Not re-claimed here. **Correction to an earlier draft of this plan:** these are **permanent product surface** under Decision A, not casualties of the loader removal — they belong to `_merge_batch_segments` and `_perform_final_merge`, the two stages of the only merge path the product has. They stay, and `B6` still does not touch them.
- Any `src/` file outside the eighteen. Adding one would mean the enumeration was wrong; that is an `Auditor` acceptance item, not an implementer's discretion.

**Decision B constraint on this block.** §2.3 records the four-code exit contract: `3` for configuration error, `1` download-failure-only, `2` usage error, `4`+ unallocated, implemented by plan 13. Two of the eighteen records are `cli.py`'s `download_failed` and `batch_download_failed`, and `cli.py` currently raises `typer.Exit(code=1)` for both a download failure **and** a `_PreambleFailure` configuration error. Plan 13's re-coding will therefore change which event name a configuration failure produces. **Binding on `B6`: the processor must be key-agnostic and event-name-agnostic — it must not special-case `download_failed`, must not branch on an event name, and must not assume any record's meaning is fixed.** It transforms values; it does not interpret records. This plan produces no status code and documents no exit-code table.

**Acceptance criteria.**

1. Each of the eighteen records, when rendered through the **configured** pipeline, contains no untransformed signed URL and no untransformed artefact path. A test drives the configured chain (not a hand-built event dict) with a redaction-worthy value in the field each record uses.
2. At least one test covers a record carrying **`exc_info=True`** and asserts the **rendered traceback** is redacted. This is the criterion that distinguishes this block from a rejected `Alt B`.
3. `cookie_file_cleanup_failed` is covered for **both** of its text fields — `path` and `error` — because it is the one record that carries an artefact path verbatim.
4. Both `logger.exception` sites in `cli.py` are covered **without any edit to `cli.py`.** If an Implementor finds it necessary to edit `cli.py`, that is a finding-level design failure and must be escalated, not absorbed.
5. The processor is **event-name-agnostic**: a test asserts it transforms a value regardless of the event name, with no branch on `download_failed` or any other name. This is the Decision B constraint (§2.3.11) made observable.
6. `config.setup_logging`'s existing log-file creation branch (`touch(mode=0o600)` / `chmod(0o600)`) and the `SEC-003:` comment above it are **untouched** — `B3` owns that comment.
7. The processor's position in the chain is asserted by a test, so a future reordering that moves it before `format_exc_info` fails.
8. Idempotency against a pre-sanitised call site (see above), including the `D-10` record-field case if `B5` lands after the ruling.
9. `D-7`'s scope choice and its residual are recorded in the commit message.
10. `uv run mypy src` clean; `ruff check` clean; full suite green with the skip count **not above 3**.

**Required agents:** **all four.** **Auditor** (the 16-record enumeration is load-bearing for the finding's closure claim and the count itself was wrong twice in this project's history); **Researcher** (structlog processor-chain semantics — specifically what a processor may and may not mutate in the event dict, and where `format_exc_info` places its output — must be settled against authoritative documentation, not from memory); **Planner** (processor placement, `D-7`'s conditional resolution, the module-placement decision, and the idempotency interaction with `B5` all interact); **Validator** (highest-risk block in the plan: it changes the rendering of **every** log record in the product, and a mistake there degrades every failure investigation in the product at once).

**Commit:** `fix(logging): redact secret-shaped text on the log pipeline`

---

### 3.7 `B7` — Mark the two in-process session carriers so their contents are not rendered in the clear

**Findings carried:** `SEC-008` — **MEDIUM** · **BEST-PRACTICE** · advisory.

**Goal.** Two carriers hold live session material and declare nothing sensitive, so both render in full: `HLSDownloadRequest.cookies: str | None` is a plain `str` on a plain `BaseModel` with **no field markers at all**, and `DownloadPolicy.headers: dict[str, str]` is a `@dataclass` field with no `repr=False`. Repo-wide, `SecretStr` / `repr=False` / `model_dump` occur **zero** times.

**Exact semantic scope.**

- `models/dtos.py::HLSDownloadRequest.cookies` — the type becomes a secret-bearing type, and the value's consumers unwrap it explicitly.
- `services/segment_downloader.py::DownloadPolicy.headers` — the dataclass field stops appearing in `repr`.
- Every construction site of `HLSDownloadRequest` (**two** in `src/`: `downloader.py` and `ytdlp_downloader.py::_attempt_segment_resume`) and of `DownloadPolicy` (**one**).
- The one consumer that reads the carrier's value: the `headers` dict is populated from the request, and `headers["Cookie"] = request.cookies` must unwrap.

**Files.** `src/vkdownloader/models/dtos.py`, `src/vkdownloader/services/segment_downloader.py`, plus the construction sites in `services/ytdlp_downloader.py` and `services/downloader.py`. **No new file.**

**`D-8` — how each carrier is marked.** Two different mechanisms, because the two carriers are two different kinds of object.

- **`HLSDownloadRequest.cookies`: `SecretStr` (default).** Pydantic-native, and it renders as `**********` in `repr`/`str` **and** requires an explicit `.get_secret_value()` at the consumer — so forgetting to unwrap is a type error, not a silent leak. Cost: `segment_downloader.py`'s `if request.cookies:` truthiness test changes shape and the unwrap becomes mandatory.
  - **Alternative: `Field(repr=False)`.** Weaker — it hides the field from `repr` but leaves the value a plain `str`, so `request.cookies` still hands the raw secret to any code that asks. **Rejected** for the Pydantic carrier where `SecretStr` is available.
- **`DownloadPolicy.headers`: `field(repr=False)` (default).** A `dict` cannot be a `SecretStr`. `field(repr=False)` removes it from the generated `repr` and costs nothing. **Alternative: a custom `__repr__`** that prints a header **count** instead of nothing — marginally more useful for triage. Default to `field(repr=False)` (simpler, house rule 5); the count variant is acceptable if stated.

**Acceptance criteria.**

1. `repr()` of an `HLSDownloadRequest` carrying cookies contains **no** cookie value. A test asserts this directly.
2. `repr()` of a `DownloadPolicy` carrying a `Cookie` header contains **no** header value. A test asserts this directly.
3. The segment-download path still functions: the value reaches the outgoing request headers unchanged. A test drives the existing segment path (or its narrowest available seam) and asserts the `Cookie` header is sent.
4. `_attempt_segment_resume`'s second construction site is updated in the same commit and its refresh path still works.
5. `uv run mypy src` clean — and note §2.3's `ignore_missing_imports = true` caveat: verify `SecretStr` resolves against the declared `pydantic` dependency by inspection, because mypy will not catch a missing declaration.
6. No `Any` introduced; the unwrap is a typed call.

**Advisory-status note.** This block is **advisory**, cheap, and self-contained, but it **touches `segment_downloader.py`, a file `B8` and plan 10 also claim.** Because the finding is advisory and the risk is a type-shape change on the download path, it runs on its own lane (§4.2) and **must not** be bundled into a mandatory block.

**Required agents:** **Auditor** (the construction-site and consumer enumeration is the whole risk here — a missed site is a `TypeError` at runtime, and the measured counts are 2 / 1 / 1), **Validator** (the segment path is the product's primary download path; a wrong unwrap breaks authenticated downloads outright). **Researcher and Planner not required** — `SecretStr` and `field(repr=False)` are settled Pydantic/dataclasses mechanisms.

**Commit:** `fix(models): mark the session carriers so they do not render their contents`

---

### 3.8 `B8` — Settle the browser-context cookie harvest as a recorded decision, not as a silent whole-store copy

**Findings carried:** `SEC-010` — **MEDIUM** · BEST-PRACTICE · **advisory**.

**Goal.** `_extract_with_browser` calls `page.context.cookies()` with **no argument** — an unfiltered whole-store harvest — and the stated reason names no dependency. The composition that turns those cookies into a flat `"; ".join` header **drops the domain**, so scoping cannot be expressed there at all.

**The bounding fact that decides how small this block must be.** `BrowserManager.create_stealth_page` calls `new_context(viewport=…, user_agent=…, locale=…, timezone_id=…)`. There is **no `storage_state`, no `launch_persistent_context`, and no `user_data_dir` anywhere in the tree**. The context is created fresh and discarded at the end of the run, so the store being harvested holds only what this run's own page visit produced. **The exposure is bounded, which is why this is advisory rather than mandatory** — and why a speculative narrowing would be a redesign rather than a fix.

**`D-9` — the decision, deliberately left open.**

- **Alt A (default): document the dependency precisely at the harvest site and pin the current composition with a test.** No behaviour change. The harvest's reason is stated in the docstring — "the context is ephemeral, the page visit needs whatever the origin set, and filtering by domain is not expressible in the flat header this composes" — and a test pins the composition contract so a future change to it is deliberate.
- **Alt B: narrow the flat `Cookie:` header to cookies whose domain suffix-matches the request host.** Scoped forwarding is defensible — a cookie scoped to an unrelated domain is definitionally not for the CDN — and it is the one row where scoping is currently impossible. **But it is a runtime behaviour change on the authenticated download path, it cannot be validated on the declared platform** (no live origin is available — the store's own skip S-6), and a wrong narrowing breaks authenticated downloads with no local signal. **Not the default.**
- **Alt C: request a domain filter from Playwright** at the harvest call. **Rejected** — changes what is harvested for every downstream consumer at once, on the same unvalidatable platform.

**Criterion for choosing `B` over `A`:** an owner statement of which cookie domains the CDN actually requires, **or** a live-origin observation. Absent one of those, `A` is the honest resolution: it closes the finding the way the store itself says it can be closed ("stating the dependency is a legitimate answer to this finding") and it leaves the operator with a written reason instead of an unexplained whole-store copy.

**Exact semantic scope.**

- `services/extractor.py::VKVideoExtractor._extract_with_browser` — the harvest call site: docstring and/or an inline comment carrying the recorded reason. **No change to the call.**
- `services/extractor.py::VKVideoExtractor._format_cookies_for_ffmpeg` — its docstring already says "Includes all cookies to ensure proper CDN authentication"; under `Alt A` that sentence becomes the **recorded dependency**, cited. **The method's name references the retired loader transport and is now a misnomer** — but renaming it is a separate concern from this finding, it touches a symbol three other plans claim (§4.3), and **this block must not rename it.** Record the misnomer here; let the owner schedule the rename with the scope it deserves.
- `tests/test_extractor.py` — a test pinning the composition contract under `Alt A`.

**Files.** `src/vkdownloader/services/extractor.py`, `tests/test_extractor.py`. **No new file.**

**Note on Decision A.** This finding's subject is untouched by the loader removal — `extractor.py` is the extraction layer, and the harvest feeds the yt-dlp cookie file, which is exactly the artefact `B2` confines. Decision A does not change this block's substance. It does change one thing: with the loader gone, the *only* consumer of the flat `Cookie:` header composition is the segment path, which is permanent. So the harvest's scope decision is now permanent rather than provisional, which raises the cost of getting `D-9` wrong and is a further reason the default is `A` — document, do not narrow on an unvalidatable platform.

**Acceptance criteria.**

1. The harvest site carries a written reason that names **what the cookies are for**, in terms a reader can act on.
2. Under `Alt A`: no behaviour change; a test pins the composition so an accidental change fails.
3. Under `Alt B` (only if `D-9` resolves to it): the narrowed set is expressed in a test that demonstrates both what is kept and what is dropped, and the commit message states that this is an unvalidated-on-platform behaviour change.
4. Either way, the commit message records which of `Alt A` / `Alt B` was chosen and the criterion that decided it.
5. `uv run mypy src` clean; `ruff check` and `ruff format --check` clean; `tests/test_extractor.py` green.

**Required agents:** **Auditor** (confirm the bounding fact still holds at execution time — if `storage_state` / `user_data_dir` / `launch_persistent_context` has appeared anywhere in the tree since this baseline, the exposure is no longer bounded and this block's priority and default both change), **Researcher** (only if `Alt B` is chosen: Playwright's cookie-filter semantics and what a same-site/third-party split would mean for CDN authentication). **Planner and Validator not required** under `Alt A` — a comment plus a pinning test is not architecturally risky. **Validator IS required under `Alt B`.**

**Commit:** `docs(extractor): record why the browser cookie harvest is not filtered`

---

### 3.9 `B9` — Add the missing severity row for a finding that passes verification

**Findings carried:** `VAL-601` — **MEDIUM** · SPEC-DEVIATION · mandatory.

**Goal.** The validate phase's severity table has **four** rows — CRITICAL, HIGH, MEDIUM, LOW — and **no row for a finding that passes verification**. The consequence is not theoretical: this very phase moved `SEC-001` HIGH→MEDIUM, `SEC-002` HIGH→MEDIUM and `SEC-007` MEDIUM→HIGH, on an unsourced rule, because the table gave it nowhere to put a validated finding. The document separately states that a decision never changes the severity column, and that `Validated` keeps the finding as-is — so the table and the decision rule point at each other and neither closes the gap.

**Exact semantic scope.**

- `.kilo/commands/audit/phases/99-audit-validate.md` — the severity table in the severity-taxonomy section gains a **fifth row** covering a finding whose verification passed and whose decision is `validated`. The row must state what the severity is in that case, and it must be consistent with the existing decision-application rule that `Validated` keeps the severity as-is.
- The surrounding prose, if the fifth row makes any existing sentence inaccurate.

**Files.** `.kilo/commands/audit/phases/99-audit-validate.md`. Nothing else. **No source, no test.**

**Design constraint.** The row must not contradict the section's own load-bearing sentences: the four severity words are not redefined here, the template is the authority for their meaning, and a decision never changes the severity column. The row's job is to say **what band a validated finding carries and where that band comes from** — not to invent a fifth severity word. Adding a fifth *word* is prohibited; adding a fifth *row* is the fix.

**Alternatives.**

- **Alt A (default): add the row.** Direct, minimal, matches the finding.
- **Alt B: amend the `Validated` decision-application row instead.** Rejected — the decision-application table lives in a different section and describes an action, not a band. The gap is in the severity table.
- **Alt C: leave the table and add a sentence elsewhere.** Rejected — a sentence in prose is exactly what produced the unsourced severity moves this finding is about.

**Acceptance criteria.**

1. The table has a row for a validated finding, and the row states both the band and its source.
2. Read against the section's other sentences, the row is consistent: it does not redefine a severity word, and it does not make a decision change a severity.
3. The document still contains no fifth severity **word**.
4. An `Auditor`/`Validator` reader can answer "what severity does a validated finding carry?" from the table alone.

**Required agents:** **Validator** required — this is a pipeline-conformance document whose whole purpose is to be followed literally under pressure, and a fifth row that reads ambiguously is worse than the gap. **Auditor** required for the same reason in reverse: confirm no **other** validate-phase section (a sibling phase file under the same directory) repeats the four-row table, because a fix applied to one file and not its siblings leaves the corpus inconsistent. **Planner, Researcher not required.**

**Commit:** `docs(audit): add the severity row for a finding that passes verification`

---

### 3.10 `B10` — Make the findings template stop supplying a pre-answered summary

**Findings carried:** `VAL-603` — **LOW** · DOC-UPDATE · advisory.

**Goal.** `.ai/audit/templates/audit-findings.md` ships a `## Summary` section whose table is **hard-coded to zeros** (`CRITICAL | 0`, `HIGH | 0`, `MEDIUM | 0`, `LOW | 0`) followed by three placeholder action lists (`## Mandatory Fixes`, `## Advisory Recommendations`, `## Doc Updates Needed`), each containing a single fill-in instruction. The template therefore supplies an **answer before the audit runs**. All **eleven** `99-validation/*.md` artifacts delete all four sections — which is itself the measured proof that every executor reads the template and then removes these parts, i.e. the template is wrong for all eleven known uses.

**Exact semantic scope.**

- `.ai/audit/templates/audit-findings.md` — the `## Summary` table and the three placeholder action lists. Either made fillable (instructions that say what to compute, not a pre-filled number) or removed, and the choice stated.
- Any cross-reference elsewhere in the template that promises those sections exist.

**Files.** `.ai/audit/templates/audit-findings.md`. **This is the only block in this plan permitted to touch a path under `.ai/audit/`.**

**Staging prohibition, absolute.** This block stages **exactly one path**: `.ai/audit/templates/audit-findings.md`, a tracked template. It must **never** stage anything under `.ai/audit/99-validation/**` or any other validated artifact. The validation corpus is evidence; editing it is never in scope for a fix block.

**Note on the template's current shape.** The template already carries a `Decision` field per finding and a `verification` field per finding (the `validated | reclassified | merged | rejected` row and the `observed | unverified` row). Those were added by an earlier plan and are **out of scope here**. `VAL-603` concerns only the tail.

**Alternatives.**

- **Alt A (default): make the summary fillable** — keep the four sections, replace the zero rows with a tally an executor fills and a one-line instruction on what to count. Preserves the template's shape.
- **Alt B: delete the four sections** and require the tally to live in the validation summary that the validate phase already mandates. Matches what all eleven executors actually do.
- **Alt C: keep them as optional.** Rejected — an optional section that is always deleted is the same defect with extra words.

**Criterion:** prefer `B`. The eleven-artifact measurement is direct evidence that the sections are not used, and a template that matches practice is one fewer thing every executor has to fight. Choose `A` only if the validate phase genuinely requires a per-phase tally that the validation summary does not already carry — **check `.kilo/commands/audit/phases/99-audit-validate.md`'s decision-tally requirement before choosing.**

**Acceptance criteria.**

1. No pre-filled count appears anywhere in the template.
2. Each of the four sections is either genuinely fillable (with an instruction that says what to compute) or removed — and the commit message states which, per section.
3. No cross-reference in the template points at a removed section.
4. `git status` after the commit shows no path under `.ai/audit/99-validation/` touched.
5. The template's `## Findings` block and the field-reference table are unchanged except for cross-references required by (3).

**Required agents:** **Auditor** (confirm the eleven-artifact measurement still holds — a twelfth artifact that *keeps* the sections would falsify the evidence the choice rests on). **Validator, Planner, Researcher not required** — lowest-risk block in the plan, and advisory.

**Commit:** `docs(audit): stop the findings template pre-answering its own summary`

---

## 4. Dependency graph, linearised order, and conflicts

### 4.1 The graph

```
        B1  SEC-009  serialiser ─────────────────────────────┐  (independent)
                                                             │
        B2  SEC-001+002+VAL-602  artefact lifecycle          │  (independent of B4)
        │        │                                            │
        │        └──► B3  SEC-003  oracles  ◄────────┐       │
        │                              │             │       │
        B4  SEC-006  transform  ◄──────┤             │       │
        │      │                           │             │       │
        │      ├──► B5  SEC-005  echo      │             │       │
        │      └──► B6  SEC-007  pipeline ─┴─────────────┘       │
        │                    │                                     │
        B7  SEC-008  carriers (independent)                      │
        B8  SEC-010  harvest  (independent)                      │
        B9  VAL-601  severity row (independent)                  │
        B10 VAL-603  template    (independent) ──────────────────┘
```

**Edges, each with its reason.**

| Edge | Reason |
|---|---|
| `B4 → B5` | `B5`'s job is to route child bytes through the transform at the console. If `B5` lands first, it redacts URLs only and the sink and the log disagree — which is the defect `B4` exists to remove. Landing `B4` first makes the console sink and the log sink the *same* transform, which is the whole point. |
| `B4 → B6` | `B6`'s processor is the same transform, applied on the pipeline. It must use `B4`'s final rule set, or the two redaction surfaces diverge and the finding is only half-closed. |
| `B4 → B6 → B3` | **File lock, not logic.** `B6` rewires `config.setup_logging`'s `structlog.configure` call; `B3` edits the `SEC-003:` comment directly above the same function's log-file branch and rewrites the two log-file oracles that call it. One writer at a time on that function. `B3` goes **second** so its comment is written against the final shape of the function. |
| `B2 → B3` | **Split into two edges after re-baselining.** The *artefact* oracle in `B3` asserts a property `B2` introduces and cannot land before it. The two *log-file* oracles are independent of `B2` and **may land first**. So `B3` is no longer a single-position block: its log-file half is unblocked now, its artefact half waits on `B2`. `SEC-003`'s own text says the recommended form is anchored to `SEC-001`'s design — that anchoring binds the artefact oracle, not the log-file ones. |
| `B2 → B5` | **File lock.** Both edit `services/ytdlp_downloader.py`; `B2` rewrites `_create_temp_cookie_file` and the `finally:`, `B5` rewrites `_echo_ytdlp_line` and the two drain-loop call sites. |
| ~~`B3 → removal track`~~ | **REMOVED — satisfied.** `B3` no longer waits on the removal track: `_temp_argfile` and its oracle were deleted by an already-landed commit, so `B3` is **UNBLOCKED**. |
| `B1, B7, B8, B9, B10 → nothing` | Five independent blocks. No edge in either direction. |

**No cycles.** `B4` is the only genuine hub; `B2` is the other.

### 4.2 Linearised order, and why each block sits where it does

**Serialised critical path (one writer at a time on every shared file):**

> **`B1` → `B2` → `B4` → `B5` → `B6` → `B3`**

| # | Block | Why here |
|---|---|---|
| 1 | **`B1`** | The only finding filed `observed` with a **live end-to-end reproduction of a correctness failure**, and the only one-line fix in the plan. It is independent of everything, so nothing is gained by delaying it, and a live data-loss defect should not sit behind four blocks. |
| 2 | **`B2`** | The largest and highest-risk product block. It goes early because it is the only block whose acceptance criteria other blocks *assert against* (`B3` depends on it), and because it is the one block a reviewer should look at with the most time remaining. It precedes `B5` by file lock. |
| 3 | **`B4`** | The capability block. Must precede both of its consumers (`B5`, `B6`). It is a pure-function change plus tests — no wiring — so landing it third means the two wiring blocks that follow are each reviewing one idea. |
| 4 | **`B5`** | Before `B6`, and the reason is concrete rather than conventional: `B6`'s processor sees records whose fields may already have been sanitised at a call site. `B5` creates exactly one such call site (`_echo_ytdlp_line`), so `B6` must land after it in order to design and prove idempotency against a **real** pre-sanitised record rather than a hypothetical one. `B5` is also the smaller of the two, so this position keeps the highest-surface-area block last among the redaction work. |
| 5 | **`B6`** | The highest-risk block in the plan — it changes the rendering of every log record in the product. Placing it after `B4` (rule set final) and after `B5` (pre-sanitised call site exists) means both of its open design questions have real answers at design time. |
| 6 | **`B3`** | **Unblocked; now two positions.** The **two log-file oracles** are independent of every other block and may land at any point — they need only `config.setup_logging`'s current shape and `D-4` resolved. The **artefact oracle** waits on `B2`, because it asserts a property `B2` introduces. Both halves must still be written against the final shape of plan 12's `ART-007` (see the external constraints below). The earlier "last, and waits for the removal track" position is **withdrawn** — that wait is already satisfied by a landed commit. |

**Parallel lanes — these five may run at any point in the sequence, concurrently with anything, because they share no file with any other block in this plan:**

| Block | Why it is genuinely parallel |
|---|---|
| `B7` | Owns `models/dtos.py`, `services/segment_downloader.py` (dataclass field only), and two construction sites in other blocks' files. Advisory and independent. |
| `B8` | Owns `services/extractor.py` only. |
| `B9` | Owns one pipeline document. No source, no test. |
| `B10` | Owns one template. No source, no test. |

**`B7`'s one caveat.** Its construction sites land in `services/ytdlp_downloader.py` and `services/downloader.py` — files `B2`/`B5` also edit. It is parallel in the graph but must **stage after** them if it would otherwise conflict, or be sequenced so the two never share a hunk. Each `B2`/`B5` commit touches `ytdlp_downloader.py`; a `B7` commit touching a different function in the same file is fine to serialise anywhere, but it must not be merged into a `B2` or `B5` commit (§2.5).

**Ordering constraints coming from outside this plan:**

1. ~~**`B3` waits for the removal track** to delete `downloader._temp_argfile`.~~ **SATISFIED — removed as a constraint.** The loader removal has landed (`d572d96` and follow-ups); `_temp_argfile`, `HLSDownloader`, `_format_argfile`, `FfmpegProgress`, `ProgressParser`, `read_progress`, `_PROGRESS_KEY_HANDLERS` and `DownloadMethod.FFMPEG` are gone from the tree, and `test_temp_argfile_permissions_are_0600` went with them. **`B3` no longer waits on anything for that reason.** What survives as a wait is only its *artefact* oracle's dependency on `B2` (§4.1).
2. **`B6` and `B3` serialise with plan 12's `ART-007` on `config.py::setup_logging`** — recorded in §4.3. **`B3`'s two log-file oracles are the ones exposed**; if `ART-007` has not landed, `B3`'s log-file half waits for it, because an oracle written against a branch `ART-007` is about to change is worse than a late oracle.
3. **`B5` and `B6` serialise with plan 10's `B2` and `B6` on the drain loop** — recorded in §4.3.
4. **`B5` overlaps plan 13's `OUT-007`** (non-progress output becomes one log record per line, stderr clean). **Not a lock — a content conflict.** See §3.5's sequencing recommendation: `B5` should land the redaction only and let plan 13 own the record-per-line change, unless plan 13 lands first, in which case `B5` must be re-scoped per `D-10`.
5. **Plan 13 also owns the exit-code contract** (`3` for configuration error). `B6`'s processor must stay event-name-agnostic so that plan 13's re-coding of `cli.py`'s error arms cannot invalidate it (§2.3.11, §3.6). **No lock** — the constraint is on `B6`'s design, not on its timing.
6. **Plan 16 owns the Python floor** (`>=3.14`). **No lock and no action** — checked and recorded in §2.3.12: no block in this plan depends on a construct below 3.14 or on one 3.14 removes.

### 4.3 Conflict matrix over shared semantic anchors

| # | Shared anchor | My claim | The other claim | Resolution |
|---|---|---|---|---|
| 1 | `ytdlp_downloader._download_with_ytdlp`'s `finally:` | `B2` (teardown becomes directory-level; existing `exists` → `unlink(missing_ok=True)` → `logger.debug("cookie_file_cleaned_up")` sequence **preserved**) | Plan 10 `B1` — three owners, one function | **Sequential, my `B2` first.** `B2` changes what the `finally:` *removes*; `B1` changes what the `finally:` can *do to the outcome*. Doing `B1` first means `B2` re-edits a function whose error-handling contract was just made load-bearing. Whoever lands second re-reads the first and preserves both invariants: the cookie file is removed on **every** interceptable end, and a cleanup failure cannot replace the download's outcome. |
| 2 | `url_sanitizer.sanitize_text_for_log`'s **docstring wording** | `B4` (the claim changes; corrected in my commit) | Plan 10 `B7` — claims the wording; explicitly **ceded the judgement** to phase 06 and kept the wording | **`B4` owns it.** The ceded judgement is the whole of this anchor: `B7` keeps the wording until the phase that can make the wording true has landed. `B4`'s commit is the one that changes it. |
| 3 | `sanitize_text_for_log`'s matcher — `return _URL_REGEX.sub(...)` | `B4` (adds named rules alongside the URL rule) | Plan 10 `B14` lists it as a semantic anchor it owns, **while its own body is `AWAITING DECISION` and internally inconsistent** (its prohibitions cede the exposure judgement to phase 06 and its acceptance says the block does not land if phase 06 owns it) | **`B4` owns it. Do not inherit `B14`'s claim.** `B14` contradicts itself on this anchor; an anchor cannot be owned by a block that disclaims it. `B14`'s **other** claim — the two merge sinks `batch_merge_failed` / `final_merge_failed` — is unaffected and stays with it (row 4). |
| 4 | `ffmpeg_utils`' two merge-failure records | **Not claimed** | Plan 10 `B14` — assigned | **No conflict. `B6` must not touch them.** **Corrected:** an earlier draft of this plan described these as casualties of the loader removal. They are **not** — `_merge_batch_segments` and `_perform_final_merge` are permanent product surface under Decision A (§1.4.1). They stay. `B6` still touches neither. |
| 5 | `ytdlp_downloader._echo_ytdlp_line`'s `sys.stderr.write` | `B5` (the transform at the sink) | Plan 10 `B14` — **ceded to `SEC-005`**; **plan 13 `OUT-007`** — non-progress output becomes one log record per line, stderr clean | **`B5` owns the redaction.** The `B14` cession is explicit. Plan 13's `OUT-007` is a **content conflict, not a shared anchor**: `B5` should land the redaction and let plan 13 own the record-per-line change; if `OUT-007` lands first, `B5` re-scopes per `D-10`. **Neither may weaken the other's half.** |
| 6 | `_download_with_ytdlp`'s **drain loop** (`_monitor_progress` / `_drain_output`) | `B5` — the value handed to `_echo_ytdlp_line` changes; the `output_chunks` buffer stays raw | Plan 10 `B2` (one oversized line must not kill the reader) and `B6` (stop accumulating the whole transcript) — both rewrite this loop | **Sequential, `B5` first.** `B5`'s edit is the smallest possible touch (one argument at the echo call). `B2`/`B6` then rewrite the loop body knowing exactly which value is sanitised and which is raw. **Hard requirement on them:** the raw line must still reach `output_chunks`, and the echo must still receive a line the progress parser can read. If `B2`/`B6` land first, `B5` re-reads the loop and preserves both. **Note:** the loop has since gained a failed-reader-task arm (`subprocess_reader_failed`) — `B6` covers that record; `B5` must not disturb it. |
| 7 | `cookies.py::_cookies_to_netscape` — mechanism **and** test | `B1` — the product fix **plus** the dotless round-trip test | Phase 10 `TST-002` (CRITICAL) — owns the test for the identical mechanism, wants the failing test written first | **`B1` lands the fix and the proving test together** (§2.5). `TST-002`'s broader coverage is the complement, not a duplicate: `B1` adds the **dotless** case and the **mixed** case; `TST-002` owns the wider suite. Whoever lands second reconciles and does not delete the other's coverage. `TST-002` has not executed; if it has by the time `B1` runs, `B1` **stops** and defers the test half to it, keeping only the product fix. |
| 8 | `config.setup_logging` — the **log-file** creation branch and its `SEC-003:` comment | `B3` (the comment and the two log-file oracles) | Plan 12 `ART-007` (confinement-posture decision) | **Sequential, and `B3` goes second.** Plan 12's confirmation: both writes land on this function. `B3` must be written against the **final** shape of `ART-007`'s decision. If `ART-007` changes the log-file creation branch, `B3`'s two log-file oracles must be re-evaluated against it before they land — they are **two of the four** D-11 mode oracles, so an `ART-007` change can invalidate both. **Hard requirement on `B3`:** it must not assert a confinement property `ART-007` has already changed. |
| 9 | `config.setup_logging` — the **structlog processor chain** | `B6` (one redaction processor, after `format_exc_info`) | Plan 12 `ART-007` (same function; plan 12 has confirmed the serialisation) | **Sequential, same function, one writer at a time.** Two sub-cases: (a) if plan 12 lands first, `B6` adds its processor to the chain `ART-007` leaves behind; (b) if `B6` lands first, `ART-007` must not remove or reorder the chain `B6` added to. **The two changes are additive and should not conflict semantically** — `B6` touches `structlog.configure`, `ART-007` concerns artefact confinement — but they are the **same function**, so they cannot be two concurrent edits. |
| 10 | `downloader._temp_argfile` and its oracle | **Already gone — nothing to repair** | Plan 12 `ART-007`; plan 10's loader-removal block | **RESOLVED; no conflict remains.** `_temp_argfile` and `test_temp_argfile_permissions_are_0600` were deleted by a landed commit. `B3` neither deletes nor reverts them. **Withdrawn claim — see row 13.** |
| 11 | `extractor._format_cookies_for_ffmpeg` | `B8` — the **docstring** (the recorded dependency) | A rename of the misnomer (three other plans claim `extractor.py`) | **Split by symbol part, explicitly.** `B8` may rewrite the docstring; `B8` must **not** rename the method. The name now references a transport that no longer exists, so a rename is legitimate — but it is not this finding's work, and a rename inside a security block would make the block unreviewable. Record the misnomer; let the owner schedule the rename. |
| 12 | `tests/test_packaging.py`'s two frozensets | **No block edits them** — no block adds a file | Any block anywhere that adds or removes a file | **No conflict by construction.** Re-measured at `58bb7ce`: `EXPECTED_SDIST_ENTRIES` = **73**, `EXPECTED_WHEEL_ENTRIES` = **32**, `BUILDER_ADDED_SDIST_ENTRIES` = **2** — unchanged by the loader removal. Recorded so it stays true: **if a block adds or removes any file under `src/`, `tests/` or `docs/`, the frozenset edit is mandatory in the same commit.** |
| 13 | **Claim about plan 10's loader-removal block** | **Withdrawn — it was false and this plan did not rely on it** | Plan 12 asserted that plan 10's retirement block does not name `services/ffmpeg_utils.py` for partial deletion | **CORRECTION: plan 10's block DOES name the file and the five loader symbols.** Plan 12's assertion was wrong. This plan never adopted it — no row in this matrix depended on it — and it is withdrawn explicitly so no later reader re-introduces it. **The substantive correction is recorded in row 14.** |
| 14 | `services/ffmpeg_utils.py` as a whole | **Never deletable** — permanent product code, merge engine | Two plans disagreed on `check_ffmpeg_available` | **Settled by Decision A: everything in `services/ffmpeg_utils.py` stays.** Specifically permanent: `_merge_batch_segments`, `_perform_final_merge`, `_merge_segments_batched`, `check_ffmpeg_available`, `_check_merge_space`, `_required_merge_bytes`, `_build_ffmpeg_concat_command`, `_await_ffmpeg_with_timeout`, `iter_process_lines`, `cancel_subprocess`, `cancel_ffmpeg_process`. **No block in this plan deletes, renames, or hardens any of them.** `B6` touches exactly one — `merge_space_probe_failed`'s record — and only by covering it with the pipeline transform, never by editing the merge code. |
| 15 | `cli.py`'s error arms and exit codes | **No claim — recorded only** | Plan 13 owns the four-code contract (`3` = configuration error) | **No lock, no implementation.** `B6`'s only constraint: the processor is event-name-agnostic, so plan 13's re-coding of `_PreambleFailure` from `code=1` to `code=3` cannot invalidate it. No `VAL-` finding here is an exit-code finding; none is widened. |

---

## 5. Risks

### 5.1 Implementation risk

| Risk | Where | Severity | Containment |
|---|---|---|---|
| **`os.kill(pid, 0)` on Windows may `TerminateProcess` the target.** The documented Windows behaviour of `os.kill` calls `TerminateProcess` for a signal value other than the two console-control values. If `0` is in that set, a liveness probe written the obvious way would **kill** the process it is probing. | `B2` (`D-1`) | **Critical if wrong** — a sweep that kills the operator's other processes | Default is the `ctypes` `OpenProcess` + `GetExitCodeProcess` probe. **Settle from CPython source or documentation, never by running it against a live process.** Record the citation in the commit message. The `ctypes` probe may not be "simplified" away without that check. |
| **A reaper that deletes a live run's artefact.** | `B2` | High — credential loss mid-download, and a reaper that is wrong is worse than no reaper | Liveness gate is mandatory and has its **own** test (acceptance criterion 5: a directory with a live PID survives). Sweep is scoped to this product's own directories only — never a top-level temp glob, never age-based (`VAL-602`). |
| **Double transform.** After `B5` and `B6`, a value may be sanitised at a call site and again on the pipeline. | `B4`, `B5`, `B6` | Medium — mangled log text, unreadable failures | Idempotency is a hard acceptance criterion in `B4` and re-asserted with a specific test in `B6`. `***REDACTED***` must not match any rule. |
| **Transform applied before the progress predicate**, corrupting the callback's arithmetic. | `B5` (`D-6`) | Medium — wrong progress percentages | `D-6` resolved: classify and parse on the **raw** line, transform only what is written. Verified by the existing `downloaded`/`total` assertions. |
| **Over-broad redaction degrades every failure investigation.** | `B4`, `B6` | Medium — the transform's current `scheme://host/***REDACTED***` output is what makes `download_failed` readable at all | `D-5`'s token-wise-fallback option is rejected with the reason recorded. Rules must be narrowly anchored. `D-7` (all-strings vs. key allowlist) is conditional on `D-5` for exactly this reason. |
| **Structlog processor mutates the event dict incorrectly**, degrading every log record at once. | `B6` | High — product-wide observability | Processor placement is asserted by a test; semantics settled against authoritative documentation before code is written; `Validator` required. |
| **A missed construction site or consumer** of the two session carriers. | `B7` | Medium — `TypeError` at runtime on the primary download path | Site counts are measured (2 / 1 / 1); `Auditor` re-verifies at execution time. |
| **Narrowing the cookie harvest breaks authenticated downloads.** | `B8` | High if `Alt B`, none if `Alt A` | `Alt A` is the default precisely because no live origin is available to validate `Alt B`. **Raised by Decision A:** the flat header's only consumer is now the *permanent* segment path, so the harvest's scope decision is permanent too. |
| **Narrowing the domain rule breaks the case that currently works.** | `B1` | Medium | `Alt B` (always `FALSE`) rejected in favour of deriving the column from the domain; the dotted-domain round-trip case is an acceptance criterion. |
| **`mypy` hides an undeclared import.** `ignore_missing_imports = true` means `B7`'s `SecretStr` import can be missing from the dependency declaration and mypy stays green. | `B7` | Low — a packaging-time failure | Verify the import resolves against declared `pydantic` **by inspection**. Recorded in `B7`'s acceptance criteria. |
| **The log-pipeline processor is coupled to an exit-code re-coding.** Plan 13 will change which event name a configuration failure produces. | `B6` | Medium — a processor that special-cases an event name would break | The processor is **event-name-agnostic and key-agnostic** (§2.3.11), asserted by a test. `B6` interprets no records. |
| **A pre-existing red format gate gets silently absorbed.** `tests/test_hls_downloader.py` is red on `ruff format --check` at baseline, and three blocks open that file. | `B2`, `B3`, `B5` | Low — an unreviewable diff | Each block either reformats it or states in its commit message that the pre-existing red was left untouched. **Never folded into an unrelated change.** |
| **A stale count is treated as current.** The exception-sink count has moved 11 → 14 → 16 → **18**, and the skip floor moved 4 → **3**, inside this plan's own lifetime. | `B6`, `B3` | Medium — a closure claim resting on a stale enumeration | Both counts are re-verified at execution time and a difference is an `Auditor` finding, not an implementer's discretion. **Never cite a count from this document without re-measuring it.** |

### 5.2 Rollout risk

1. **Three owners on one function** — plan 10 `B1`, `B2`, and `VAL-602`'s prescription all land on `_download_with_ytdlp`'s `finally:`. §4.3 row 1 fixes the order; whoever lands second re-reads the first. **Note:** plan 10's `B1` has since landed as `435ba0b`, giving the `finally:` its `try`/`except OSError`/`else` shape. `B2` builds on that shape rather than replacing it.
2. **Two owners on one function** — plan 12's `ART-007` and `B6`/`B3` on `config.setup_logging`. Plan 12 has **confirmed** it will serialise with this plan. §4.3 rows 8–9.
3. **`B5` overlaps plan 13's `OUT-007` in substance.** Not a lock — a content conflict about what `_echo_ytdlp_line` should do with a non-progress line. §3.5 declares the direction: `B5` lands the redaction; plan 13 owns the record-per-line change. **Whichever lands second must preserve the other's half, and the withdrawn test clause (§3.5's table) must not be silently reverted.**
4. **Every commit is a single block.** No commit may be red. If two blocks cannot be landed independently, they are one block (§2.5). **Exception, declared:** a block that opens the already-red `tests/test_hls_downloader.py` may carry its reformat, provided the commit message says so — otherwise the block would be forced to land on a red gate that is not its own.
5. **Nine other plans' blocks claim anchors in these files** (`segment_downloader.py`, `extractor.py`, `browser.py`, `downloader.py`, `cli.py`). `B6`'s enumeration is the load-bearing one: it must not drift into files other plans are editing.
6. **`B3` is no longer blocked on the removal track** — that constraint is satisfied by a landed commit and has been removed from §4.2. The remaining wait is its artefact oracle's dependency on `B2`.

### 5.3 Regression risk — the prohibitions that survive a fix

These are the behaviours that look like collateral damage and are not. Each has a live test today; each must still be green after its block.

1. **The `\r`-rewrite for progress lines** — rewritten in place, padded to terminal width. (`B5`.)
2. **`echo=False` writes nothing to stderr** — no partial line, no flush. (`B5`.) **This clause stands** under the owner's ruling, which moves output *off* stderr rather than onto it.
3. **The DEBUG `ytdlp_progress_suppressed` record** on an `echo=False` progress line, carrying `downloaded` and `total` computed from the **raw** line. (`B5`.)
4. **`sanitize_text_for_log` keeps `scheme://host/***REDACTED***`.** The host stays visible because that is what makes a failure record diagnosable. **A token-wise fallback is rejected outright** — it would redact the benign portion of every child line and destroy `download_failed`'s readability. (`B4`.)
5. **`sanitize_url_for_log` keeps its public alias identity.** `cli.py` imports it; the entry-layer rule forbids private imports from `utils`. (`B4`, `B6`.)
6. **The `mkstemp` prefix `vk_cookies_` and suffix `.cookies.txt` are frozen.** `.gitignore` matches the suffix; `B2`'s reaper is keyed on the prefix. Renaming either breaks ignore coverage **silently** — the file simply stops being ignored. (`B2`.)
7. **`os.chmod(path, 0o600)` stays** in `_create_temp_cookie_file`, for its POSIX effect. It is a measured no-op on Windows and that is precisely why `B2` adds a *location*-based control beside it. **The log file's `touch(mode=0o600)` / `chmod(0o600)` branches stay for the same reason.** (`B2`, `B3`.)
8. **The QLT-004 `finally` discipline inside `_create_temp_cookie_file`** — close the fd **before** unlinking; on Windows an open fd locks the file and the unlink silently fails. `B2` must not "simplify" the existing close/write-error/unlink/raise sequence.
9. **The `finally:`'s destroy-failure arm** — `cookie_file.unlink(missing_ok=True)` inside a `try`, a failed destroy recorded as `cookie_file_cleanup_failed`, `cookie_file_cleaned_up` on the `else`. **Both event names and both branches stay.** This arm is what makes a failed destroy incapable of replacing the download's outcome. (`B2`.)
10. **`config.setup_logging`'s log-file creation branch** — `touch(mode=0o600)` / `chmod(0o600)`. `B6` touches only `structlog.configure`. (`B6`, `B3`.)
11. **`iter_process_lines`, `cancel_subprocess`, `cancel_ffmpeg_process`, `check_ffmpeg_available`, `_merge_batch_segments`, `_perform_final_merge`, `_merge_segments_batched`, `_check_merge_space`, `_required_merge_bytes`, `_build_ffmpeg_concat_command`, `_await_ffmpeg_with_timeout` all survive** — the merge engine and the yt-dlp loader's draining/cancellation are **permanent product code** under Decision A (§1.4.1). `B5` reads through `iter_process_lines` and must not change its contract; `B6` touches one record in that module and only to cover it with the pipeline transform. **No block deletes, renames, or hardens any of them.**
12. **`DownloadMethod` keeps its two remaining members** (`YTDLP`, `AUTO`). No block restores `FFMPEG`.
13. **`cookie_file.exists()` → the try/except/else teardown → `logger.debug("cookie_file_cleaned_up")`** — the sequence and the event names stay. (`B2`.)
14. **The two commands' option blocks stay byte-identical** except the `--max-retries` help string, and `--method`'s value list is not restored. (§2.3.8.)
15. **`cli.py` needs no edit for `B6`,** and no exit-code change from this plan. The layer rule forbids the entry layer importing private `utils` symbols, which is why the processor must be reachable under a public name. Decision B's four-code contract belongs to plan 13 (§2.3.11).
16. **`network_monitor`'s four exception sites stay excluded** — they log `str(e.__class__.__name__)` only, which is already correct.
17. **`_cookies_to_netscape`'s legacy `str` branch** writes `.vkvideo.ru\tTRUE` and is already correct. `B1` must not "unify" it with the derived expression.

### 5.4 Compatibility risk

1. **No public API, CLI, or configuration change** in any block. `--cookie-source` semantics, `Settings` fields, `DownloadMethod`, exit codes, and the `warn_unknown_env_vars` patch target are all untouched.
2. **`HLSDownloadRequest.cookies` changes type** in `B7`. It is an internal DTO with two construction sites, but its declared type is visible to `mypy src` consumers and to any library consumer constructing one. A `SecretStr` there is source-compatible for construction (`str` is coerced) and **incompatible** for a caller that reads the attribute directly — which is exactly the intent, and why the change is scoped to a measured two-site enumeration.
3. **`DownloadPolicy` is a `@dataclass`** and remains one; `field(repr=False)` changes only `repr`. `repr` is not part of its contract and nothing parses it.
4. **The redaction transform's output shape is a de facto contract** with whatever reads the logs. `B4` keeps the existing shape for existing shapes and introduces `***REDACTED***` — already in the module's vocabulary — for the new ones. No output shape is removed.
5. **`mypy src tests` error count must not rise above 79.** `B7` may add a test-time typing complaint if a fixture is written loosely; that is a delta-gate failure even though `mypy src` is green.

### 5.5 Documentation risk

1. **The ffmpeg-loader-framed documentation sites are not this plan's to fix** (§2.4). Editing them would collide with the removal track and would document a loader that must not exist. They are explicitly OUT — and the loader removal has landed, so they are already handled.
2. **The merge-engine documentation must SURVIVE.** `docs/11-guides/vkdownloader-limitations.md`'s segment-merge disk-space section and `docs/01-tools/api-reference.md`'s reference to it describe **permanent** functionality under Decision A. A removal track that deleted them would be deleting live documentation. **This plan does not touch them, and records the hazard so it is not repeated.**
3. **Four code comments and one docstring make claims this plan changes**: the `DF-007:` comment (`B2`), the `SEC-002:` sanitisation comment and `sanitize_text_for_log`'s docstring (`B4`), and the `SEC-003:` comment above `setup_logging`'s log-file branch (`B3`). Each is corrected **in the same commit as the change that invalidates it**, so the tree never carries a claim its code does not support. **The `SEC-003:` comment must also stop mentioning an argfile** — that mechanism is gone.
4. **The reverse hazard is real and worse:** leaving a comment that over-claims. Three of the four comments today already claim cookie-file-path redaction that the regex cannot deliver. `B4` exists partly to stop the codebase asserting capabilities it lacks.
5. **`B8`'s docstring edit creates a new naming debt.** `_format_cookies_for_ffmpeg` now names a transport that does not exist. The docstring correction is in scope; the rename is not. **Record the debt in the commit message** so it is scheduled rather than forgotten.
6. **`B10` is the only block permitted to touch a path under `.ai/audit/`**, and only the template — never the validation corpus. Recorded again here because it is easy to breach by accident when staging a fix that mentions an audit artifact.

### 5.6 Test-pinning risk

1. **The cookie-file lifecycle is invisible to the suite on Windows** because all remaining D-11 oracles skip. **Any change to the `finally:` therefore needs a test that actually runs on this platform**, and it is new, not an extension of an existing one. `B2`'s criteria 4–6 are that test.
2. **The skip floor is 3.** A **fourth** D-11 skip is review-blocking; more than 4 is a hard stop. The floor **fell** from 4 to 3 because the loader removal deleted one oracle with its subject — **not** because of anything in this plan. `B3`'s effect is therefore demonstrated by a **named conversion**, not by a count delta (§3.3 criterion 2). **If `B3` leaves all three oracles gated, it has closed nothing and must be reported as not-landed.**
3. **An existing expectation must never be relaxed to let a block land.** Where a block changes behaviour, the change in the expectation must be visible in the diff and defensible. Two declared exceptions, both owner-directed: `B5`'s rewrite of the "non-progress emits no record" test (§3.5's clause table) and `B5`'s new sibling for a redaction that changes benign passthrough only.
4. **A retargeted fixture is a silent coverage loss.** `tests/test_cookies.py`'s `_DOMAIN` is hard-coded into three builders; changing it would re-aim every existing case. `B1` adds, never retargets.
5. **A new test that skips on Windows is worse than no test** — it looks like coverage. Every test this plan adds runs on the declared platform or is explicitly a POSIX-only addition alongside a Windows-side counterpart.
6. **The `tests/test_packaging.py` gate builds for real.** It is runnable and green and must stay green. It is also the gate that catches an undeclared file change — which now includes a **removal**, not only an addition.
7. **`ruff format --check src tests` is red at baseline** on `tests/test_hls_downloader.py`, and three blocks open that file. A block that reformats it must say so; a block that does not must also say so. **Silence is not acceptable in either direction.**

### 5.7 Risk carried but not retired: `SEC-004`

`SEC-004` is **superseded, not fixed, and now confirmed** by Decision A. No block works on it. Its removal surface is named in §1.4.1, split into what was deleted permanently and what is permanent product surface, and documented skip **S-3 stays permanently unanswerable and stays recorded as retired.**

**The one hazard this section exists to prevent.** An earlier draft of this plan listed the merge functions among the symbols that "die with the transport", and separately listed `check_ffmpeg_available` among those that survive. **Both of those were open questions at the time and both are now settled by the owner, in the same direction: nothing in `services/ffmpeg_utils.py` goes away.** Any later phase that reads this plan and concludes the merge engine is scheduled for removal is reading a superseded statement. §1.4.1, §4.3 row 14 and §5.3 item 11 all state the settled position; this section exists so a reader who lands here first is not misled.

**What the retirement does and does not reduce.** It removes ffmpeg-the-loader from **`SEC-003` by exactly one of its four oracles** (already landed). It removes `SEC-004`'s entire justification, because with one loader there is no argv asymmetry left to breach. It makes documented skip **S-3 permanently unanswerable**. It reduces **`SEC-001`, `SEC-002`, `SEC-005`, `SEC-006`, `SEC-007`, `SEC-008`, `SEC-010`, `VAL-602` by not more than a fraction** — and for `SEC-001`/`SEC-002` the reduction is in *scope* only (§1.4.2).

**The residue an Implementor must not mistake for closure.** The yt-dlp loader still passes `--cookies <path>` as a bare argv element. That is correct behaviour — yt-dlp has no response-file mechanism for option values — and the artefact now sits in a per-run private directory (`B2`), so the exposure `B2` addresses is the file's **confidentiality**, not its **process-listing** visibility. **Do not invent a transport-level fix for `SEC-004` in a later phase**: the correct action was deletion, it has landed, and it is permanent.

### 5.8 Risks recorded but not owned here

Two owner rulings touch this plan without belonging to it. Neither is implemented here; both are recorded so no block of this plan collides with them.

| Ruling | Owner | What it constrains here | What it does **not** do |
|---|---|---|---|
| **Decision B** — dedicated exit code `3` for configuration error; `1` download-failure-only; `2` usage error; `4`+ unallocated | plan 13 | `B6`'s processor must be event-name-agnostic and key-agnostic (§2.3.11, §3.6, §4.3 row 15) | **No block here produces or documents a status code.** `VAL-601`/`VAL-602`/`VAL-603` are audit-pipeline findings and are **not** widened to become exit-code findings. |
| **Decision C** — Python floor is `>=3.14` | plan 16 | Nothing. **Checked and recorded: no block depends on a construct below 3.14, and none uses a construct 3.14 removes** (§2.3.12) | **The floor change is not implemented here.** `requires-python` is untouched by this plan. |

---

## 6. Task specifications

One entry per block, in landing order. Each entry is what a fresh Implementor executes without re-deriving anything.

---

### `T-B1` — Derive the Netscape `include_subdomains` column

**Commit:** `fix(cookies): derive Netscape include_subdomains from the cookie domain`

1. **Freeze the interfaces.** Read `services/cookies.py` and confirm exactly three branches exist (header-only, `list[Cookie]`, legacy `str`) and that `_cookies_to_netscape` is the only writer of the Netscape format in `src/`. If a fourth branch exists, **stop** — that is an `Auditor` finding, not an implementer's discovery.
2. **Add the dotless fixture in `tests/test_cookies.py`.** Do **not** modify the module-level `_DOMAIN` or the three existing builders. Add a builder that takes a domain.
3. **Write the failing test first**, in `TestCookieRoundTripThroughConsumer`, using the existing harness: write via `_create_temp_cookie_file`, read via `YoutubeDLCookieJar(path).load()`. Two cases: (a) a host-only cookie alone survives with its value intact; (b) a **mixed** file — one dotted cookie then one host-only cookie — yields **both** cookies. Case (b) is the one that reproduces the real failure; (a) alone would not have caught it.
4. **Run the test and watch it fail.** A test that passes before the fix is not testing the fix.
5. **Apply the fix** in the `list[Cookie]` branch: derive the `include_subdomains` column from `domain` — leading dot ⇒ `TRUE`, otherwise `FALSE`.
6. **Do not touch** the legacy `str` branch, `_normalize_expiry`, or `_sanitize_cookie_value`.
7. **Gates:** `uv run pytest tests/test_cookies.py -q` green · `uv run mypy src` clean · `uv run ruff check src tests` clean · full suite green, skips **not above 3**. (`ruff format --check` is **red at baseline**; this block does not open `tests/test_hls_downloader.py`, so it neither fixes nor worsens that — say which in the commit message.)
8. **Commit message records:** the derived rule; the fact that the literal `TRUE` made a host-only domain fail `domain_specified == initial_dot` for the whole file; and a pointer to `TST-002` as the coverage complement.
9. **If `TST-002` has already landed when you start:** stop, and land only the product fix, noting in the commit that the test half is `TST-002`'s.

---

### `T-B2` — Per-run private directory and liveness-gated sweep

**Commit:** `fix(cookies): confine the credential artefact to a per-run private directory with a liveness-gated sweep`

1. **Settle `D-1` before writing code.** Determine from CPython source or authoritative documentation whether `os.kill(pid, 0)` terminates the target on Windows. **Do not test it on a live process.** Record the citation in the commit message. If `0` is in the terminating set, the Windows branch uses the `ctypes` `OpenProcess` + `GetExitCodeProcess` probe and `os.kill(pid, 0)` is **prohibited there**.
2. **Freeze the artefact's naming strings.** `prefix="vk_cookies_"`, `suffix=".cookies.txt"`. They are load-bearing beyond this block (§5.3.6).
3. **Add the per-run private directory**, created on first artefact creation, recording the owning PID. The `mkstemp` call moves into it.
4. **Preserve the existing sequences exactly.** The write-error path in `_create_temp_cookie_file` (unlink then re-raise) and the QLT-004 close-before-unlink discipline stay. `os.chmod(path, 0o600)` stays for its POSIX effect. The `finally:`'s `try`/`except OSError`/`else` shape — `cookie_file_cleanup_failed` on a failed destroy, `cookie_file_cleaned_up` on success — stays exactly as it is.
5. **Rework the `finally:` in `_download_with_ytdlp`** to remove the directory as well as the file, keeping the current `try`/`except`/`else` teardown intact — same branches, same two event names — and adding the directory teardown after it.
6. **Add the sweep**, invoked before this process creates any artefact, scoped to this product's own artefact directories, deleting a directory **only** when its recorded PID is not live. **Never a top-level temp glob. Never age-based** (`VAL-602`).
7. **Register `atexit` exactly once**, guarded so repeat artefact creation does not register a second hook.
8. **Write the four new tests** (§3.2 acceptance 4–7): stale-and-dead PID → swept; stale-and-live PID → **survives**; artefact's parent is the recorded directory, not the shared temp root; `atexit` registered once. All four **run on Windows**.
9. **Correct the `DF-007:` comment** in the same commit — its claim changes.
10. **Do not touch** `config.setup_logging`, `signal_handlers`, or anything in `services/ffmpeg_utils.py` — the merge engine is permanent product code (Decision A).
11. **Gates:** full suite green with **no existing expectation changed** (additions only) · skips **not above 3** · `uv run mypy src` clean · `uv run ruff check src tests` clean · **`uv run mypy src tests` count ≤ 86** · and the pre-existing `ruff format` red on `tests/test_hls_downloader.py` either fixed or explicitly acknowledged.
12. **Commit message records:** `D-1`'s resolution and its citation; `D-2`'s deferral with the missing dependency named; `D-3`'s anchor choice; and the explicit statement that no top-level glob and no age heuristic was used, and why.

---

### `T-B4` — Widen the redaction transform

**Commit:** `fix(logging): redact the product's own artefact paths in sanitised child output`

1. **Re-derive the call-site set** of `sanitize_text_for_log`. The baseline enumeration is three call classes. A fourth is an `Auditor` finding.
2. **Resolve `D-5`.** Default: artefact-name patterns only. Adopting the header-value rule requires evidence that a sink receives a `Cookie:`/`Set-Cookie:` header **from a child process**.
3. **Add named, individually testable rules** alongside the URL rule. Do **not** replace the single `.sub()` with a token-wise fallback (§5.3.4).
4. **Reuse `***REDACTED***`** as the replacement, so the rules read alike. Preserving a basename is acceptable only as a stated decision with a tight matching rule.
5. **Prove idempotency** for every rule, and prove `***REDACTED***` matches no rule. This is a hard criterion — `B5` and `B6` both apply the transform twice by design.
6. **Write the tests** in `TestSanitizeTextForLog`: an artefact path is redacted; the same text with no artefact-shaped token is **byte-identical** to its input; a signed CDN URL still reduces to `scheme://host/***REDACTED***`; double application equals single application. Add path-shaped and header-shaped cases — **there are none today**.
7. **Correct the docstring** and the `SEC-002:` comment in `services/ytdlp_downloader.py` in the same commit.
8. **If `D-5` resolved to Alt A**, state in the docstring which shapes are **not** covered. The block makes the existing claim true; it does not imply coverage that does not exist.
9. **Do not** re-export `sanitize_text_for_log` from `utils/__init__.py`; services import it directly and the layer rules permit it.
10. **Gates:** `uv run pytest tests/test_url_sanitizer.py -q` green · the four **existing** cases green **unchanged** · full suite green · `uv run mypy src` clean · `ruff check` and `ruff format --check` clean.

---

### `T-B5` — Redact at the terminal echo

**Commit:** `fix(download): redact child output before it reaches the console`

1. **Re-derive the `_echo_ytdlp_line` call sites and every caller that sets `echo`.** An undiscovered `echo=True` changes the blast radius — stop and report if found.
2. **Check whether plan 13's `OUT-007` has landed** (non-progress output → one log record per line, stderr clean). **This decides the shape of the whole block** (§3.5).
   - **Not landed (default):** continue with steps 3–9 as written.
   - **Landed:** re-scope per `D-10` — there is no stderr write for a non-progress line, so the redaction goes on the **value handed to the log call**, and the idempotency requirement now composes with `B6`'s pipeline processor. `B6`'s idempotency test is the evidence; do not weaken it.
3. **Confirm the admission predicate is `_is_ytdlp_progress_line`,** not `_parse_ytdlp_progress`. They are different functions; the source report names the wrong one.
4. **Apply the transform to what reaches the console only** (or, under `D-10`, to what reaches the log record only). The two drain-loop call sites pass the raw decoded line for **two** purposes: the echo and the `output_chunks` buffer. **The buffer must stay raw.** **Do not disturb the `subprocess_reader_failed` arm** the loop gained — `B6` covers that record; `B5` leaves it alone.
5. **Keep classification and progress parsing on the raw line** (`D-6`). The callback's `downloaded`/`total` are read from the raw text; a transform that ran first could corrupt them. Add the evidence test to the existing `test_ytdlp_echo_false_progress_emits_debug_log`.
6. **Transform both write branches** — the progress branch's `text` and the non-progress branch's `line`.
7. **Evaluate the `echo` gate before any transform**, so `echo=False` writes nothing even for a redaction-worthy line.
8. **Add the redaction test** to the existing echo contract class: a non-progress line carrying a signed CDN URL reaches the console redacted. **Keep** the existing "passed through unchanged" assertion for benign input — do not weaken it.
9. **Rewrite — do not delete, do not relax — the non-progress `echo=False` test.** Its new form asserts the owner's ruling: with stderr clean, the line is emitted as **one log record**. This is the block's one declared test change (§3.5's clause table). **The stderr-empty half of that same test remains asserted.**
10. **Update the docstring** to state that what reaches the console is the transformed line and that the buffer receives the raw one.
11. **Verify the surviving clauses** are green unchanged: the `\r` rewrite and terminal-width padding; `echo=False` writes nothing to stderr; the DEBUG `ytdlp_progress_suppressed` record with its `downloaded`/`total`.
12. **`tests/test_hls_downloader.py` is already red on `ruff format --check` at baseline.** Reformat it or state that the pre-existing red was left untouched. Silence is not acceptable.
13. **Gates:** full suite green · skips **not above 3** · `uv run mypy src` clean · `uv run ruff check src tests` clean · **`uv run mypy src tests` count ≤ 86.**
14. **Commit message records:** whether `OUT-007` had landed; the declared test change and its reason; `D-6`'s resolution; `D-10`'s resolution if applicable.

---

### `T-B6` — One redaction transform on the log pipeline

**Commit:** `fix(logging): redact secret-shaped text on the log pipeline`

1. **Re-verify the eighteen-record enumeration** (the table in §3.6). **The count has moved three times** — 11, 14, 16, now 18. A nineteenth record, or a missing one, is an `Auditor` finding. If the count differs, **the finding's closure claim changes** — stop and report.
2. **Confirm `format_exc_info` is in the chain** and that the processor goes **after** it and **before** the renderer. This is what makes the traceback records coverable; it is also why the rejected call-site-only alternative fails.
3. **Settle structlog processor semantics** against authoritative documentation: what a processor may mutate in the event dict, and where `format_exc_info` places its output. **Before writing code.**
4. **Choose the module.** Default: extend `utils/url_sanitizer.py`, no new file, no frozenset edit. Alternative: a new `utils/log_redaction.py` — cleaner separation, but the `tests/test_packaging.py` frozenset edit is then **mandatory in the same commit**, and `utils/__init__.py`'s `__all__` decides what is public. State which was chosen.
5. **Place the processor in `config.setup_logging`'s `structlog.configure`.** Import it under a **public** name — the layer rule forbids the entry-adjacent layer from importing private `utils` symbols. **`cli.py` is not edited.**
6. **Keep the processor event-name-agnostic and key-agnostic.** It must not special-case `download_failed` or branch on any event name. This is the Decision B constraint: plan 13 will re-code `cli.py`'s configuration-error arm from `code=1` to `code=3`, changing which record a configuration failure produces. **The processor transforms values; it does not interpret records** (§2.3.11, §4.3 row 15).
7. **Resolve `D-7` only after `T-B4` has landed**, by asking whether the final rule set can match a field the product logs for benign purposes. Narrow rules ⇒ every string value. Broad rules ⇒ a key allowlist over `error`, `exception`, and the rendered-traceback key.
8. **Do not edit any of the eighteen call sites.** If one seems to need an edit, escalate — that is a design failure, not a task.
9. **Do not touch** `batch_merge_failed` / `final_merge_failed` (plan 10 `B14`; permanent product surface under Decision A) or the four `network_monitor` sites. **Do not touch any merge code in `services/ffmpeg_utils.py`** — permanent, and `B6` touches only the one record's coverage, never the merge implementation.
10. **Write the tests:** drive the **configured** pipeline (not a hand-built event dict) with a redaction-worthy value in each record's field; **at least one with `exc_info=True`** asserting the rendered traceback is redacted; **one for `cookie_file_cleanup_failed` covering both `path` and `error`**; one asserting the processor's chain position; one asserting **event-name-agnosticism**; one asserting idempotency against a pre-sanitised call site.
11. **Do not touch** `setup_logging`'s log-file `touch`/`chmod` branch or the `SEC-003:` comment above it — `B3` owns those.
12. **Gates:** full suite green · skips **not above 3** · `uv run mypy src` clean · `uv run ruff check src tests` clean · **`uv run mypy src tests` count ≤ 86.**
13. **Commit message records:** the eighteen-record enumeration; the five records a call-site edit could not reach; the two records added since the original baseline; `D-7`'s scope and its residual; the module-placement choice; and the Decision B constraint on event-name-agnosticism.

---

### `T-B3` — Executable permission oracles

**Commit:** `test(logging): replace the skipped permission oracles with ones that execute on Windows`

> **Rewritten after re-baselining.** This block now converts **three** oracles, is **UNBLOCKED**, and demonstrates its effect by named conversion rather than by a skip-count delta.

1. **Re-verify the skip set.** It must be the three D-11 oracles: `test_config.py`'s `test_log_file_created_with_owner_only_permissions` and `test_existing_log_file_permissions_updated`, plus `test_hls_downloader.py::TestCreateTempCookieFile::test_file_permissions_are_0600`. Run them with `-rs`. A **fourth** D-11 skip appearing is review-blocking.
2. **No co-edit with the loader removal is required or possible.** `_temp_argfile` and its oracle were deleted by a landed commit. `B3` neither deletes nor reverts them; the commit message **acknowledges** that they are gone by someone else's change, so a reviewer reading the diff is not left guessing (§3.3 criterion 6).
3. **Decide the split.** The **two log-file oracles** are independent of `B2` and of the removal — they may land first. The **artefact oracle** asserts a property `B2` introduces and **must not land before `B2`.** If `B2` has not landed, land the log-file half and say in the commit message that the artefact half waits on `B2` (§3.3 criterion 5).
4. **Check the other gate.** If plan 12's `ART-007` has changed `config.setup_logging`'s log-file creation branch, re-evaluate the two log-file oracles against its decision before writing anything (§4.3 row 8). **Those two oracles are the exposed ones.**
5. **Resolve `D-4`** for the two log-file oracles. Default `B` (assert the read-only attribute is clear — a real Windows-meaningful assertion, which the `0o444` positive control proves the platform can report). `A` (assert the requested mode) is the minimal fallback. **`C` (read the DACL) is prohibited** — it needs a dependency §1.3.4 forbids. **Neither `A` nor `B` may assert owner-only confinement on Windows**; if both are unsatisfying, the honest outcome is the POSIX gate plus a Windows-side test that pins the branch and the request, with a docstring that says plainly what is and is not guaranteed.
6. **Convert the credential-artefact oracle** (after `B2`). Assert what `T-B2` delivers: the artefact's parent is the per-run private directory this process created, and that directory is removable. The POSIX mode assertion may be **kept as an additional** check — additive, never a replacement that loses coverage. Update the docstring to state what is asserted on which platform.
7. **Demonstrate the block's own effect** by named conversion, not by a count: the commit message names every oracle converted, every oracle left gated **and why**, and the resulting skip count. **If all three remain gated, report the block as not-landed.**
8. **Correct the `SEC-003:` comment** above `setup_logging`'s log-file branch in the same commit: it must no longer imply a confinement Windows does not deliver, and it must **stop mentioning an argfile** — that mechanism is gone.
9. **`tests/test_hls_downloader.py` is already red on `ruff format --check` at baseline.** `B3` opens that file; it must either reformat it or state that the pre-existing red was left for a separate formatting commit. **Never fold an unrelated reformat into a test-semantics change.**
10. **Gates:** the D-11-guarded count is **strictly lower than 3, or every remaining guard is justified per-oracle in the commit message** · every remaining skip named · full suite green · `uv run mypy src` clean · `uv run ruff check src tests` clean · **`uv run mypy src tests` count ≤ 86.**

---

### `T-B7` — Mark the session carriers

**Commit:** `fix(models): mark the session carriers so they do not render their contents`

1. **Re-verify the site counts**: `HLSDownloadRequest` constructed at **2** sites, `DownloadPolicy` at **1**, and the value read at **1** consumer. A different count is an `Auditor` finding.
2. **`cookies` → `SecretStr`** in `models/dtos.py`. Pydantic-native; renders masked; requires an explicit `.get_secret_value()`, so a forgotten unwrap is a type error rather than a silent leak. **Not** `Field(repr=False)` — that hides the field but leaves the value a plain `str`.
3. **`headers` → `field(repr=False)`** on `DownloadPolicy`. A `dict` cannot be a `SecretStr`. `field(repr=False)` costs nothing; a custom `__repr__` printing a header count is acceptable if stated, but the simple form is the default.
4. **Update all four sites in one commit** — both constructions, the one construction of `DownloadPolicy`, and the consumer that unwraps into the outgoing `Cookie` header.
5. **Verify `SecretStr` resolves against the declared `pydantic` dependency by inspection** — `ignore_missing_imports = true` means mypy will not catch a missing declaration (§5.1).
6. **Write the tests:** `repr()` of an `HLSDownloadRequest` carrying cookies contains no cookie value; `repr()` of a `DownloadPolicy` carrying a `Cookie` header contains no header value; the segment path still sends the `Cookie` header unchanged; `_attempt_segment_resume`'s refresh path still works.
7. **No `Any`.** The unwrap is a typed call.
8. **Gates:** full suite green · `uv run mypy src` clean · `ruff check` and `ruff format --check` clean · **`uv run mypy src tests` error count ≤ 79**.

---

### `T-B8` — Record the cookie-harvest decision

**Commit:** `docs(extractor): record why the browser cookie harvest is not filtered`

1. **Re-verify the bounding fact.** `create_stealth_page` still uses `new_context(viewport=…, user_agent=…, locale=…, timezone_id=…)`, and there is still **no** `storage_state`, **no** `launch_persistent_context`, **no** `user_data_dir` anywhere in the tree. If any has appeared, **the exposure is no longer bounded** — this block's priority and default both change; stop and report.
2. **Resolve `D-9`.** Default `A`: record the dependency precisely at the harvest site and pin the composition with a test. **No behaviour change.** `B` (narrow the flat header by domain suffix) requires an owner statement of the CDN's cookie-domain dependency or a live-origin observation; neither is available, and the change cannot be validated on this platform.
3. **Do not rename `_format_cookies_for_ffmpeg`.** Its **name** references the retired transport and belongs to the removal track; `B8` may rewrite its **docstring** (§4.3 row 11).
4. **Do not change the harvest call.**
5. **Under `Alt A`,** add a test pinning the composition contract so an accidental change fails.
6. **Commit message records** which alternative was chosen and the criterion that decided it.

---

### `T-B9` — The severity row for a validated finding

**Commit:** `docs(audit): add the severity row for a finding that passes verification`

1. **Check for sibling copies** of the four-row table under `.kilo/commands/audit/phases/`. Fixing one file and not its siblings leaves the corpus inconsistent — report what you find.
2. **Add the fifth row** to the severity table: a finding whose verification passed and whose decision is `validated`. The row states both the band and where the band comes from.
3. **Keep it consistent** with the section's own sentences: it does not redefine a severity word, and it does not make a decision change a severity. The existing decision-application rule — `Validated` keeps the severity as-is — is the source the row points at.
4. **Add no fifth severity word.** A fifth **row** is the fix; a fifth **word** is prohibited.
5. **Adjust surrounding prose** only if the new row makes an existing sentence inaccurate.
6. **No source, no test.** This block touches exactly one file.
7. **Verification:** a reader can answer "what severity does a validated finding carry?" from the table alone.

---

### `T-B10` — Stop the template pre-answering its summary

**Commit:** `docs(audit): stop the findings template pre-answering its own summary`

1. **Re-verify the evidence.** All eleven `99-validation/*.md` artifacts still delete the four sections. A twelfth artifact that **keeps** them falsifies the evidence — stop and report.
2. **Check whether the validate phase needs a per-phase tally** that its validation summary does not already carry. Prefer `Alt B` (delete the four sections) when it does not; choose `Alt A` (make them fillable) only when it does.
3. **Remove every pre-filled count.** The zero-valued `CRITICAL/HIGH/MEDIUM/LOW` rows are the defect.
4. **State per section** in the commit message: fillable or removed.
5. **Fix any cross-reference** pointing at a removed section. Leave the `## Findings` block and the field-reference table alone, except for those cross-references.
6. **Staging prohibition.** Stage **exactly one path**: `.ai/audit/templates/audit-findings.md`. **Never** anything under `.ai/audit/99-validation/**`. Confirm with `git status` before committing.
7. **No source, no test.**

---

## 7. Verification strategy

### 7.1 Per-block gate

Every block runs the **full** suite before its commit. Per-block additions on top:

| Block | Per-block gate beyond the full suite | Why this gate |
|---|---|---|
| `B1` | `uv run pytest tests/test_cookies.py -q` green **and** the new dotless + mixed cases were observed **failing** before the fix | A test that passed before the change was never testing the change. The mixed case is the one that reproduces the whole-file loss. |
| `B2` | `uv run pytest tests/test_hls_downloader.py -q -rs` — the four new lifecycle tests **run on Windows**, and the live-PID test **passes** | The existing suite cannot see this area (the D-11 oracles skip). The live-PID survival test is the only check on the sweep's concurrency safety — `VAL-602`'s whole point. |
| `B4` | `uv run pytest tests/test_url_sanitizer.py -q` green · the four **existing** cases green **unchanged** · double-application equals single-application · a case for a cookie-artefact path | Existing cases passing unchanged is the evidence the rule is additive rather than a rewrite. Idempotency is shared proof on which `B5` and `B6` both depend. |
| `B5` | The `echo` contract: `\r` rewrite unchanged · **`echo=False` writes nothing to stderr** · the rewritten non-progress test asserts the owner's record-per-line ruling · a new redaction case | The stderr-clean half is the half `B5` must not break, and it is the half the owner's ruling strengthens. **The rewritten clause is the one declared test change in this plan** — it must be a rewrite with a reason, never a relaxation. |
| `B6` | A test drives an **`exc_info=True`** record through the **configured** chain and asserts the rendered traceback is redacted · a test covers `cookie_file_cleanup_failed`'s **both** fields · a test asserts the processor's chain position · a test asserts **event-name-agnosticism** · a test asserts idempotency against a pre-sanitised call site | These five are what distinguish this block from the rejected call-site-only remedy. Chain position is asserted because a future reorder that moves the processor before `format_exc_info` silently disables the whole block. Event-name-agnosticism is the Decision B constraint made observable. |
| `B3` | **A named conversion, not a count delta:** the commit message names every oracle converted, every oracle left gated **and why**, and the resulting skip count · **every remaining skip named** · no surviving oracle claims owner-only confinement on Windows | The finding *is* the absence of an executable oracle. The floor already fell to 3 for reasons unrelated to this block, so a count delta proves nothing — **the named conversion is the evidence.** If all three stay gated, the block has closed nothing and is reported not-landed. |
| `B7` | Two `repr()` tests (both carriers) · the segment path still sends its `Cookie` header · **`uv run mypy src tests` count ≤ 86** | `ignore_missing_imports = true` hides an undeclared import from the `src` gate, so the delta gate and an explicit dependency check are the only backstops. |
| `B8` | `uv run pytest tests/test_extractor.py -q` green · (under `Alt A`) the composition-pinning test | Under `Alt A` there is no behaviour change, so the pinning test is the entire gate. Under `Alt B` a `Validator` review is **required** in addition. |
| `B9` | A reader can answer "what severity does a validated finding carry?" from the table alone · no sibling table left unfixed | The document's value is that it is followed literally; an ambiguous row is worse than the gap. |
| `B10` | `git status` shows no path under `.ai/audit/99-validation/` touched · no pre-filled count remains in the template | The staging prohibition is the only thing protecting the validation corpus from being edited by a fix block. |

### 7.2 End-of-plan gate

Run **after the last block lands**, in this order, and record the outputs in the plan's completion note:

| # | Command | Pass condition |
|---|---|---|
| 1 | `uv run pytest -q -rs` | exit 0 · **skips not above 3**, every skip named in the completion note · passed count ≥ the baseline **752** |
| 2 | `uv run ruff check src tests` | `All checks passed!` · exit 0 |
| 3 | `uv run ruff format --check src tests` | exit 0 **or** the pre-existing red on `tests/test_hls_downloader.py` is explicitly accounted for in the completion note |
| 4 | `uv run mypy src` | `Success: no issues found` · exit 0 |
| 5 | `uv run mypy src tests` | error count **≤ 86** (delta gate; exit code is meaningless) |
| 6 | `uv run pytest tests/test_packaging.py -q` | green — the real-build entry-set gate still holds |
| 7 | `git status --porcelain` | only intended paths; **nothing** under `.ai/audit/99-validation/` |
| 8 | A full re-derivation sweep | `atexit`, `mkdtemp`, `O_EXCL`, `chown`, `umask`, `0o700`, `icacls`/`setfacl`/`win32security` — record what now exists in `src/` and confirm it is only what `B2` added |
| 9 | A re-count of the exception-text sinks | the **eighteen** records of §3.6 are all covered by the pipeline; **no** nineteenth appeared |
| 10 | A re-count of the D-11-guarded oracles | **zero** remaining, or every one justified per-oracle in the completion note |
| 11 | A check that nothing permanent was removed | `services/ffmpeg_utils.py` still exports its full permanent surface (§4.3 row 14) and `DownloadMethod` still has exactly `YTDLP` and `AUTO` |
| 12 | `git log --oneline` | one commit per block, `{type}({scope}): {description}` shape, nothing amended |

**Not gates, and must never be reported as such:** `uv run ruff check .` (red on untracked `tmp/`), `uv run mypy` with no path (invalid invocation), `uv run mypy src tests`'s exit code (delta only).

### 7.3 Per-finding verification trace

How each finding is shown to be closed. A finding is closed when its **acceptance criterion** is observable, not when a commit exists.

| Finding | Closed when | Where verified |
|---|---|---|
| `SEC-001` | The yt-dlp cookie artefact is inside a directory this process created, `atexit` is registered once, and the `DF-007:` comment matches. **The mode bit alone is not the evidence** — it is a measured no-op on Windows. | `T-B2` criteria 1, 6, 7, 9 |
| `SEC-002` | A stale directory with a **dead** PID is swept; a stale directory with a **live** PID survives. Together those two are the whole finding: reclamation without unsafe reclamation. | `T-B2` criteria 4, 5 |
| `SEC-003` | **Each of the three surviving oracles has a Windows-executable assertion**; the commit message names every conversion and every remaining guard **with its reason**; no surviving oracle claims Windows confinement. The floor already fell to 3 for unrelated reasons, so **named conversion is the evidence, not a count delta**. | `T-B3` steps 7, 1, 10 |
| `SEC-004` | **Superseded, not closed — now confirmed by Decision A.** Recorded as retired, its removal surface named and split into deleted-permanently vs. permanent-product-surface, and skip S-3 re-recorded as retired. **No verification is possible or intended** — a fix here would be the defect. | §1.4.1, §5.7 |
| `SEC-005` | A signed CDN address in a non-progress line reaches the console (or the log record) **redacted**, while the benign "unchanged" case and the stderr-clean clause stay green. The one declared test change is recorded with its reason. | `T-B5` steps 8, 9, 11 |
| `SEC-006` | An artefact path in free text is redacted — **including the `cookie_file_cleanup_failed` record's own `path` field**, which is the live instance; text with no matched shape is byte-identical; the host stays visible; double application is a no-op. | `T-B4` steps 3–6, §3.6 |
| `SEC-007` | An `exc_info=True` record's **rendered traceback** is redacted through the **configured** chain, with no edit to any of the eighteen call sites, none to `cli.py`, and the processor proven event-name-agnostic. | `T-B6` steps 5, 10 |
| `SEC-008` | Neither carrier's `repr()` contains its value, and the segment path still sends its `Cookie` header. | `T-B7` step 6 |
| `SEC-009` | A host-only domain survives a real `YoutubeDLCookieJar` round trip **on its own** and **in a mixed file**, with the dotted case unaffected. | `T-B1` steps 3, 5 |
| `SEC-010` | The harvest site carries a written reason naming what the cookies are for, and the composition is pinned by a test. Under `Alt B` instead: the narrowed set is demonstrated by a test and the change is declared unvalidated-on-platform. | `T-B8` steps 2, 5, 6 |
| `VAL-601` | The table has a row for a validated finding; it introduces no fifth severity **word**; no sibling table is left unfixed. **Audit-pipeline only — not an exit-code finding.** | `T-B9` steps 1–4 |
| `VAL-602` | Discharged inside `B2`: no top-level glob, no age heuristic, a liveness gate with its own survival test, and the reconciled order (sweep defined before the run's directory is created; the `finally:` still removes the file). | `T-B2` steps 6, 12 |
| `VAL-603` | No pre-filled count remains; each of the four sections is fillable or removed, stated per section; nothing under `.ai/audit/99-validation/` is touched. **Audit-pipeline only — not an exit-code finding.** | `T-B10` steps 3, 4, 6 |

### 7.4 What this plan does not verify

Stated plainly, so no one reads a green gate as more than it is.

1. **No live VK origin.** No block's behaviour is validated against a real authenticated download. `B8`'s `Alt B` is unreachable for exactly this reason, and `B7`'s segment-path test is the narrowest available seam rather than a real CDN request.
2. **No POSIX run.** Every gate in §7.2 executes on Windows only. The POSIX branches (`os.kill(pid, 0)`, the retained mode assertions) are reasoned and reviewed, not executed here.
3. **No process-listing exposure measurement.** `B2` confines the artefact's **confidentiality** by location. It does not change the yt-dlp loader's argv, and the argv exposure `SEC-004` used to frame was addressed by **permanent deletion**, not by a fix.
4. **No DACL assertion.** Owner-only confinement on Windows is **not** proven by this plan and is **not** claimed by it. `D-2` records the deferred capability and the dependency that would be needed. The point-in-time machine facts — the temp root's ACL, the `%TEMP%` residue count, the `0o444` positive control — are evidence, may be re-measured, and are never asserted.
5. **No verification of the merge engine.** Decision A keeps it; this plan does not test, harden, or change it. End-of-plan gate item 11 checks only that its surface is **still present** — that it works is plan-independent and out of scope.
6. **No exit-code verification.** Decision B's four-code contract is plan 13's. This plan produces no status code and verifies none. Its only obligation is the event-name-agnosticism assertion, which is about `B6`'s own design, not about the codes.
7. **No Python-floor verification.** Decision C is plan 16's. §2.3.12 records the checked answer — no dependency, no construct at risk — and that is a static inspection, not an execution under 3.14.

---

## Execution record

*To be completed by the Implementor as blocks land. One line per block: commit hash, gate results, and any deviation from this plan with its reason. **Re-measure every baseline number before the first block lands — several moved during this plan's own lifetime.***

**Baseline at `HEAD = 58bb7ce`, measured for this revision:** 752 passed · 3 skipped · `ruff check` clean · `ruff format` **red on `tests/test_hls_downloader.py`** · `mypy src` clean (31 files) · `mypy src tests` **86 errors in 8 files** · `EXPECTED_SDIST_ENTRIES` 73 · `EXPECTED_WHEEL_ENTRIES` 32 · builder-added 2 · exception-text sinks **18**.

| Block | Commit | Suite | ruff check | ruff format | mypy src | mypy src tests | Skips | Notes |
|---|---|---|---|---|---|---|---|---|
| `B1` | | | | | | | | |
| `B2` | | | | | | | | |
| `B4` | | | | | | | | |
| `B5` | | | | | | | | |
| `B6` | | | | | | | | |
| `B3` | | | | | | | | |
| `B7` | | | | | | | | |
| `B8` | | | | | | | | |
| `B9` | | | | | | | | |
| `B10` | | | | | | | | |

**End of plan 11.**