---
name: audit-findings
description: Phase 11 - Supply Chain - VALIDATED findings (validator run)
phase: 11-supply-chain
executor: validator
template: .kilo/commands/audit/phases/99-audit-validate.md
source: .ai/audit/11-supply-chain/findings.md
status: complete
validated: yes
problems-only: true
---

# Phase 11 Validated Findings — Supply Chain

**Executor:** validator
**Source report:** `.ai/audit/11-supply-chain/findings.md` — opened **read-only**, unmodified
**Source handbook:** `.kilo/commands/audit/phases/11-audit-supply-chain.md`
**Validated artifact:** this file

**Deviation, stated once.** The report format
(`.ai/audit/templates/audit-findings.md`) has **no slot** for a validation decision: its
finding block runs from the heading straight into a nine-field table, and none of the nine
carries a decision. This phase defines the `Validation Note` block and requires it on every
decided finding; the block is written immediately below each `### {ID}:` heading, ahead of
the field table, until the format gains the slot. **This is a defect of the format, owned by
the validation phase, not of the report under validation.**

**The source report's own pre-answered sections were removed**, per block (i): its
`## Summary` severity table, `## Mandatory Fixes`, `## Advisory Recommendations` and
`## Doc Updates Needed` restate decisions and severities this phase re-derives. Every
finding's original content is retained verbatim below its decision record. The
`## Documented skips` and the cross-phase de-duplication record are **retained in full**:
they are the evidence that specific checks were not performed, and suppressing them would
manufacture a clean result on exactly the rows that must not be manufactured.

---

## Scope and corpus position

| Property | Value |
|---|---|
| Phase range validated | `11` only (the file this run was given) |
| Findings in scope | 16 — `DEP-001` … `DEP-016` |
| Phase that owns the `DEP-` prefix | 11 (supply chain) only |
| Prefix collisions | none — no other live phase prefix begins `DE` |
| Findings file | present, 16 findings, handbook present |
| Decision tally | Validated 16 · Reclassified 0 · Merged 0 · Rejected 0 · `VAL-` filed 0 |

**Tree state, re-established by this run, not inherited.** `HEAD = a335b2a`.
`git diff --name-only HEAD -- pyproject.toml uv.lock .gitignore .github/` returns **zero
lines**, so every manifest, lock and gate anchor in this report is byte-identical at `HEAD`
and in the working tree. The only tracked source files carrying uncommitted edits are
`src/vkdownloader/cli.py` and `src/vkdownloader/config.py` (a concurrent agent's work,
untouched by this run). No file was modified, added or removed by this validation; all
scratch went to `.temp/`, which `.gitignore:40` and `pyproject.toml:70` both exclude.

---

## Checkpoint 1 — R1 Copy Source Findings

- **Stage:** R1 Copy Source Findings
- **Findings in scope:** 16 (Validated 0, Reclassified 0, Merged 0, Rejected 0 — decisions
  taken at R3)
- **Evidence anchor:** this file, self-contained — every finding's original text is retained
  below its decision record. The source report was opened read-only and is unmodified.
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 2 — R2 Cross-Finding Analysis

- **Stage:** R2 Cross-Finding Analysis
- **Findings in scope:** 16 (Validated 0, Reclassified 0, Merged 0, Rejected 0)
- **Cross-phase conflicts:** 0 — no two phases assert incompatible facts about any subject
  this phase checked. The one cross-phase pair that is *the same* claim, `TST-005`/`DEP-002`,
  is a duplicate, not a conflict; see the de-duplication ruling below.
- **Merge candidates:** 1 — `TST-005` / `DEP-002`, already recorded as `VAL-125` by phase
  10's validator and **ratified here**.
- **Genuine complements retained, not merged:** 2 — `TST-007`/`DEP-001` (absent lint jobs vs
  the absent behavioural-suite step: different gate steps, independently fixable);
  `DEP-004`/`DEP-012` (inert ignore *rules* vs index-tracked *files*: different subjects,
  one shared edit).
- **Evidence anchor:** `.ai/audit/99-validation/10-test-coverage-validated-findings.md`
  (`VAL-125` at its line 2193, retained in this file's de-duplication ruling);
  `.github/workflows/packaging-check.yml:51-53`
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 3 — R3 Validate Each Finding

- **Stage:** R3 Validate Each Finding
- **Findings in scope:** 16 (**Validated 16, Reclassified 0, Merged 0, Rejected 0**)
- **Severities re-derived:** 16 of 16; **0 changed** (3 HIGH, 10 MEDIUM, 3 LOW confirmed).
  A decision never changes a severity; each severity below was composed from this run's own
  verification and the agreement with the filed value is reported, not inherited.
- **Reproduced end-to-end by direct command:** `DEP-001`, `DEP-002`, `DEP-003`, `DEP-004`,
  `DEP-005`, `DEP-006`, `DEP-007`, `DEP-008`, `DEP-009`, `DEP-010`, `DEP-011`, `DEP-012`,
  `DEP-013`, `DEP-014`, `DEP-015`, `DEP-016` — **16 of 16**.
- **Two enumerations drifted since the source run and are corrected in place** — `DEP-005`
  (four named paths → three) and `DEP-013` (six orphan names → six, but a different six).
  Both findings' subjects, root causes and consequences reproduce unchanged; only the
  current-tense file lists are corrected. **Neither is a rejection.**
- **Evidence anchor:** per-finding Validation Note below; the artifact each note names
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 4 — R4 Assess Rollout Safety

- **Stage:** R4 Assess Rollout Safety
- **Findings added by this phase:** **0** — no cross-phase conflict, no circular dependency,
  no hidden chain, and no rollout blocker was detected. A zero is written as a zero; no
  `VAL-` row is manufactured to fill the shape.
- **Unsafe-ordering constraints found: 3** (all one-way, none fatal; recorded in *Rollout
  ordering constraints* below):
  1. `DEP-001` + `DEP-002` + `TST-005` all insert into the **same step list** of the same
     53-line file. One commit, never three.
  2. `DEP-005` must land **before or with** any whole-tree form of `DEP-001`, or the lint
     gate turns the three `tmp/` scratch files into a red build.
  3. `DEP-004`'s rewrite must land **before** the `git check-ignore` step it recommends
     adding, or that step is red on arrival.
- **Circular dependencies:** 0. **Hidden dependency chains:** 0. **Fragile insertion
  points:** 0 — every recommendation anchors on a named file and a named construct
  (`EXPECTED_WHEEL_ENTRIES`, the `if self._stealth_path.exists():` guard, `check_ffmpeg_available()`,
  `[tool.hatch.build.targets.wheel] artifacts`).
- **Evidence anchor:** `.github/workflows/packaging-check.yml:37-53`; `.gitignore:1-66`;
  `tests/test_packaging.py:142-200`
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

---

## Findings

### DEP-001: Lint, format check and type check are documented as the project's verification and enforced by no automation

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** HIGH (unchanged) · **Type:** `SPEC-DEVIATION` (unchanged) · **Classification:** `mandatory` (unchanged)
> - **Detail:** Re-derived independently, and the enumeration is complete. A recursive
>   filesystem walk for `*.yml`/`*.yaml` outside `.venv/`, `.kilo/`, `.ai/`, `.temp/` returns
>   **exactly two files**, and `git ls-files .github` returns **the same two** — the directory
>   walk and the index-scoped listing agree, and `.github/` holds nothing else:
>   `workflows/doc-lint.yml`, `workflows/packaging-check.yml`. A separate check for every
>   other automation surface returns `exists=False` for all of: `.pre-commit-config.yaml`,
>   `tox.ini`, `noxfile.py`, `Makefile`, `package.json`, `.husky`, `Taskfile.yml`, `justfile`.
>   `git grep -c -I -E "ruff|mypy" -- .github` returns no matches. The **only** tracked
>   `run:` line naming any verification tool in the whole repository is
>   `packaging-check.yml:53`. The finding's evidence is sound and the defect is exact.
> - **Independently re-measured consequence** (the part that makes this HIGH rather than
>   theoretical): `uv run --no-sync ruff check src tests` → `All checks passed!` (exit 0);
>   `uv run --no-sync mypy src` → `Success: no issues found in 30 source files` (exit 0);
>   `uv run --no-sync mypy src tests` → `Found 55 errors in 6 files (checked 52 source
>   files)` (exit 1). `[tool.mypy]` is at `pyproject.toml:90` with `strict = true` at `:92`.
>   Nothing in the repository reports that 55-error result.
> - **The declaration the finding rests on is verified:** `.ai/context/commands.md:15-18`
>   states the four commands, and `docs/01-tools/installation.md:94-110` presents the same
>   three as the documented development workflow (`uv run ruff check src/` at `:97`,
>   `uv run ruff format --check src/` at `:103`, `uv run mypy src/` at `:109`).
> - **Correction to the evidence, immaterial to the finding:** the finding writes
>   "the filter is not the defect here" and that assessment is correct and confirmed —
>   `packaging-check.yml:12-30` admits `src/**`, `tests/**` and `pyproject.toml`. The
>   job *body* is the defect, exactly as filed.
> - **See also:** `DEP-002` (the same job's step list — see the de-duplication ruling and
>   `VAL-125`); `TST-007` (complement, not duplicate); `DEP-005` (becomes a red build the
>   moment the whole-tree form of the lint step lands).

| Field | Value |
|-------|-------|
| **ID** | DEP-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.github/workflows/**`, `pyproject.toml`, `.ai/context/commands.md`, `docs/01-tools/installation.md` |
| **Classification** | mandatory |

**Description (as filed, retained):** The project states four verification commands as its own bar — `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` — in `.ai/context/commands.md:15-18` and again as the documented development workflow in `docs/01-tools/installation.md:94-110`. All three tools are declared with configuration blocks the tools actually read (`[tool.ruff]` at `pyproject.toml:67`, `[tool.mypy]` at `pyproject.toml:90` with `strict = true` at line 92). The repository's complete automation set contains two definitions and neither runs any of them. `ruff check`, `ruff format --check` and `mypy` are invoked by nothing: no workflow, no hook file, no `tox`/`nox`/`make` target, no script. The only places the tool names appear outside their own configuration blocks are `.ai/context/commands.md`, `docs/01-tools/installation.md` and the agent command prompts under `.kilo/commands/` — none of which is an automation that runs.

The consequence is not hypothetical on this tree: `mypy` is configured `strict = true`, and `uv run mypy src tests` currently exits 1 with 55 errors in 6 files, every one of them in `tests/`. Nothing in the repository reports this. A commit that breaks a type contract in production code merges green.

**Evidence (as filed, retained):**

```
$ git ls-files .github
.github/workflows/doc-lint.yml
.github/workflows/packaging-check.yml

$ git grep -c -I -E "ruff|mypy" -- .github
(no matches)

$ uv run --no-sync mypy src
Success: no issues found in 30 source files
EXIT=0

$ uv run --no-sync mypy src tests
Found 55 errors in 6 files (checked 52 source files)
EXIT=1
```

| Class | Present | Evidence |
|---|---|---|
| Lint | **absent** | no `ruff` invocation in any definition |
| Format check | **absent** | no `ruff format` invocation in any definition |
| Type check | **absent** | no `mypy` invocation in any definition |
| Dependency scan | **absent** | see `DEP-003` |
| Secret scan | **absent** | see `DEP-003` |
| Lockfile check | present | `packaging-check.yml:51` `uv sync --locked` |
| Build and publish | partial (build-only) | see `DEP-015` |

**Recommendation (as filed, retained, confirmed sound):** Add one job — or one step in the existing `packaging-check` job — that runs `uv run ruff check src tests`, `uv run ruff format --check src tests` and `uv run mypy src` on the path filter that already covers `src/**`, `tests/**` and `pyproject.toml`, failing the build on a non-zero exit of any of the three. Type-check `src` first: it is the gate that is currently green and worth protecting, and folding `tests` in (55 errors) into the same change would fail every PR until those are cleared separately. No new tool is needed — all three are already declared, already configured, and already run cleanly.

---

### DEP-002: No job in the repository executes the test suite; the only pytest invocation collects 14 of 502 tests

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** HIGH (unchanged) · **Type:** `SPEC-DEVIATION` (unchanged) · **Classification:** `mandatory` (unchanged)
> - **Detail:** Reproduced by running the exact CI command and the exact collection count
>   this run, on the same interpreter the workflow pins:
>   `uv run --no-sync pytest tests/test_packaging.py -v` → `14 passed`, **exit 0**;
>   `uv run --no-sync pytest -q --collect-only` → **`502 tests collected`**;
>   `uv run --no-sync pytest -q -rs` → `498 passed, 4 skipped`, **exit 0**. The arithmetic
>   holds exactly: 502 collected, 14 of them run by the only pytest invocation in the
>   repository, **488 never executed by any automation**. `doc-lint.yml` runs one `grep` and
>   nothing else — confirmed by reading all 26 lines.
> - **The "under 3% of the tree" framing is confirmed and the trap it names is real:** the
>   workflow's path filter (`:19`, `:29`) admits `tests/**`, so a change to the test tree
>   *looks* gated while running one module of the tree.
> - **The four non-product tests are confirmed present** at
>   `tests/test_packaging.py:529` (`test_a_build_failure_that_is_not_a_network_error_fails_everywhere`),
>   and the two string constants they consume are at `:525-526`
>   (`NETWORK_BUILD_ERROR = "error: failed to fetch https://pypi.org/simple/hatchling/"`,
>   `NON_NETWORK_BUILD_ERROR = "error: Invalid distribution: no README"`). They call
>   `_build_failure_outcome()` with hardcoded strings and exercise no product code.
> - **Scope discipline confirmed:** this finding files the *absence of the class from the
>   catalogue*, and it says so explicitly. It makes no claim about what the 502 tests prove.
>   That is phase 10's subject and this phase does not reach it.
> - **No double-listing of the permission oracle:** the recommendation's one sentence about
>   the 4 skips names them as Windows-`chmod` subjects and notes the runner is
>   `ubuntu-latest`. That is a note about CI signal visibility, **not** a filing. Phase 07's
>   `ART-007` carries the file-permission guarantee and phase 10's `TST-013` carries the
>   platform-neutrality of those oracles. This finding files neither, and the skips
>   re-measure at exactly the four sites the source names (`tests/test_config.py:337`, `:353`,
>   `tests/test_hls_downloader.py:533`, `:678`).
> - **See also:** **`VAL-125` — this finding and phase 10's `TST-005` are one defect.** The
>   de-duplication ruling is recorded in full below. `DEP-001` shares the insertion point.

| Field | Value |
|-------|-------|
| **ID** | DEP-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.github/workflows/packaging-check.yml` |
| **Classification** | mandatory |

**Description (as filed, retained):** R9's job-class enumeration requires recording, against the catalogue of recognised classes, which exist and which do not. This finding files the **absence of the class from the catalogue** and the shape of the one job that touches the test tree. It files nothing about whether the tests prove anything — that is phase 10's, cited here and not merged.

`packaging-check.yml:53` runs `uv run pytest tests/test_packaging.py -v`. That path is a single module. The full suite collected 502 tests when re-measured here. The consequence: 488 collected tests are never executed by any automation in this repository, and a regression in any of them merges green. A change to `tests/**` is admitted by the workflow's path filter and therefore *looks* gated while running under 3% of the tree.

**Evidence (as filed, retained, re-run here):**

```
$ uv run --no-sync pytest tests/test_packaging.py -v
collected 14 items
14 passed in 2.32s
EXIT=0

$ uv run --no-sync pytest -q --collect-only
502 tests collected

$ uv run --no-sync pytest -q -rs
498 passed, 4 skipped in 27.14s
EXIT=0
```

**Recommendation (as filed, retained, confirmed sound):** Add `uv run pytest tests/` as a step in the existing `packaging-check` job, or as a separate `tests` job on the same path filter. Both `src/**` and `tests/**` are already in the filter, so no trigger change is required. The 4 skips are Windows-`chmod` subjects and the runner is `ubuntu-latest`, so they will not fire there; running with `-rs` in CI makes any runner-dependent skip visible in the log rather than silent. Keep the existing `test_packaging.py` step — it is a real artifact gate, not a substitute for the behavioural suite.

---

### DEP-003: No dependency scanner, no secret scanner, no update automation, no pre-commit control and no ownership file are configured anywhere in the repository

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `BEST-PRACTICE` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** Both halves of R10(a) were re-run, not accepted. **Path check:** every
>   recognised configuration returns `exists=False` — `.pre-commit-config.yaml`,
>   `.github/dependabot.yml`, `.github/CODEOWNERS`, `.github/renovate.json`, `renovate.json`,
>   `.github/workflows/dependency-review.yml`, `.github/workflows/codeql.yml`,
>   `.github/workflows/security.yml`. **Name grep:** `git ls-files` filtered on
>   `pre-commit|dependabot|renovate|CODEOWNERS|gitleaks|trufflehog|detect-secrets|pip-audit|osv|trivy|grype|syft|sbom|cyclonedx|spdx`
>   returns no matches. A per-tool `git grep -c -I -i -F` over tracked files (excluding
>   `uv.lock`, `.kilo/`, `.ai/`) returns **files=0 for all 16 tools** — `pre-commit`,
>   `gitleaks`, `trufflehog`, `detect-secrets`, `pip-audit`, `osv-scanner`, `dependabot`,
>   `renovate`, `trivy`, `grype`, `syft`, `CODEOWNERS`, `cyclonedx`, `sbom`, `hatch-audit`,
>   `uv audit`. The `safety` discard as a false positive on the English word is sound and is
>   re-confirmed by inspection of the 10 hits (documentation prose, no class implies it).
> - **The "12 open-ended lower bounds" claim in the recommendation is confirmed exactly:**
>   a parse of every quoted requirement string in `pyproject.toml` finds **12 declared
>   requirements, 12 of them open-ended `>=` with no ceiling** — 8 runtime (`:19-28`) and
>   4 dev (`:111-115`).
> - **The clean counterpart was re-verified rather than assumed, and it is clean:** a
>   high-precision committed-secret sweep over the project's own tracked files (81 files,
>   excluding `.ai/` and `.kilo/`) across nine patterns — PEM private-key block, `AKIA…`,
>   `gh[pousr]_…`, `sk-…`, `xox[baprs]-…`, `AIza…`, a three-segment JWT, an assigned
>   `secret|token|password|key = "…"` of 12+ characters, and a `pypi-…` token — returns
>   **0 hits on every pattern**. There is no committed material for a scanner to find today;
>   the finding is correctly filed against the *absence of the control*, never against
>   absence of material. (The source's denominator of 167 tracked files was taken before the
>   audit corpus grew; the numerator is what matters and it is 0 either way.)
> - **Type adjudication:** `BEST-PRACTICE` is the correct label. An unconfigured control is a
>   defensible arrangement with a demonstrated gap, not a contradiction of a declared rule —
>   `SPEC-DEVIATION` would be wrong here. `advisory` is correct: no correctness, security or
>   data-loss consequence attaches to a control being absent on a 41-package project.
> - **Scope discipline confirmed:** the finding proposes `dependabot.yml` for the `uv`
>   ecosystem and an advisory-scan step. It does not file a package-manager preference, a
>   "could be newer" observation, or a speculative upgrade. Correct.
> - **See also:** `DEP-006` (the second half of the same coverage question: a rule that stops
>   covering a path is this phase's finding; a scanner that would notice its loss is the
>   control that is also absent).

| Field | Value |
|-------|-------|
| **ID** | DEP-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.github/**`, `.pre-commit-config.yaml` (absent), `.github/dependabot.yml` (absent), `.github/CODEOWNERS` (absent) |
| **Classification** | advisory |

**Description (as filed, retained):** R10(a) requires path-checking each recognised configuration for each scanning, update-automation, ownership and pre-commit class and separately grepping tracked files for the tool names each class implies. Both were run. Five classes are configured nowhere and nothing runs them. The declared dependency surface is 8 runtime distributions and 4 development ones, resolved to 41 locked packages, none of which any control inspects for a known vulnerability and none of which any automation proposes an update for.

This is filed against the *absence of a control*, never against the absence of material — the committed-material sweep is a separate row and it returned zero (recorded as a measurement, not a finding; see the documented-skips section for the advisory-database skip that pairs with this finding).

| Class | Configured | Run by |
|---|---|---|
| Dependency vulnerability scan | no | nothing |
| Secret scan | no | nothing |
| Dependency-update automation | no | nothing |
| Pre-commit | no | nothing |
| Ownership (`CODEOWNERS`) | no | nothing |

**Recommendation (as filed, retained, confirmed sound):** Two additions carry most of the value and neither is an enterprise pattern. First, `.github/dependabot.yml` with `package-ecosystem: "uv"` — it is a 6-line file, it runs on GitHub's schedule, and it turns the 12 open-ended lower bounds in `pyproject.toml` into reviewed update PRs instead of silent drift. Second, a `uv run` step using an advisory scanner over `uv.lock` in the existing `packaging-check` job, so a known-vulnerable transitive resolution fails the same build that already asserts the artifact composition. Add `.pre-commit-config.yaml` only if the team wants a local pre-flight — the CI gate from `DEP-001` is the higher-leverage half and needs no new configuration file at all.

---

### DEP-004: Seven root debris entries are index-tracked and the ignore rules that claim to exclude them are inert literal patterns

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** HIGH (unchanged) · **Type:** `SPEC-DEVIATION` (unchanged) · **Classification:** `mandatory` (unchanged)
> - **Detail:** **Reproduced end-to-end, all seven rules, plus the eighth.** This is the
>   report's most technical claim and it holds exactly. The mechanism, the positive control,
>   the seven failures, the eighth case, and the stated consequence were each re-derived by
>   this run from `git check-ignore` directly, not from the finding's wording.
>
>   **Positive control first** — the mechanism works, so a later miss is the rule's fault
>   and not the tool's:
>   ```
>   $ git check-ignore -v -- urls.txt
>   .gitignore:46:urls.txt        urls.txt
>   ```
>
>   **All seven bare names match nothing** (`git check-ignore -q` returns non-zero for
>   every one):
>   ```
>   NOT-IGNORED: %PYFILE%
>   NOT-IGNORED: Continue
>   NOT-IGNORED: Continue=SilentlyContinue
>   NOT-IGNORED: ErrorPreference=SilentlyContinue
>   NOT-IGNORED: cli_ruff_output.txt
>   NOT-IGNORED: temp_tests_output.txt
>   NOT-IGNORED: stage_and_commit.bat
>   ```
>
>   **The proof that each line is a literal pattern** — feeding each rule line back to
>   `git check-ignore -v` verbatim, git reports that line as the source rule for that
>   literal string, which can only happen if it is parsing the whole line as one pattern:
>   ```
>   .gitignore:59:%PYFILE%                    # empty file left by an unexpanded %PYFILE% variable
>   .gitignore:60:Continue                    # PowerShell pipeline fragment: `Continue` with no argument
>   .gitignore:61:Continue=SilentlyContinue   # PowerShell pipeline fragment
>   .gitignore:62:ErrorPreference=SilentlyContinue  # PowerShell pipeline fragment
>   .gitignore:63:cli_ruff_output.txt         # captured ruff output
>   .gitignore:64:temp_tests_output.txt       # captured test output
>   .gitignore:65:stage_and_commit.bat        # one-off staging script
>   .gitignore:66:Shows/                      # empty directory left behind by a stray shell command
>   ```
>   All eight lines are confirmed: the reported defect is the `#`-on-the-pattern-line
>   mechanism, present on every line the finding names, and on the eighth it names as well.
>
>   **The stated consequence is real.** `git ls-files` filtered to root-level paths returns
>   **13** entries; 6 are the project (`pyproject.toml`, `uv.lock`, `README.md`,
>   `.gitignore`, `.python-version`, `.env.example`) and **7 are the debris**. Each of the
>   seven is confirmed index-tracked and its byte size matches the filed table exactly
>   (97 / 0 / 0 / 0 / 1078 / 3336 / 1342 B). Because none is ignored, `git rm --cached` on
>   any of them would leave it untracked-**and**-unexcluded, immediately committable — the
>   exact failure the prose at `.gitignore:56-58` claims to prevent, six lines above the
>   rules that fail to prevent it.
> - **One citation correction, immaterial to the finding.** The finding describes
>   `.gitignore:66` as `Show/` and reports `Test-Path Show -> False`. The line is `Shows/`
>   and the probe was of a name that never existed. The substantive claim is unaffected and
>   is in fact confirmed: `Test-Path Shows` is also `False`, `git check-ignore -q -- Shows`
>   also returns non-ignored, and line 66 is also a literal pattern. The finding's own
>   wording — "a tenth case of the same shape" — is correct.
> - **The negative control the filing leans on is also confirmed:** `.gitignore:34`
>   `!/.env.example` is the file's one negation, it is anchored, and it behaves correctly —
>   `git check-ignore -v -- .env.example` reports no match, which is the intended
>   re-admission. The defect is confined to lines 59-66.
> - **Type adjudication:** `SPEC-DEVIATION` is exactly right, and is the correct label here
>   rather than a convenience. The intent prose and the adjacent rule contradict each other
>   **in the same file, six lines apart**. `mandatory` is right: the configuration performs
>   none of the work it is on the page to perform.
> - **Scope discipline confirmed:** the finding correctly records that none of the seven
>   reaches a built artifact, and does not treat that as exculpatory. Re-verified — the
>   sdist's 73 members contain none of them and the wheel's 35 entries contain none of them;
>   `tests/test_packaging.py:191-200` independently pins all seven names in
>   `FORBIDDEN_SDIST_ENTRIES`. The exposure is the index and every future commit.
> - **See also:** `DEP-012` (the *files* rather than the *rules* — different subject, one
>   shared edit; see the rollout constraints), `DEP-005` (the mirror-image case: paths
>   nothing names at all).

| Field | Value |
|-------|-------|
| **ID** | DEP-004 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.gitignore`, `%PYFILE%`, `Continue`, `Continue=SilentlyContinue`, `ErrorPreference=SilentlyContinue`, `cli_ruff_output.txt`, `temp_tests_output.txt`, `stage_and_commit.bat` |
| **Classification** | mandatory |

**Description (as filed, retained):** `.gitignore:56-58` states the intent in prose: *"Root debris from earlier tool runs. None of it is part of the project; every entry below is currently tracked and is listed so the reason is recorded here and so the files cannot come back once they are untracked."* Each of the seven entries at `.gitignore:59-65` puts a `#` comment **on the same line as the pattern**. Git starts a comment only when `#` is the first character of a line, so each of those lines is one literal pattern whose text includes the comment. The rules do not exclude the files they name; they exclude filenames that do not exist and never will. The stated purpose — that the files "cannot come back once they are untracked" — is not performed by the configuration, so `git rm --cached` on any of them followed by one `git status` would show them as untracked-and-unexcluded, ready to be committed again.

This is filed as `SPEC-DEVIATION`: the comment is a statement of intent that the adjacent line contradicts, in the same file, six lines apart.

**Recommendation (as filed, retained, confirmed sound):** Put each `#` comment on its own line above its pattern, then `git rm --cached` the seven tracked files. The rewrite is mechanical:

```
# empty file left by an unexpanded %PYFILE% variable
%PYFILE%
# PowerShell pipeline fragment: `Continue` with no argument
Continue
...
```

After the rewrite, `git check-ignore -q -- cli_ruff_output.txt` must return 0; that is the one-line check that proves the fix landed, and it is worth adding to the packaging check because the regression is silent — the rules are wrong today and nothing reports it. **(Ordering note added by this phase: that check is red on arrival until the rewrite lands. See rollout constraint 3.)**

---

### DEP-005: Four untracked-and-unexcluded scratch paths sit at the repository root and already break the project's own whole-tree verification command

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `SPEC-DEVIATION` (unchanged) · **Classification:** `mandatory` (unchanged)
> - **Detail:** **The class and the consequence both reproduce; one of the four named paths
>   no longer exists.** The tree moved between the source run and this one, so the finding's
>   enumeration is corrected here rather than the finding being treated as stale. Nothing
>   else in the finding changed.
>   - `Test-Path probe_tmp.py` → **False**. It is absent from
>     `git ls-files --others --exclude-standard`. The file has been deleted from the working
>     tree since the source run. **Three of the four remain**, and all three are still
>     untracked and still named by no repository-carried rule:
>     `tmp/click_result.txt`, `tmp/click_test.py`, `tmp/click_test2.py`.
>   - **The consequence is still observable, not hypothetical** — re-run now:
>     `uv run --no-sync ruff check .` → `Found 2 errors` in `tmp\click_test.py` and
>     `tmp\click_test2.py` (both `I001 Import block is un-sorted`), **exit 1**;
>     `uv run --no-sync ruff format --check .` → `2 files would be reformatted, 52 files
>     already formatted`, **exit 1**. Both counts are one lower than filed, because the
>     deleted file was one of the three linted. The exit status — the entire substance of
>     the finding — is unchanged.
>   - **The root cause is unchanged and is the part that matters.** `.gitignore` carries a
>     rule for each of the *neighbouring* paths — `.temp/` at `:40`, `urls.txt` at `:46`,
>     `*.mp4` at `:13` — and simply omits these. This is not a machine-local gap; the file
>     is in the repository and names the neighbourhood correctly.
>   - **The scoped form the project documents still passes**, confirming the diagnosis:
>     `uv run --no-sync ruff check src tests` → `All checks passed!` (exit 0), which is
>     exactly why a contributor has not noticed the whole-tree form is red.
> - **Type adjudication:** `SPEC-DEVIATION` and `mandatory` are both correct. A contributor
>   running the obvious whole-tree verification command receives a red result for files that
>   are not the project's, and the project declares `ruff` as its own verification tool.
>   That is a deviation from a declared rule with an observable failure today.
> - **See also:** `DEP-001` (the moment the lint gate lands in whole-tree form, this becomes
>   a red build — rollout constraint 2), `DEP-004` (the mirror-image case), `DEP-012` (the
>   tracked script that would stage these three into the index).

| Field | Value |
|-------|-------|
| **ID** | DEP-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `probe_tmp.py` *(deleted since the source run)*, `tmp/click_result.txt`, `tmp/click_test.py`, `tmp/click_test2.py`, `.gitignore` |
| **Classification** | mandatory |

**Description (as filed, retained, enumeration corrected in the note above):** R12 records three states as three — tracked-and-ignored, untracked-and-ignored, untracked-and-unexcluded — and the third is the one to characterise. Four paths are in it. They are excluded by no repository-carried rule, by no nested ignore file, and by no rule held outside the repository: nothing names them. The exclusion sources for the neighbouring paths in the same neighbourhood *are* carried (`.gitignore:40` for `.temp/`, `.gitignore:46` for `urls.txt`, `.gitignore:13` for `*.mp4`), so this is not a machine-local configuration gap — the rules are present and simply omit these four.

The consequence is already observable, not hypothetical. `ruff` discovers them:

```
$ uv run --no-sync ruff check .
I001 [*] Import block is un-sorted or un-formatted
  --> tmp\click_test.py:1:1
I001 [*] Import block is un-sorted or un-formatted
  --> tmp\click_test2.py:1:1
Found 2 errors.
[*] 2 fixable with the `--fix` option.
EXIT=1

$ uv run --no-sync ruff format --check .
Would reformat: tmp\click_test.py
Would reformat: tmp\click_test2.py
2 files would be reformatted, 52 files already formatted
EXIT=1
```

The scoped form the project documents (`docs/01-tools/installation.md:97,103` — `uv run ruff check src/`) still passes, which is why nothing has noticed. A contributor who runs the obvious whole-tree invocation gets a red result for files that are not the project's. The second path to the same files is `stage_and_commit.bat:5`, which runs `git add -A` — see `DEP-012`.

**Recommendation (as filed, retained, confirmed sound):** Add one rule to `.gitignore` next to the existing scratch entries at line 40 — `/tmp/` and `/probe_tmp.py` — then delete the four files. Two lines, no build-configuration change, and it removes the only reason `uv run ruff check .` currently exits 1. Once `DEP-001` adds the lint gate, this rule is what stops the gate from being the thing that discovers the next stray file.

---

### DEP-006: Two exclusions depend on a nested ignore file the repository does not carry

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `BEST-PRACTICE` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** Reproduced exactly, including the asymmetry the finding turns on.
>   `.kilo/.gitignore` exists, is 8 lines long, and is **untracked** (absent from
>   `git ls-files`). It lists **itself** at line 7 (` .gitignore`) and `agent-manager.json`
>   at line 8 — so a contributor who has never run the agent tooling never has it, which is
>   precisely the exposure being filed. `git check-ignore -v` on all four agent paths:
>   ```
>   .kilo/agent-manager.json  <-  .kilo/.gitignore:8:agent-manager.json   .kilo/agent-manager.json
>   .kilo/.gitignore          <-  .kilo/.gitignore:7:.gitignore           .kilo/.gitignore
>   .kilo/node_modules        <-  .kilo/.gitignore:1:node_modules         .kilo/node_modules
>   .kilo/worktrees           <-  .gitignore:49:.kilo/worktrees/          .kilo/worktrees
>   ```
>   The asymmetry is visible in the output exactly as filed: `worktrees` resolves to the
>   **tracked** root `.gitignore` at line 49, the other two resolve to the **untracked**
>   nested file at lines 7 and 8. `node_modules` is covered by both, so the root comment's
>   claim for it holds — the finding says so and so does this run.
> - **The maintainer's own reasoning for the root file is verified verbatim** at
>   `.gitignore:51-53`: *"Ignored here as well as in .kilo/.gitignore because the build
>   backend reads this file, not the nested one, when it selects the files to package."*
>   Two entries were missed in exactly that block. The finding's framing — the rule set is
>   correct, it is incompletely carried — is right.
> - **Scope discipline confirmed and honoured.** The finding declares that
>   `agent-manager.json`'s *contents* are not its subject and only its *coverage* is. This
>   run did not read that file's contents either. The only property this phase asserts about
>   it is the one the finding asserts: it exists, it is untracked, and its exclusion depends
>   on an untracked file.
> - **Type adjudication:** `BEST-PRACTICE` is correct — the nested file is right for what it
>   does and the fix is additive, not corrective. `advisory` is correct: on a single-contributor
>   project the practical consequence is two agent-tooling paths appearing as ordinary
>   untracked files in a clean checkout, with no security, data-loss or correctness
>   consequence. Filing it as mandatory would overstate it; the finding does not.
> - **See also:** `DEP-003` (a rule that stops covering a path is this phase's finding; a
>   scanner that would notice its loss is the control that is also absent).

| Field | Value |
|-------|-------|
| **ID** | DEP-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.kilo/.gitignore`, `.kilo/agent-manager.json`, `.gitignore` |
| **Classification** | advisory |

**Description (as filed, retained):** R4 requires recording every exclusion that depends on a file the repository does not carry, because such an exclusion protects exactly one machine: a clean checkout has no `.kilo/.gitignore`, so the two paths it excludes become ordinary untracked files there. `.gitignore:48-54` shows the maintainer already reasoned about this seam for two neighbouring paths — *"Ignored here as well as in .kilo/.gitignore because the build backend reads this file, not the nested one, when it selects the files to package"* — and carried `.kilo/worktrees/` and `.kilo/node_modules/` in the root file for that reason. Two entries were missed: `.kilo/agent-manager.json` and `.kilo/.gitignore` itself.

`agent-manager.json` is a live file on this machine, and its top-level keys are agent-manager session state, one key of which is named for sessions. The file's contents are **not** a subject of this phase; the *coverage* is.

**Recommendation (as filed, retained, confirmed sound):** Add the two missing names to the root `.gitignore`, in the block that already exists for this reason:

```
# Agent worktrees: each holds a complete second copy of src/vkdownloader/.
.kilo/worktrees/
.kilo/agent-manager.json
.kilo/.gitignore
```

Keep the nested file — it is correct for what it does and there is no reason to remove it. The change is additive, three lines, and it makes the root file match the intent its own comment already states. It is also the second half of the coverage question `DEP-003` files: a rule that stops covering a path is this phase's finding, and a scanner that would notice its loss is the control that is also absent. Neither is present today.

---

### DEP-007: The test tree imports `annotated_types`, which no declaration mechanism names

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `SPEC-DEVIATION` (unchanged) · **Classification:** `mandatory` (unchanged)
> - **Detail:** The finding was produced by an AST-based import scan; this run performed an
>   **independent** scan of `src/` and `tests/` (every `.py`, `__pycache__` excluded) and
>   reduced every `import X` / `from X import` to its top-level name. The result agrees on
>   the finding and, importantly, on every row of its reachability table:
>
>   | Declared name | Reached in `src/` | Reached in `tests/` | Verdict |
>   |---|---|---|---|
>   | `playwright` | 6 files | 3 files | reachable |
>   | `aiohttp` | 2 files | 0 | reachable |
>   | `pydantic` | 4 files | 1 file | reachable |
>   | `pydantic_settings` | 1 file | 0 | reachable |
>   | `typer` | 2 files | 1 file | reachable |
>   | `rich` | 1 file | 2 files | reachable |
>   | `structlog` | 16 files | 0 | reachable |
>   | `yt_dlp` | 1 file | 1 file | reachable |
>   | `ruff` / `mypy` | configured blocks only | — | reachable as tools |
>   | `pytest` | — | 18 files | reachable |
>   | `pytest-asyncio` | — | 174 `asyncio` marker / fixture references across `tests/` | reachable as a plugin |
>
>   **Every declared runtime and development dependency is reached by a real import or by the
>   construct that consumes it. Nothing is declared and unreachable.** The only top-level
>   third-party import in either tree that no declaration mechanism names is
>   `annotated_types`, at exactly `tests/test_config.py:472`:
>   `from annotated_types import Ge, Le`. Confirmed present at that line, inside
>   `test_max_retries_bounds_derived_from_field_metadata`, which uses `Ge` and `Le` to read
>   the declared constraints off `Settings.model_fields["max_retries"]`.
> - **Duplication and conflicting-bounds rows, both empty, confirmed by parsing the manifest
>   rather than reading it:** 12 declared requirements, **each declared exactly once** —
>   `[project.dependencies]` at `:19-28` holds 8, `[dependency-groups].dev` at `:111-115`
>   holds 4, `[build-system] requires` at `:34` holds `hatchling` (build-time only), and
>   `[project.optional-dependencies]` is **absent**. No name is declared by two mechanisms;
>   no two mechanisms give one name different bounds.
> - **The lock side is confirmed:** `annotated-types` is present in `uv.lock` only as a
>   transitive entry of `pydantic`, and the built wheel's `METADATA` carries exactly
>   **8 `Requires-Dist` lines and no `Provides-Extra`**, so the extras question has no
>   duplicate to report. The finding's claim that the import resolves today only because
>   `pydantic` declares it is correct.
> - **Type adjudication:** `SPEC-DEVIATION` and `mandatory` are correct. The consequence is
>   a correctness one: if `pydantic` ever drops, renames or vendors that dependency without
>   a major version bump, the suite fails at import with a `ModuleNotFoundError` whose cause
>   is invisible in this repository's manifest.
> - **One citation correction in the cross-phase section, immaterial to the finding:** the
>   report writes that `yt_dlp` is "reached at `src/vkdownloader/services/extractor.py:7` and
>   `src/vkdownloader/services/ytdlp_downloader.py`". The import is at `extractor.py:7` only.
>   `ytdlp_downloader.py` contains `yt_dlp` solely inside **log-event name string literals**
>   (`"yt_dlp_download_cancelled"` at `:388`, `:410`, `:687`, `:716`; `"yt_dlp_cancel_not_clean"`
>   at `:642`, `:720`) — no import. The evidence table's own row (`1 file` in `src`) is
>   correct; only the prose overstates it. The declared-dependency angle is unaffected:
>   `yt_dlp` is declared at `pyproject.toml:27` and reached.
> - **See also:** phase 09's `QLT-009` (`yt_dlp` is the sole dependency invisible to the
>   mypy profile) — the same import, a different concern; cited, not re-filed.

| Field | Value |
|-------|-------|
| **ID** | DEP-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_config.py:472`, `pyproject.toml:110-116` |
| **Classification** | mandatory |

**Description (as filed, retained):** R5 asks, for each name the manifest declares, whether anything reaches it; and the converse question is the one that produced this finding. An AST-based import scan of the two production and test trees found exactly one top-level module that is imported and is named by no declaration mechanism anywhere in `pyproject.toml`. `tests/test_config.py:472` does `from annotated_types import Ge, Le` inside a test. `annotated-types` is not in `[project.dependencies]` (8 names) and not in `[dependency-groups].dev` (4 names). It resolves today only because `pydantic>=2.0.0` declares it, so the name is present in `uv.lock` and the import succeeds.

The consequence is a correctness one: if `pydantic` ever drops, renames or vendors that dependency — which its own maintainers may do without a major version bump — the suite fails at import with a `ModuleNotFoundError` whose cause is invisible in this repository's manifest. Nothing here records that the test tree depends on it.

| Mechanism | `pyproject.toml` | Names and bounds |
|---|---|---|
| `[project.dependencies]` | lines 19-28 | `playwright>=1.45.0`, `aiohttp>=3.9.0`, `pydantic>=2.0.0`, `pydantic_settings>=2.0.0`, `typer>=0.12.0`, `rich>=14.0.0`, `structlog>=24.0.0`, `yt-dlp>=2024.0.0` |
| `[dependency-groups].dev` | lines 110-116 | `ruff>=0.4.0`, `mypy>=1.10.0`, `pytest>=8.0.0`, `pytest-asyncio>=0.23.0` |
| `[project.optional-dependencies]` | absent | — |
| `[tool.hatch.build.targets.*]` | lines 37-65 | names paths, not distributions |
| `[build-system] requires` | lines 33-35 | `hatchling` (unbounded, build-time only) |
| `uv.lock` | — | 41 packages, 40 registry-sourced, 1 editable |

**Recommendation (as filed, retained, confirmed sound):** `uv add --dev annotated-types` (or, if the maintainer prefers to keep the dev group minimal, import the constrained types from `pydantic` instead — the test needs the operator types, not the package). One line either way; the point is that the test tree's real dependency set becomes visible in the manifest instead of being inherited by accident.

---

### DEP-008: Neither built artifact carries a PEP 561 marker, so the published package's types are invisible to every consumer

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `SPEC-DEVIATION` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** **Rebuilt both artifacts from the working tree into a gitignored scratch
>   directory** (`.temp/dist/`, excluded by `.gitignore:40` and `pyproject.toml:70`; no build
>   residue entered the index) and enumerated them directly.
>   - Wheel: **35 entries** — `vkdownloader/*` **31**, `vkdownloader-0.1.0.dist-info/*`
>     **4**. `vkdownloader/stealth.min.js` is present at **2 608 bytes**, exactly as filed.
>     **`py.typed` is absent from the central directory**: the name matches **0** of the 35
>     entries.
>   - Source tree and index: `git ls-files | Select-String "py.typed"` → no matches;
>     `Test-Path src\vkdownloader\py.typed` → **False**. Absent everywhere, in all three
>     places it could have been.
>   - `[tool.hatch.build.targets.wheel]` at `:37-44` declares `packages` and `artifacts`;
>     **neither names a marker, and neither is a mechanism that could add one** — a PEP 561
>     marker must exist as a file inside the package directory. The finding's reasoning is
>     correct and is confirmed by the build, not inferred from the manifest.
> - **The interaction with the existing artifact gate is confirmed by reading the gate, not
>   by assumption.** `tests/test_packaging.py:146-180` is
>   `EXPECTED_WHEEL_ENTRIES = frozenset({…})` and its 31 members are exactly the 31
>   `vkdownloader/*` names the built wheel carries. Adding the marker therefore **will** fail
>   `test_wheel_entry_set_matches_the_manifest` until `"vkdownloader/py.typed"` is added to
>   that frozenset. The gate is working as designed; the finding says so, and the change is
>   correctly scoped as two lines across the manifest and the test.
> - **Type adjudication:** `SPEC-DEVIATION` is the right label, not merely a convenient one.
>   The project pays the full cost of static typing — every module annotated, `strict = true`
>   at `pyproject.toml:92`, `uv run --no-sync mypy src` re-measured at `Success: no issues
>   found in 30 source files` (exit 0) — and ships none of the benefit. Code and the
>   project's own declared typing discipline contradict each other at the artifact boundary.
>   `advisory` classification is correct: a downstream consumer running mypy treats the
>   package as untyped and skips it, which is a real but non-correcting consequence for a
>   single-developer CLI.
> - **Scope discipline confirmed:** the finding does not become an opinion about type-checker
>   choice, does not file a `basedpyright` preference, and does not re-derive phase 09's mypy
>   profile subject.
> - **See also:** `DEP-009` (a second, independent change to the same pinned artifact sets —
>   rollout constraint 4), phase 09's `QLT-009` (the producer-side typing policy; cited, not
>   re-filed).

| Field | Value |
|-------|-------|
| **ID** | DEP-008 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/`, `pyproject.toml:37-44` |
| **Classification** | advisory |

**Description (as filed, retained):** R2 requires recording, from the source tree, whether a typed-distribution marker exists at all. It does not. The package is fully annotated and is type-checked under `strict = true` (`pyproject.toml:92`) with `mypy src` exiting 0 across all 30 source files. None of that reaches an installer, because PEP 561 requires an empty `py.typed` marker file inside the package, and neither the working tree nor the wheel contains one.

The consequence is at the consumer's end: after `pip install vkdownloader`, a downstream project running mypy treats every `vkdownloader` import as untyped and skips it, so the annotations the project maintains at real cost deliver nothing. Under `--strict` the same import surfaces as `import-untyped` and, with `warn_unused_ignores` on the consumer's side, produces a second class of noise. The project pays the full typing cost and ships none of the benefit.

Note the interaction with the existing artifact gate: `tests/test_packaging.py:146-180` pins the wheel's entry set to an exact `frozenset`, so adding the marker will fail `test_wheel_entry_set_matches_the_manifest` until `"vkdownloader/py.typed"` is added to `EXPECTED_WHEEL_ENTRIES`. That is the gate working as designed; the change is two lines across the manifest and the test.

**Evidence (as filed, retained, rebuilt here):**

```
$ git ls-files | Select-String "py.typed"
(no matches)
$ Test-Path src\vkdownloader\py.typed
False

built wheel: 35 entries; vkdownloader/* = 31; py.typed present in 0 of them
```

**Recommendation (as filed, retained, confirmed sound):** Create an empty `src/vkdownloader/py.typed` and add the two lines the gate needs: `"vkdownloader/py.typed"` in `EXPECTED_WHEEL_ENTRIES` (`tests/test_packaging.py:146-180`) and nothing in the manifest, because `packages = ["src/vkdownloader"]` already admits any file inside the package directory, which `tests/test_packaging.py:142-145` already documents. Verify with the existing job: `uv run pytest tests/test_packaging.py -v` must stay at 14 passed. **(Re-measured at 14 passed, exit 0, on the current tree — so the target state is exactly today's state plus the marker.)**

---

### DEP-009: Both artifacts assert an MIT licence and ship no licence text

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `SPEC-DEVIATION` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** Confirmed against the artifacts this run rebuilt, not against the manifest
>   alone. The wheel's `METADATA` header carries **`License-Expression: MIT`** and
>   **`License-File` appears nowhere in the block** — searched case-insensitively over the
>   whole metadata, absent. The wheel's `.dist-info` holds **exactly 4 entries**
>   (`METADATA` 6 257 B, `WHEEL` 87 B, `entry_points.txt` 54 B, `RECORD` 3 117 B), none of
>   which is a licence. The sdist's **73 members** contain no licence file either — probed
>   on `/licen[cs]e|copying|notice` across all 73 names, **no match**.
>   `pyproject.toml:7` `license = "MIT"` and `:15` the `License :: OSI Approved :: MIT
>   License` classifier are both present and both reach the metadata.
> - **The exclusion is confirmed complete.** `git ls-files` filtered on
>   `(?i)licen|copying|notice` returns exactly three paths, all third-party licence files
>   belonging to bundled agent skills under `.kilo/skills/`
>   (`agent-md-refactor/LICENSE`, `artifacts-builder/LICENSE`,
>   `artifacts-builder/LICENSE.txt`). None is this project's, and `.kilo/` is a
>   `FORBIDDEN_SDIST_PREFIXES` entry at `tests/test_packaging.py:188`, so none can serve.
>   There is no fourth candidate hiding anywhere.
> - **The sdist's 73-file composition is confirmed file-for-file**, which is the evidence
>   the other findings cite for "this does not reach the archive":
>   `.env.example` 1, `.gitignore` 1, `.python-version` 1, `PKG-INFO` 1, `README.md` 1,
>   `pyproject.toml` 1, `uv.lock` 1, `docs` **13**, `src` **31**, `tests` **22** — total 73.
>   **No licence file among them**, and none can be added without an `include` entry at
>   `pyproject.toml:52-65`, which `test_sdist_entry_set_matches_the_manifest` pins exactly.
> - **Scope discipline confirmed, and it is the sharpest thing about this finding.** The
>   report states in its own words that *"the licence claim itself is not the subject and is
>   not filed"*, and files only that a publishable artifact carries a licence assertion with
>   nothing behind it. That is the correct boundary: this phase validates the artifact's
>   internal coherence, and licence posture as such is expressly not one of its subjects. The
>   finding does not moralise about the licence chosen, does not recommend a different one,
>   and does not assert a legal conclusion.
> - **The recommendation's PEP 639 detail is correct and its secondary advice is sound:**
>   `license-files` is the key that makes the builder emit `License-File` and have hatchling
>   add the file to the sdist, and dropping the classifier is the right call for a manifest
>   that already carries `License-Expression` under PEP 639. Both are additive and are
>   picked up by the existing packaging test with the two expected-set additions it demands.
> - **See also:** `DEP-008` (a second, independent change to the same pinned artifact sets).

| Field | Value |
|-------|-------|
| **ID** | DEP-009 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `pyproject.toml:7`, `pyproject.toml:15`, `LICENSE` (absent) |
| **Classification** | advisory |

**Description (as filed, retained):** `pyproject.toml:7` declares `license = "MIT"` and `pyproject.toml:15` adds the trove classifier `License :: OSI Approved :: MIT License`. Both assertions reach the metadata of both built artifacts. No licence text reaches either. Per this phase's scope the *licence claim itself* is not the subject and is not filed; the subject is that a publishable artifact carries a licence assertion with nothing behind it.

The consequence is at the distribution end. PEP 639 separates the SPDX expression (what the metadata asserts) from the licence file (what a redistributor needs in order to comply), and the builder emits a `License-File` entry only when it can find a licence file to point at. It finds none, so the metadata has `License-Expression: MIT` and no `License-File` at all. An index listing shows MIT; a downloader that mirrors, vendors or re-licences the package has nothing to reproduce and no notice obligation it can discharge.

**Evidence (as filed, retained, re-derived from a fresh build):**

```
Metadata-Version: 2.5
Name: vkdownloader
Version: 0.1.0
License-Expression: MIT
Classifier: License :: OSI Approved :: MIT License
Requires-Python: >=3.12
Requires-Dist: aiohttp>=3.9.0
Requires-Dist: playwright>=1.45.0
Requires-Dist: pydantic-settings>=2.0.0
Requires-Dist: pydantic>=2.0.0
Requires-Dist: rich>=14.0.0
Requires-Dist: structlog>=24.0.0
Requires-Dist: typer>=0.12.0
Requires-Dist: yt-dlp>=2024.0.0
Description-Content-Type: text/markdown

License-File:  ABSENT
licence text in the wheel:  NONE
licence text in the sdist:  NONE
```

**Recommendation (as filed, retained, confirmed sound):** Add a `LICENSE` file at the repository root with the MIT text and point the manifest at it using the PEP 639 `license-files` key. The builder will then emit a `License-File` entry and hatchling will add the file to the sdist automatically; both changes are picked up by the existing packaging test with the two expected-set additions it already demands. While doing it, delete the now-redundant `License :: OSI Approved :: MIT License` classifier at `pyproject.toml:15` — PEP 639 tooling treats the classifier as a deprecated duplicate of the `License-Expression` field and some index validators warn on having both.

---

### DEP-010: The one runtime data file the product loads is declared in both build targets; its loss is reported at no log level

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `BEST-PRACTICE` (unchanged) · **Classification:** `mandatory` (unchanged)
> - **Detail:** The finding splits the question into a *declaration* half and an
>   *observability* half, files only the second, and both halves were re-derived.
>   - **Declaration half — satisfied, and correctly not filed.** The path is derived at
>     `src/vkdownloader/infrastructure/browser.py:32`:
>     `self._stealth_path = Path(__file__).parent.parent / "stealth.min.js"`. It is named in
>     `[tool.hatch.build.targets.wheel].artifacts` at `pyproject.toml:44` and in the sdist
>     `include` list at `pyproject.toml:55`. **Both built artifacts carry it** — the rebuilt
>     wheel has `vkdownloader/stealth.min.js` at **2 608 bytes** and the rebuilt sdist carries
>     it under its `src` tree. The manifest's own comment at `:41-42` ("it must ship in both
>     artefacts") is honoured. This half of the question is clean and is written down as
>     such inside the finding rather than being padded into a defect.
>   - **Observability half — the filed defect, confirmed by reading the load site:**
>     ```
>     112:        if self._stealth_path.exists():
>     113:            await page.add_init_script(path=str(self._stealth_path))
>     114:            logger.debug("stealth_script_applied")
>     115:
>     116:        return page
>     ```
>     An `if …exists():` with **no `else`**. The only log line naming the script is
>     `logger.debug` at `:114`, on the **taken** branch. When the file is absent the product
>     proceeds to launch a page with no anti-automation masking, at the default log level,
>     with **nothing written at any level**. The exact consequence — the download proceeds,
>     the CDN's automation detection starts rejecting the request, and the operator sees a
>     generic extraction failure with no line anywhere saying the masking script did not
>     load — is stated precisely and is not inflated.
>   - **The finding's cited precedent for the fix is real and is the right one:**
>     `src/vkdownloader/services/ffmpeg_utils.py:81-88` logs `logger.warning("ffmpeg_not_found",
>     hint=…)` for exactly this shape of event — an external capability silently absent. The
>     recommendation is to add the `else` at `browser.py:112` logging a `warning`, so the
>     failure mode becomes visible in the same log stream as the rest of the run. Four lines,
>     no new dependency, and the `exists()` guard correctly stays: making the file optional
>     at runtime is a reasonable design choice, and the finding's point is that it should be
>     a *stated* choice rather than an invisible one.
> - **Type adjudication:** `BEST-PRACTICE` is correct. The code is not wrong — it degrades
>   safely by design — and the gap is a missing diagnostic where a defensible arrangement
>   has a demonstrable blind spot. `mandatory` is correct and is the stronger of the two
>   claims: an installed product that silently loses a required capability produces an
>   operator-visible failure with no diagnostic anywhere, and the manifest asserts the file
>   "must ship in both artefacts" while nothing defends the assertion at runtime.
> - **The "only `__file__`-derived runtime read" claim is confirmed:** the only other
>   `__file__` use in `src/` is `src/vkdownloader/utils/security.py:65`, which computes a
>   repository root for a path-safety warning and reads nothing.
> - **See also:** `DEP-008` (a second, independent change to the same pinned artifact sets).

| Field | Value |
|-------|-------|
| **ID** | DEP-010 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py:32,112-114` |
| **Classification** | mandatory |

**Description (as filed, retained):** `src/vkdownloader/infrastructure/browser.py:32` derives a path from the module's own location — `Path(__file__).parent.parent / "stealth.min.js"` — and `:112-113` reads it when `create_stealth_page` runs. This is the only file the installed product reads by a path derived from its own location.

The **declaration** half of this question is satisfied and is not filed: `pyproject.toml:44` names it in `[tool.hatch.build.targets.wheel].artifacts`, `pyproject.toml:55` names it in the sdist `include` list, and the built artifacts carry it at `vkdownloader/stealth.min.js` (2 608 bytes) and `src/vkdownloader/stealth.min.js` respectively.

The **observability** half is not. The guard is `if self._stealth_path.exists():` and the `else`-equivalent is nothing: no `else` branch, no `warning`, no `error`. The only log line in `create_stealth_page` that mentions the script is `logger.debug("stealth_script_applied")` at line 114, which fires on the *present* path. When the file is absent the product proceeds to launch a page with no anti-automation masking, at default log level, with nothing written anywhere. The consequence is a silent capability downgrade: the download proceeds, the CDN's automation detection starts rejecting the request, and the operator sees a generic extraction failure with no line anywhere saying the masking script did not load.

**Recommendation (as filed, retained, confirmed sound):** Add an `else` that logs the absence at `warning` — the level `config.py`'s logger already uses for comparable degradations such as `ffmpeg_not_found` (`src/vkdownloader/services/ffmpeg_utils.py:81-88` logs `warning` for exactly this shape of event). One branch, four lines, and the failure mode becomes visible in the same log stream as the rest of the run. The `exists()` guard should stay: the file being optional at runtime is a reasonable design choice, but it should be a *stated* choice rather than an invisible one.

---

### DEP-011: The ffmpeg binary is discovered at runtime with no version constraint recorded anywhere in the repository

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `BEST-PRACTICE` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** The claim is a **negative** one — "no version constraint is recorded
>   anywhere" — and a negative was verified by exhausting every place such a constraint could
>   live, not by accepting the report's word.
>   - The product's entire declaration of what it needs from the binary is
>     `src/vkdownloader/services/ffmpeg_utils.py:80`:
>     `_ffmpeg_available = shutil.which("ffmpeg") is not None`. **Presence, never version** —
>     confirmed by reading the function.
>   - No version floor exists in `pyproject.toml` (parsed: 12 requirements, none naming
>     `ffmpeg` or any binary), in either workflow (read in full), or in `tests/` (no
>     `ffmpeg` version constant; the test files reference the function, not a version).
>   - The documentation prescribes install commands with no version, all confirmed by line:
>     `docs/01-tools/installation.md:32` `choco install ffmpeg`, `:37` `brew install ffmpeg`,
>     `:42` `sudo apt-get install ffmpeg`. The only verification offered is `:47`
>     `ffmpeg -version` — a command whose **output nothing compares against**, confirmed by
>     the absence of any comparison in the repository.
>   - The finding's grep result is confirmed: the only `-version` / `version_info` /
>     `shutil.which` hits in `src/` are the `ffmpeg_utils.py:69` docstring line and the
>     `:80` call itself. The docstring explains the *caching* of the check, not any version
>     requirement.
>   - The second instance is also confirmed: `docs/01-tools/installation.md:74` prescribes
>     `playwright install chromium` unpinned, against `playwright>=1.45.0` at
>     `pyproject.toml:20` with **no ceiling** — the resolved lock currently pins
>     `playwright 1.61.0`, so the browser build that gets installed is whatever the resolver
>     picked on the day of the sync.
>   - The `ffprobe` row is confirmed by absence: `git grep -F "ffprobe" -- src tests` returns
>     **no match** (exit 1). Nothing in the product or the suite references it.
> - **Scope discipline — the most important property of this finding, and it is honoured.**
>   The finding explicitly declines to re-derive the runtime failure, names phase 05's
>   `TRN-001` as the owner, and files only the pinning policy: the observation that made a
>   capability shippable against an unbounded external tool without recording which builds
>   are trustworthy. **This phase did not re-derive the argfile behaviour and does not
>   assert it.** The boundary is drawn in the right place: the declared-dependency angle is
>   this phase's, the runtime observation is phase 05's.
> - **One correction to the cross-phase reference, immaterial to the finding:** the report
>   describes `TRN-001` as CRITICAL. Phase 05's **validated** report records it at **HIGH**
>   (reclassified, re-derived by that run). The subject, the boundary and the validity of
>   the cross-reference are unaffected; the severity label is corrected here so the corpus
>   does not carry two severities for one ID.
> - **Type adjudication:** `BEST-PRACTICE` and `advisory` are both correct. The product is
>   not wrong; it works on a large fraction of real ffmpeg builds. The gap is a missing
>  record, and the consequence the finding names is a *user-visible warning*, not a refusal
>   to run — which is the right bar for a CLI that should not lock a user out of an older
>   distro build.
> - **Scope discipline beyond the required:** the finding files no "ffmpeg is out of date",
>   no "playwright should be pinned to X", and no preference for a different package
>   manager. It records an absence of record-keeping, which is a real and bounded claim.

| Field | Value |
|-------|-------|
| **ID** | DEP-011 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py:66-89`, `docs/01-tools/installation.md:26-48`, `README.md:112` |
| **Classification** | advisory |

**Description (as filed, retained):** R7's question — is anything invoked, and is the rule set the project does use already covering the named tool's function — has an external-binary arm that the declaration mechanisms cannot express. `ffmpeg` is not a distribution; it is a native binary the product discovers on `PATH` and executes. The product's entire declaration of what it needs from that binary is the following:

```python
# src/vkdownloader/services/ffmpeg_utils.py
80:        _ffmpeg_available = shutil.which("ffmpeg") is not None
```

Presence, never version. No minimum version is recorded in `pyproject.toml`, in `docs/`, in `README.md`, in the CI workflow, or in a test. The documentation prescribes install commands (`choco install ffmpeg`, `brew install ffmpeg`, `apt-get install ffmpeg` — `docs/01-tools/installation.md:32,37,42`) with no version, and the only verification offered is `ffmpeg -version` at line 47, whose output nothing compares against.

A second instance of the same shape: the Playwright browser binaries. `docs/01-tools/installation.md:74` prescribes `playwright install chromium`, unpinned; the `playwright` distribution is declared at `pyproject.toml:20` with `>=1.45.0` and no ceiling, so the browser build that gets installed is whatever the resolver picked on the day of the sync.

| Subject | Declaration in `pyproject.toml` | Version constraint recorded | Enforced by |
|---|---|---|---|
| `ffmpeg` (native binary) | none possible | **none** | nothing |
| Playwright browser build | transitively, via `playwright>=1.45.0` (line 20) | distribution floor only, no ceiling | nothing |
| `ffprobe` | none | none | nothing — and no `ffprobe` reference exists in `src/` or `tests/` at all |

R6's projection does not change this: `uv sync --dry-run` exits 0 with "Would make no changes" — re-measured by this run, exit 0, `Resolved 41 packages`, `Found up-to-date lockfile at: uv.lock`, `Audited 41 packages`, `Would make no changes`. The Python-side default provisioning path is sound. The gap is entirely on the native-binary side, which no Python manifest can close.

**Recommendation (as filed, retained, confirmed sound):** Record the constraint where a developer will meet it, not in code. Add one line to `docs/01-tools/installation.md`'s ffmpeg section stating the minimum build the product is verified against (derived from the `N-117624` behaviour phase 05 recorded, plus whatever the argfile path needs), and turn the existing `ffmpeg -version` check at line 47 into a check that compares. For a CLI, a `--version`-style preflight that warns when the discovered binary is older than the recorded floor costs about ten lines in `ffmpeg_utils.py` next to `check_ffmpeg_available()` and converts an entire class of silent downgrade into a visible warning. This is deliberately not a hard failure: a user on an older distro build should get a clear message, not a refusal to run.

---

### DEP-012: Seven index-tracked files at the repository root are read by no tool, and one of them runs `git add -A`

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** LOW (unchanged) · **Type:** `BEST-PRACTICE` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** Every one of the seven was located in the index, its size measured, and its
>   content read by this run — not accepted from the table.
>   `git ls-files` filtered to root-level paths returns **13**: the 6 the finding names as
>   the project (`pyproject.toml`, `uv.lock`, `README.md`, `.gitignore`, `.python-version`,
>   `.env.example`) and 7 it names as debris. All seven confirmed **index-tracked**, with
>   sizes matching the filed table exactly — `%PYFILE%` 97 B, `Continue` 0 B,
>   `Continue=SilentlyContinue` 0 B, `ErrorPreference=SilentlyContinue` 0 B,
>   `cli_ruff_output.txt` 1 078 B, `temp_tests_output.txt` 3 336 B,
>   `stage_and_commit.bat` 1 342 B.
>   - `%PYFILE%` read in full: a two-line append-to-file Python script
>     (`with open(sys.argv[1], 'a', encoding='utf-8') as f: f.write(sys.argv[2])`), left
>     behind by an unexpanded shell variable. With no `.py` name it is inert to the import
>     system — confirmed.
>   - `cli_ruff_output.txt` read: captured ruff output naming `cli_test.py` / `cli_test2.py`,
>     **files that no longer exist** in the tree.
>   - `temp_tests_output.txt` read: captured pytest output whose last line is
>     `325 passed in 12.75s`. The suite is now **502 collected / 498 passed / 4 skipped**, so
>     the count is stale exactly as filed.
>   - `stage_and_commit.bat` read — **this is the one that is not inert, and the claim holds:**
>     ```
>     1: @echo off
>     2: cd /d C:\py_exp\mko_vkideo
>     4: echo Step 1: Stage all changes
>     5: git add -A
>     ```
>     `git add -A` stages every untracked-and-unexcluded path in the working tree, and
>     `DEP-005` established that such paths exist right now. The script also hardcodes one
>     contributor's absolute checkout path and its 30-line commit message describes a
>     refactor that has long since landed — a one-off artifact, not a maintained tool.
> - **The "no tool reads any of them" claim is confirmed** and the archive claim with it:
>   the sdist's 73 members contain none of the seven, and `tests/test_packaging.py:191-200`
>   pins all seven names in `FORBIDDEN_SDIST_ENTRIES` (`stage_and_commit.bat` at `:193`,
>   `cli_ruff_output.txt` at `:194`, `temp_tests_output.txt` at `:195`, `%PYFILE%` at `:196`,
>   `Continue` at `:197`, `Continue=SilentlyContinue` at `:198`,
>   `ErrorPreference=SilentlyContinue` at `:199`) — every name verified at its line. The
>   sdist allow-list at `pyproject.toml:52-65` is the mechanism keeping them out and it is
>   working.
> - **One citation nit, immaterial:** the finding quotes `stage_and_commit.bat:3-6`; the
>   `cd /d` line is line **2**. The quoted content is otherwise verbatim and the line is
>   the 5th, not within a 3-6 window that would change the meaning.
> - **Type and severity adjudication:** `BEST-PRACTICE` / `advisory` / **LOW** are all
>   correct. Six of the seven are pure index hygiene with no behaviour. The seventh
>   (`stage_and_commit.bat`) has a real consequence, but it requires a person to run it by
>   hand, and the harm is bounded: the files it would stage are already excluded by
>   `FORBIDDEN_SDIST_ENTRIES` from reaching any published artifact. LOW is the right weight.
> - **See also:** `DEP-004` (the *rules* meant to describe these files; one shared edit — see
>   rollout constraint 4), `DEP-005` (the three untracked paths this script would stage).

| Field | Value |
|-------|-------|
| **ID** | DEP-012 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `%PYFILE%`, `Continue`, `Continue=SilentlyContinue`, `ErrorPreference=SilentlyContinue`, `cli_ruff_output.txt`, `temp_tests_output.txt`, `stage_and_commit.bat` |
| **Classification** | advisory |

**Description (as filed, retained):** R12 requires every index-tracked entry no tool reads to be identified with its content read. `git ls-files` filtered to root-level entries returns 13 paths; six of them are the project and seven are not. Each was read in full. None is referenced by any tracked file, none is imported, and none is a Python module — `%PYFILE%` is a script body with a `.py` script's content and no `.py` name, so it is inert to the import system.

The seventh is not inert in the same way. `stage_and_commit.bat` runs `git add -A`. `git add -A` stages every untracked-and-unexcluded path in the working tree. `DEP-005` established that such paths exist right now. A contributor who runs this tracked script commits all of them. The script also hardcodes one contributor's absolute checkout path, and its 30-line commit message describes a refactor that has long since landed — it is a one-off artifact, not a maintained tool.

| File | Size | What it is |
|---|---|---|
| `%PYFILE%` | 97 B | a 2-line append-to-file Python script, left by an unexpanded shell variable |
| `Continue` | 0 B | empty; a PowerShell pipeline fragment |
| `Continue=SilentlyContinue` | 0 B | empty; a PowerShell pipeline fragment |
| `ErrorPreference=SilentlyContinue` | 0 B | empty; a PowerShell pipeline fragment |
| `cli_ruff_output.txt` | 1 078 B | captured ruff output naming `cli_test.py` / `cli_test2.py`, files that no longer exist |
| `temp_tests_output.txt` | 3 336 B | captured pytest output, ending `325 passed in 12.75s` — a stale count |
| `stage_and_commit.bat` | 1 342 B | one-off `git add -A` + `git commit` script with a hardcoded absolute path |

Per-candidate ignore verdict: **none of the seven is named by any working ignore rule** — see `DEP-004`, which files the mechanism and the proof.

Did any reach the built source archive? **No.** The 73-file enumeration lists every member; none of the seven is among them, and `tests/test_packaging.py:191-200` independently pins all seven names in `FORBIDDEN_SDIST_ENTRIES`. The sdist allow-list at `pyproject.toml:52-65` is the mechanism that keeps them out, and it is working.

**Recommendation (as filed, retained, confirmed sound):** Delete all seven from the index and the working tree — `git rm --cached` plus a local delete — as part of the `DEP-004` fix, which already rewrites the rules meant to describe them. `stage_and_commit.bat` is the one to prioritise: it is the mechanism by which the `DEP-005` scratch files would enter the index, and it has no reason to exist in a repository. No tool reads any of them, so removal is behaviour-free; the only change is that a stale `325 passed` count and a one-contributor absolute path stop living in the project's history.

---

### DEP-013: Compiled bytecode for six deleted module names survives in the source and test trees, in two coexisting cache generations

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** LOW (unchanged) · **Type:** `BEST-PRACTICE` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** The compiled-file census re-derives exactly: **77** `.pyc` files under
>   `src/` and `tests/`, excluding `.venv/` and `node_modules/`. The repository-root
>   `__pycache__/` exists and holds **3** files — `main.cpython-312.pyc`,
>   `test_script.cpython-312-pytest-9.0.3.pyc`, `_test.cpython-312-pytest-9.0.3.pyc` — with no
>   `.py` beside any of them, matching the filed row.
>   **The two coexisting cache generations are confirmed:** both `cpython-312-pytest-9.0.3`
>   and `cpython-312-pytest-9.1.1` files sit in `tests/__pycache__` and
>   `tests/integration/__pycache__`. The plugin version changed between runs and neither
>   generation was cleared — so a cleanup that clears one leaves the other, and the class
>   survives the fix. That is the finding's actual claim and it holds.
> - **The orphan enumeration has drifted, and is corrected here rather than treated as
>   staleness.** Diffing cache basenames against the source basenames beside them, the
>   orphan set under `src/` + `tests/` is now **six** names — the five the report names
>   (`adaptive_throttle`, `http_client`, `test_http_client`, `test_smoke_resume`,
>   `test_mock_vk_server`) plus **one new one: `test_probe_tmp`**, left behind by the
>   deletion of the scratch probe. `test_http_client` now carries **both** generations
>   (`9.0.3` and `9.1.1`); the report listed only `9.0.3`. The class, the root cause, the
>   two-generation observation and the operational conclusion are all unchanged; only the
>   current file list moved, and it moved in the direction the finding predicts.
> - **The "already covered, and that is why this is LOW" reasoning is confirmed and is the
>   right call.** `.gitignore:2` declares `__pycache__/` and `.gitignore:3` declares
>   `*.py[oc]`, so every one of the 77 files is untracked *and* ignored — `git ls-files
>   --others --ignored --exclude-standard` lists the `__pycache__` directories under `!!`.
>   Neither built artifact contains any: the wheel's 35 entries have none and the sdist's 73
>   members have none (the `include` allow-list at `pyproject.toml:52-65` admits directories
>   but hatchling excludes `__pycache__` by default — **confirmed empirically by the
>   enumeration, not by assumption**, which is the standard the report sets for itself and
>   meets). CPython will not import a `__pycache__/*.pyc` whose source is absent, so the
>   files are inert at runtime as well as at build time.
> - **Type and severity adjudication:** `BEST-PRACTICE` / `advisory` / **LOW** are correct,
>   and the finding's own operational judgement — *"worth doing once and not worth a rule: the
>   ignore coverage is already correct, so this is a one-time tidy, not a gate that should be
>   added"* — is the right answer for this class. It explicitly declines to recommend a
>   new rule where the existing rules already work, which is precisely the discipline this
>   phase is asked to enforce. It also correctly diagnoses the likely recurrence cause as a
>   pytest upgrade in the environment rather than a repository defect.

| Field | Value |
|-------|-------|
| **ID** | DEP-013 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/__pycache__/`, `tests/__pycache__/`, `__pycache__/` (repository root) |
| **Classification** | advisory |

**Description (as filed, retained, enumeration corrected in the note above):** R13 diffs the module-name set derived from compiled cache files against the source basenames. Six names have no source beside them, and two cache generations coexist, so a cleanup that clears one leaves the other and the class survives the fix.

| Orphaned name | Cache file | Nearest existing source |
|---|---|---|
| `adaptive_throttle` | `src/vkdownloader/infrastructure/__pycache__/adaptive_throttle.cpython-312.pyc` | none — `infrastructure/` holds only `__init__.py`, `browser.py`, `network_monitor.py` |
| `http_client` | `src/vkdownloader/infrastructure/__pycache__/http_client.cpython-312.pyc` | none — same directory |
| `test_http_client` | `tests/__pycache__/test_http_client.cpython-312-pytest-9.0.3.pyc` | none — no `tests/test_http_client.py` |
| `test_smoke_resume` | `tests/__pycache__/test_smoke_resume.cpython-312-pytest-9.0.3.pyc` | none — no `tests/test_smoke_resume.py` |
| `test_mock_vk_server` | `tests/integration/__pycache__/test_mock_vk_server.cpython-312-pytest-9.0.3.pyc` and `-9.1.1.pyc` | none — `tests/integration/` holds only `__init__.py` |
| `_test`, `main`, `test_script` | `__pycache__/` at the repository root, 3 files | none — no such `.py` at the root |

Coexisting cache generations: `cpython-312-pytest-9.0.3` and `cpython-312-pytest-9.1.1` both sit in `tests/__pycache__` and in `tests/integration/__pycache__`. The plugin version changed between runs and neither generation was cleared. The repository-root `__pycache__` is a fourth location, holding bytecode for scripts that no longer exist at the root.

**Recommendation (as filed, retained, confirmed sound):** Delete the three `__pycache__` directories that no longer have a full set of sources under them — the repository-root one, and the two `tests/` ones that hold the 9.0.3 generation — or simply run `find . -name __pycache__ -type d -prune -exec rm -rf {} +` outside `.venv/`. Worth doing once and not worth a rule: the ignore coverage is already correct, so this is a one-time tidy, not a gate that should be added. If the two-generation split recurs regularly, the cause is a pytest upgrade in the environment rather than the repository, and nothing here needs to change.

---

### DEP-014: The shipped README and the installation guide both promise Python 3.10+ while the artifact they ship in requires 3.12

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `DOC-UPDATE` (unchanged) · **Classification:** `mandatory` (unchanged)
> - **Detail:** Both sides re-derived exactly, from the source documents and from a
>   freshly built artifact, and the contradiction is character-for-character as filed.
>   ```
>   pyproject.toml:6            requires-python = ">=3.12"
>   README.md:111               - Python 3.10+
>   docs/01-tools/installation.md:20   - Python 3.10 or higher
>   .python-version             3.12
>   built wheel METADATA        Requires-Python: >=3.12
                                Classifier: Programming Language :: Python :: 3
                                Classifier: Programming Language :: Python :: 3.12
   ```
>   The wheel's version classifier list corroborates the real floor independently of the
>   `requires-python` field: **`3.12` is the only version classifier present.** The
>   `.python-version` pin says `3.12`. All three agree, and two shipped documents disagree.
> - **The consequence is confirmed, not hypothetical, and its mechanism is specific.** The
>   same installation guide's step 2 (`docs/01-tools/installation.md:61-64`) offers
>   `pip install -e .` as the supported path — confirmed present at those lines, under
>   `### 2. Install Dependencies` at `:59`. On Python 3.10 or 3.11 that command fails at
>   **resolution** with a `Requires-Python` error, *after* the user has followed the
>   prerequisite check at `:18-22` and believed it passed. That ordering — a check that says
>   yes, followed by a failure that contradicts it — is what makes this more than a stale
>   number, and it is stated accurately.
> - **Both files ship in both artifacts, so the contradiction is reproduced to the
>   consumer.** `README.md` enters the sdist via `pyproject.toml:61` and the whole `docs`
>   tree via `pyproject.toml:57`; both include entries are confirmed at those lines, and
>   both files are present in the rebuilt 73-member sdist. `README.md` is additionally
>   embedded verbatim in the wheel's `METADATA` long description — `readme = "README.md"` at
>   `pyproject.toml:5` is confirmed, `Description-Content-Type: text/markdown` is confirmed
>   in the built metadata — so `pip show vkdownloader` and every index listing repeat
>   "Python 3.10+" to a user who will be rejected by the very same artifact.
> - **Type adjudication:** `DOC-UPDATE` is exactly right and is the correct label on both
>   available readings. The code is correct — `requires-python = ">=3.12"` matches the
>   language features the source uses, the `.python-version` pin, and the only classifier —
>   and two documents say otherwise. Nothing about this finding is a product defect; it is
>   documentation contradicting the artifact it ships inside. `mandatory` is correct
>   because the incorrect claim is inside the published artifact and produces a user-facing
>   resolution failure.
> - **The recommendation correctly refuses to choose the direction.** It offers the
>   two-character documentation fix *and* names the alternative — relax
>   `pyproject.toml:6` and re-verify — while stating plainly that the latter is a code
>   decision, not a documentation one, and that the `.python-version` pin and the single
>   `3.12` classifier both currently say 3.12. That is the right boundary for a validator to
>   hold.
> - **The secondary claim is also confirmed:** `README.md:113` reads
>   `- Playwright browsers (auto-installed)` and is inaccurate. `git grep -F "playwright
>   install"` over the repository returns **exactly one hit** — the manual step at
>   `docs/01-tools/installation.md:74` — and no code path in `src/` or `tests/` installs a
>   browser. The accurate wording is the one the installation guide already uses. Correctly
>   raised in the same pass rather than filed as a separate finding.
> - **See also:** phase 08 owns any structural description; this is a packaging/install
>   document claim and is this phase's, per its own boundary.

| Field | Value |
|-------|-------|
| **ID** | DEP-014 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `README.md:111`, `docs/01-tools/installation.md:20`, `pyproject.toml:6` |
| **Classification** | mandatory |

**Description (as filed, retained):** A document claim about packaging, provisioning, publication or installation is this phase's subject, and this one ships inside the wheel. `pyproject.toml:6` declares `requires-python = ">=3.12"`, and the built metadata carries `Requires-Python: >=3.12`. Two documents a user reads before installing tell them something different:

- `README.md:111` — this file is `readme = "README.md"` (`pyproject.toml:5`), so its `## Requirements` section is embedded verbatim in the wheel's `METADATA` long description, on the index listing and on `pip show vkdownloader`. It reads `- Python 3.10+`.
- `docs/01-tools/installation.md:20` — under `## Prerequisites`, it reads `- Python 3.10 or higher`.

The same installation guide's step 2 (`docs/01-tools/installation.md:61-64`) offers `pip install -e .` as the supported path. On Python 3.10 or 3.11 that command fails at resolution with a `Requires-Python` error, after the user has followed the guide's prerequisite check and believed it passed. The wheel's own classifier list corroborates the real floor — `Programming Language :: Python :: 3.12` is the only version classifier present.

**Recommendation (as filed, retained, confirmed sound):** Change both lines to `3.12` in the same commit. `README.md:111` becomes `- Python 3.12+` and `docs/01-tools/installation.md:20` becomes `- Python 3.12 or higher`. Two characters each. If the maintainer would rather support 3.10, the fix is the other direction — relax `pyproject.toml:6` and re-verify — but that is a code decision, not a documentation one, and the `.python-version` pin and the single `3.12` classifier both currently say 3.12. `README.md:113` ("Playwright browsers (auto-installed)") is worth a second look in the same pass: nothing in the codebase installs browsers automatically — a repository-wide search for `playwright install` returns exactly one hit, and it is the manual step at `docs/01-tools/installation.md:74` — so the accurate wording is the one the installation guide already uses.

---

### DEP-015: The gate set has a `release` trigger that produces and verifies no artifact, and no build-and-publish job exists

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** MEDIUM (unchanged) · **Type:** `BEST-PRACTICE` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** The workflow was read in full — all 53 lines — and every element the finding
>   cites is present at the cited line:
>   ```
>   31:  release:
>   32:    types: [published]                        <- fires after publication
>   34:  permissions:
>   35:    contents: read                            <- cannot publish
>   37:  jobs:
>   38:    packaging-check:
>   39:      runs-on: ubuntu-latest
>   41:      - uses: actions/checkout@v4
>   43:      - uses: astral-sh/setup-uv@v6
>   47:      - uses: actions/setup-python@v5
>   51:      - run: uv sync --locked
>   53:      - run: uv run pytest tests/test_packaging.py -v
>         no upload, no hash recording, no publish action
>   ```
>   The job genuinely builds both artifacts and asserts their composition — real, useful
>   work, and the finding says so rather than dismissing the existing job. But it uploads
>   nothing, records nothing about what it built, and verifies nothing about a *published*
>   artifact.
> - **The core defect is confirmed and stated with the right force.** `release: types:
>   [published]` fires **after** a human has already published a GitHub Release, so by the
>   time the job runs the release exists. It re-derives the answer from the released ref on
>   a different machine at a different moment and asserts only that the entry sets match.
>   `permissions: contents: read` at `:34-35` confirms the job is deliberately — and
>   correctly — unable to publish. **Nothing in the repository ties what an installer
>   downloads to what CI checked.** A release assembled and uploaded by hand from a working
>   tree whose uncommitted state is unknown, against a stale `uv.lock` or a different `uv`
>   version, produces a release the green check cannot detect. Each of those three failure
>   modes is concrete and none is speculative.
> - **The absence of publishing tooling is confirmed:** no `[project.urls]` in
>   `pyproject.toml` (read in full — absent), no `publish` table, no upload action in either
>   definition. `git grep -n -I -E "twine|hatch publish|uv publish|__token__|PYPI_|pypi.org"`
>   over the repository excluding the lockfile and agent tooling returns a single hit,
>   `tests/test_packaging.py:525` `NETWORK_BUILD_ERROR = "error: failed to fetch
>   https://pypi.org/simple/hatchling/"` — **a test fixture string, not a configuration.**
>   The finding identifies it correctly.
> - **Type and severity adjudication:** `BEST-PRACTICE` / `advisory` / **MEDIUM** are all
>   correct. The defect is a configuration state that gives false assurance — a green check
>   attesting to a rebuild rather than to an upload — which is worse than no check, and that
>   is a real consequence rather than a preference. It is `BEST-PRACTICE` rather than
>   `SPEC-DEVIATION` because no declared rule is contradicted: the project simply has not
>   said which of the two release models it wants.
> - **The recommendation is correctly framed as a decision, not a fix.** It presents the two
>   coherent states — "not published from CI, GitHub Release is the release" versus
>   "published to an index" — and labels option (a) two lines matching the project's current
>   state and option (b) a publishing decision that should be made deliberately. It does not
>   impose a release process, and it does not recommend a publishing tool by preference.
>   That is the right call: this phase can observe that the configuration is undecided, and
>   cannot decide it.

| Field | Value |
|-------|-------|
| **ID** | DEP-015 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.github/workflows/packaging-check.yml:31-32,50-53` |
| **Classification** | advisory |

**Description (as filed, retained):** R9's job-class list includes `build and publish`. Half of it exists. The job builds both artifacts and asserts their composition — genuinely useful work — but it does not upload anything, does not record what it built, and does not verify anything about a published artifact. The `release: types: [published]` trigger at line 31-32 fires *after* a human has already published a GitHub Release, which means by the time this job runs the release exists. It re-derives the answer from the released ref on a different machine at a different moment and asserts only that the entry sets match.

The consequence: nothing in the repository ties what an installer downloads to what CI checked. A release is assembled and uploaded by hand, from a working tree whose uncommitted state is unknown; the green check that accompanies the release attests to a rebuild, not to the upload. A `git status`-dirty tree, a stale `uv.lock`, or a different `uv` version on the uploader's machine all produce a release that the green check cannot detect. `permissions: contents: read` at line 34-35 confirms the job is deliberately unable to publish.

```
$ git grep -n -I -E "twine|hatch publish|uv publish|__token__|PYPI_|pypi.org" -- . ':!uv.lock' ':!.kilo'
tests/test_packaging.py:525:NETWORK_BUILD_ERROR = "error: failed to fetch https://pypi.org/simple/hatchling/"
```

The single hit is a test fixture string, not a configuration. There is no `[project.urls]`, no `publish` table and no upload action in either definition.

**Recommendation (as filed, retained, confirmed sound):** Decide which of two states the project wants, and make the configuration say so. Either (a) the package is not published from CI and the GitHub Release is the release — in which case drop the `release: types: [published]` trigger, because a check that fires after the fact and can act on nothing gives false assurance, and add a `steps` upload of the two built artifacts as CI artifacts so the exact bytes that were checked are retained; or (b) the package is published to an index, in which case add a `build` job that runs on tags, records `sha256sum` of both artifacts into the job summary, and publishes with trusted publishing so no long-lived token exists in the repository. Option (a) is two lines and matches the project's current state; option (b) is a publishing decision, not a configuration one, and should be made deliberately.

---

### DEP-016: The version is declared twice — in the manifest and in `__init__.py` — with nothing that keeps them equal

> **Validation Note:**
> - **Action:** validated
> - **Confirmed severity:** LOW (unchanged) · **Type:** `SPEC-DEVIATION` (unchanged) · **Classification:** `advisory` (unchanged)
> - **Detail:** Both declarations re-read at their cited lines and against a fresh build:
>   ```
>   pyproject.toml:3                     version = "0.1.0"
>   src/vkdownloader/__init__.py:3       __version__ = "0.1.0"
>   built wheel METADATA                 Version: 0.1.0
>   built wheel payload                  vkdownloader/__init__.py   118 bytes
>   ```
>   The `__init__.py` was read in full — a one-line docstring, a blank line, and
>   `__version__ = "0.1.0"` at line 3. The wheel ships that exact file, so the second copy is
>   not merely present in the source tree, it is **installed**. Two sources of truth, no
>   check between them, and `importlib.metadata.version("vkdownloader")` will report
>   whichever one the builder stamped.
> - **The documented verification step is confirmed and is what makes the duplication
>   user-visible.** `docs/01-tools/installation.md:150-157` is a `## Verification` section
>   whose first check is
>   ```python
>   from vkdownloader import __version__
>   print(f"VK Video Downloader version: {__version__}")
>   ```
>   — confirmed at lines 154-157. A user is instructed to read a value that nothing keeps in
>   sync with the manifest, immediately after installing.
> - **The "nothing compares them" claim is confirmed by reading the test, not by absence of
>   evidence.** `tests/test_packaging.py` is the packaging gate; a search of it for `version`
>   returns two hits and **neither is a comparison**: `:69` is the `".python-version"` entry
>   in the sdist file list, and `:142-143` is a comment about the versioned `.dist-info`
>   directory name. No test compares `__version__` against the parsed `pyproject.toml` value,
>   and no workflow does either.
> - **The two copies agree today. The finding is right that this is the state, not the
>   guarantee,** and it says so in those words. The consequence is stated precisely: the next
>   release bump updates one copy and the published package's own `__version__` reports the
>   previous release while `importlib.metadata.version` reports the new one. Two correct
>   answers from two sources.
> - **Type adjudication, recorded as the one arguable label in this report.** `SPEC-DEVIATION`
>   is defensible and is upheld, on the strength of one piece of evidence: the project's own
>   shipped documentation (`installation.md:154-157`) tells a user that the package attribute
>   is the thing to check, so a document and the code disagree about which copy is
>   authoritative. `BEST-PRACTICE` would also be defensible — duplicated constant. This phase
>   upholds `SPEC-DEVIATION` rather than reclassifying it, and records the alternative here
>   so a later run does not treat the label as settled beyond the evidence.
> - **Severity adjudication:** **LOW** is correct. The two copies agree at `0.1.0`, the
>   failure requires a release process to go wrong, and the symptom is a stale string in a
>   diagnostic print — not a broken install, not data loss, not a security consequence. The
>   finding does not inflate this, and neither does this note.
> - **Both remedies in the recommendation are sound** and the choice between them is left
>   where it belongs: derive the attribute from `importlib.metadata.version`, or keep it
>   dependency-free and add a one-line assertion in `tests/test_packaging.py`. Either turns
>   a silent drift into either a single source or a red build. The recommendation correctly
>   offers the choice rather than mandating a mechanism.

| Field | Value |
|-------|-------|
| **ID** | DEP-016 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/__init__.py:3`, `pyproject.toml:3`, `docs/01-tools/installation.md:154-157` |
| **Classification** | advisory |

**Description (as filed, retained):** The distribution version has two sources of truth and no check between them. `pyproject.toml:3` declares `version = "0.1.0"`, which is what the builder stamps into the wheel's `METADATA` and the sdist's `PKG-INFO`. `src/vkdownloader/__init__.py:3` hardcodes `__version__ = "0.1.0"`, which is a second, independent copy that ships as ordinary package code. `docs/01-tools/installation.md:154-157` documents exactly that attribute as the post-install verification step, so a user is told to check a value that nothing keeps in sync.

The consequence: the next release bump updates one copy and the published package's own `__version__` reports the previous release, while `importlib.metadata.version("vkdownloader")` reports the new one. Two correct answers from two sources is the failure mode; neither `tests/test_packaging.py` (which pins entry sets, not versions) nor any workflow compares them.

**Recommendation (as filed, retained, confirmed sound):** Delete `__version__` from `src/vkdownloader/__init__.py:3` and derive it — `__version__ = importlib.metadata.version("vkdownloader")` — so the manifest stays the single source and the documented verification step keeps working. This costs one import and removes a class of release-day error. If the project prefers the attribute to stay dependency-free, the alternative is a one-line assertion in `tests/test_packaging.py` comparing `__version__` against the parsed `pyproject.toml` value, which turns a silent drift into a red build.

---

## Cross-phase de-duplication ruling — `TST-005` and `DEP-002` are one defect

**This is the ruling phase 10's validator explicitly deferred to this run.** Its
`VAL-125` (`.ai/audit/99-validation/10-test-coverage-validated-findings.md:2193`) records
the merge candidate, designates `DEP-002` the absorbing ID, and states:

> *"**This run has not performed the merge**: it edits neither report, and phase 11's
> validation has not run, so the absorbing decision is recorded here for that run to ratify
> or overrule. **Do not land both fixes independently.**"*

**RATIFIED. `DEP-002` absorbs `TST-005`.** They are the same defect, and saying so plainly
rather than letting both stand in the corpus is the whole point of this ruling. The four
criteria for a same-root-cause merge, each re-derived from both reports rather than from
`VAL-125`'s characterisation:

| Merge criterion | `TST-005` (phase 10) | `DEP-002` (phase 11) | One? |
|---|---|---|---|
| Subject | `packaging-check.yml:53` — one module of 502 | `packaging-check.yml:53` — one module of 502 | **yes, the same line** |
| Cause | the job's only test step is a single-module run | the same | **yes** |
| Consequence | the suite's collected tests are executed by no automation | 488 of 502 never executed by any automation | **yes** |
| Remediation | add a full-suite step to that job's step list | add `uv run pytest tests/` to that job's step list | **yes, one change** |
| Insertion point | the two-line `- name:` / `run:` pair at the end of a 53-line job | the same two lines | **yes, a collision** |

Two fixes authored from two reports, applied from two worktrees, in either order, produce
two identical steps or a merge conflict at the same two lines of
`.github/workflows/packaging-check.yml`. That is not a complement; a complement has
different subjects and independently shippable fixes.

**One half of `VAL-125`'s stated premise no longer holds, and this is the substantive
update this run contributes.** `VAL-125` was filed because the two reports "classify it
differently". Phase 10's validator then reclassified `TST-005` from `BEST-PRACTICE` /
`advisory` to **`SPEC-DEVIATION` / `mandatory`** — which is exactly what `DEP-002` already
carried. **The classification disagreement is resolved; both sides now agree.** What
remains is a single defect stated twice with one remediation, which is the residual
`VAL-125` warned about and which this ruling discharges.

**The one element that must not be lost in the merge**, carried over from `VAL-125` and
confirmed still true: `TST-005` uniquely records that **no coverage measurement or
threshold is declared anywhere in the repository** — no coverage tool in
`[dependency-groups] dev` (4 names: `ruff`, `mypy`, `pytest`, `pytest-asyncio`; verified),
and no threshold in either workflow. That element belongs inside `DEP-002`.

**Neither report is edited by this phase.** This run was given phase 11's findings and
writes exactly one artifact; `.ai/audit/10-test-coverage/findings.md` and
`.ai/audit/99-validation/10-test-coverage-validated-findings.md` are read-only to it. The
merge is therefore **ratified and recorded, not executed** — and that is the correct
outcome, not a shortfall: the decision needed a validator to make it, and the edit needs
the owner of both files. **`TST-005` is marked absorbed. Do not land both fixes
independently.**

### Complements retained, not merged (recorded so a later run does not mistake them for duplicates)

| Pair | Why it is a complement, not a merge |
|---|---|
| `TST-007` / `DEP-001` | Different gate steps, independently fixable and independently valuable: the absent lint / format / type-check jobs versus the absent behavioural-suite step. Phase 10's validator classified this as a genuine complement and that assessment is upheld. **The shared-insertion-point risk between them is a rollout constraint, recorded below — not a merge.** |
| `DEP-004` / `DEP-012` | Different subjects: the *inert ignore rules* that fail to exclude seven files, versus the *seven index-tracked files* themselves. Neither subsumes the other; each is actionable alone. They share one edit, which is a sequencing fact, not an identity. Both retained, cross-referenced. |
| `DEP-003` / `DEP-006` | `DEP-003` files the absence of any control that would notice a coverage loss; `DEP-006` files one specific coverage loss. A control that would catch it is the same subject seen from two directions — explicitly **not** a merge, and the report says so in its own words. |

---

## Rollout ordering constraints

Detected under block (c) at R4. **Three constraints, all one-way. No circular dependency
exists and no fix is unorderable.** No `VAL-` finding is minted: nothing here is a
cross-phase conflict, and none of the three can be turned into a blocker by an authoring
choice that the findings themselves already specify.

| # | Constraint | Why | Dissolves? |
|---|---|---|---|
| 1 | `DEP-001`, `DEP-002` and `TST-005` insert into the **same step list** — `packaging-check.yml:37-53`. | Three accepted fixes, one insertion point, a 53-line file. Applied as three commits they collide at the same two lines. | **No — sequence them in one commit.** This is `VAL-125`'s collision, now ratified, extended to `DEP-001`. |
| 2 | `DEP-005` must land **before or with** any whole-tree form of `DEP-001`. | The moment the lint gate runs `ruff check .` rather than `ruff check src tests`, the three `tmp/` scratch files stop being a local annoyance and become a red build. `uv run ruff check .` exits 1 today. | **Yes — if `DEP-001` is implemented in the scoped form its own recommendation already specifies.** The constraint exists only against the unscoped form. |
| 3 | `DEP-004`'s rule rewrite must land **before** the `git check-ignore -q -- cli_ruff_output.txt` step `DEP-004` recommends adding. | `git check-ignore -q` returns non-zero while the rules are inert, so the verifying step is red on arrival and would fail the build for the very thing it verifies. | **No — order them.** Two lines in the same file, same commit is fine. |
| 4 | `DEP-008` and `DEP-009` both edit pinned artifact sets in `tests/test_packaging.py` — `EXPECTED_WHEEL_ENTRIES` (`:146-180`) and the sdist set — and `DEP-012` deletes the seven files that `DEP-004` un-ignores. | Independent edits, no shared anchor conflict. | **No constraint. Either order, or together.** Recorded so a run does not treat the co-location as a dependency. |

**No fragile insertion point exists in this report.** Every recommendation anchors on a named
file and a named construct, not a line number that will move: `EXPECTED_WHEEL_ENTRIES`, the
`if self._stealth_path.exists():` guard, `check_ffmpeg_available()`,
`[tool.hatch.build.targets.wheel] artifacts`, `[dependency-groups] dev`. The one
line-number-only anchor is `browser.py:112`, which sits near the end of the function and
survives any edit above it. **No hidden chain:** `DEP-001`'s recommendation depends on a
green `mypy src`, and `mypy src` is green — re-measured by this run at
`Success: no issues found in 30 source files`, exit 0.

---

## Documented skips (retained verbatim from the source report)

Emitted in the fixed wording, because under `problems-only` silence reads as "no finding".
**These are retained in full.** They are the record that specific checks were **not**
performed, and dropping them would manufacture a clean result on exactly the rows that must
never be manufactured clean.

1. **Live advisory-database access** (which dependencies carry a known vulnerability) — *not
   performed.* It requires a network an advisory database is not reachable from here. **No
   vulnerability count is asserted.** What remains verifiable, and was verified: the resolved
   dependency set is 41 locked packages (`uv.lock`, format version 1, revision 3), every one
   of the 40 registry-sourced entries carries a `sha256` hash on every artifact it lists
   (hash-presence count: 40 of 40; missing-hash list: empty), and `uv lock --check` exits 0
   with "Resolved 41 packages in 3ms", so the resolution record is in sync with the manifest.
   The fileable subject is the absence of a scanner from the gate set, filed as `DEP-003`.
   *Independently re-verified by this run; the one precision added is that `playwright`
   lists **wheels only, no `sdist` line**, so "a sha256 on every sdist and wheel" is exact
   for 39 of the 40 and "on every artifact it lists" is exact for 40 of 40. The
   substantive claim — no unhashed artifact, no missing hash — is unchanged.*

2. **Publishing to a real index** (what a real release would expose) — *not performed.*
   Nothing was uploaded anywhere and no index was contacted. What remains verifiable, and
   was verified: the archive's measured composition from the build and enumeration — 73
   files in the sdist, 35 entries in the wheel, per-top-level counts and byte totals
   recorded in `DEP-008` and `DEP-009`, with no vendored tree, no worktree, no audit corpus
   and no user data among them. The publication consequence is stated as a projection only,
   in `DEP-015`.

3. **A real install from source** (what a consumer's build does with the archive) — *not
   performed offline.* No separate environment was constructed and the archive was not
   installed into one. The R11 invocation-form matrix (both the declared form and the form
   the package structure permits, five cases each) was executed against the current
   editable development environment, not against a clean install of the built wheel. What
   remains verifiable, and was verified: the archive's contents, and the fact that the
   product's own `.venv` has the console script and the module form both working with
   identical exit statuses (0 for `--help`, 2 for no arguments, an unknown command, and a
   missing required argument on both `download` and `batch`). The fileable subject is the
   archive's contents, enumerated above.
   *Independently re-run by this run, both forms, all five cases:*

   | Case | `python -m vkdownloader` | console script `vkdownloader` |
   |---|---|---|
   | `--help` | 0 | 0 |
   | no arguments | 2 | 2 |
   | unknown command | 2 | 2 |
   | `download`, missing required URL | 2 | 2 |
   | `batch`, missing required URLs | 2 | 2 |

   **The two invocation forms agree on all five exit statuses.** `docs/STRUCT.md:11` is
   confirmed to record `__main__.py` as the `python -m vkdownloader` entry point, and
   `pyproject.toml:30-31` declares `[project.scripts] vkdownloader = "vkdownloader.cli:cli"`
   — the second form is documented even though the manifest declares only the console
   script.

4. **Scratch directory outside the repository** (R1's stated prerequisite) — *deviation
   recorded.* The environment denies writes to any path outside the workspace, so
   `uv build --out-dir` was pointed at `.temp/dist/` instead. `.temp/` is excluded by the
   repository-carried rule at `.gitignore:40` and by `[tool.ruff] extend-exclude` at
   `pyproject.toml:70`, and the sdist `include` allow-list (`pyproject.toml:52-65`) has no
   entry that could admit it. A clean working-tree check was run after the build and the
   four untracked-and-unexcluded paths are unchanged from their pre-build state (`DEP-005`
   lists them); no build residue entered the index.
   `tests/test_packaging.py:397-415` performs the same build into a
   `tempfile.mkdtemp()` path outside the repository and asserts the project's top-level
   entries are unchanged afterwards, and that module passed in the run recorded in the
   baselines table.
   *This run repeated the deviation and re-checked the post-build tree: no build residue
   entered the index, and `git status --porcelain` shows no change to `pyproject.toml`,
   `uv.lock`, `.gitignore`, `.github/`, `src/` or `tests/` beyond the two pre-existing
   concurrent edits. **The untracked-and-unexcluded set is now three paths, not four** —
   `probe_tmp.py` was deleted before this run began. See the `DEP-005` note.*

5. **Live behaviour of a third-party transport, downloader or browser library** — *out of
   scope by design.* `yt_dlp`, `aiohttp` and `playwright` were read as declarations and as
   import sites; nothing about their runtime behaviour, their network behaviour or their
   vulnerability status is asserted or guessed here.
   *This phase adds nothing to this row and asserts nothing about third-party runtime
   behaviour. The `TRN-001` argfile observation is phase 05's and was not re-derived.*

---

## Cross-phase references (not re-filed here)

- **`TST-005` / `DEP-002` — merged, `DEP-002` absorbs.** See the de-duplication ruling
  above and `VAL-125` in phase 10's validation store.
- **Phase 06** owns runtime credential and secret handling. `SEC-005` (the same child-output
  bytes reaching the terminal untransformed and the log redacted in one run) and `SEC-007`
  (caught-exception text reaching the log untransformed) are **not re-derived here.** This
  phase checked only whether the declared dependency set covers what is imported. It does:
  `yt_dlp` is declared at `pyproject.toml:27` and reached at
  `src/vkdownloader/services/extractor.py:7` (`import yt_dlp`) and, in the test tree, at
  `tests/test_cookies.py`. No finding is filed on the leak itself. *Note: the report's
  cross-phase text also names `ytdlp_downloader.py` as an import site; it is not one — see
  the `DEP-007` note. The declared-dependency angle is unaffected.*
- **Phase 05** owns subprocess, ffmpeg and browser invocation. `TRN-001` (HIGH as re-derived
  by that run, not CRITICAL as the source report's cross-reference states) is the observed
  `ffmpeg @<argfile>` downgrade. `DEP-011` files only the pinning-policy consequence. **The
  argfile behaviour was not re-derived by this phase and is not asserted anywhere in this
  artifact.**
- **Phase 09** owns the mypy profile and the unmarked-dependency policy. `QLT-009` (the
  three `Any` keys absent from the profile; `yt_dlp` the sole unmarked dependency) is
  adjacent to `DEP-007` and is cited, not re-filed. The profile's absence of those keys is
  why `uv run mypy src` is clean across 30 source files (re-measured, exit 0) while
  `uv run mypy src tests` reports 55 errors in 6 files (re-measured, exit 1).
- **Phase 10** owns the tests themselves and the test-execution job. `DEP-002` files only
  the catalogue gap and makes no claim about what the 502 collected tests prove. `TST-013`
  (the four permission oracles permanently skipped on Windows) and `ART-007` (the
  file-permission guarantee) are **not double-listed here**: this report records the four
  skips as measured skips and names their phase-07 subject, and files no finding on the
  oracle form.
- **Phase 02** owns settings and env parsing; `CFG-001`/`CFG-002` are fixed as of
  `ea44b3d` and were not re-examined.
- **`.ai/plans/done/01-confirmed-code-defects_DONE.md`** — the archived defect register
  describes an earlier manifest shape (`[project.optional-dependencies] dev` holding
  `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `black`, `isort`, `pyyaml`) and a `uv sync`
  projection that uninstalled the verification tooling. **Neither describes the manifest as
  it stands**, and this run confirms the current shape independently: `[dependency-groups]
  .dev` at `pyproject.toml:110-116` holds four names with no `black`, `isort` or `pyyaml`;
  `[project.optional-dependencies]` is absent; and `uv sync --dry-run` reports
  "Would make no changes" with all four verification commands resolving. The historical
  formatters are not present, so R7's "a formatter declared beside a linter that already
  owns its function" correctly produced no finding. The register is a `.ai/plans/done/`
  document and is cited, not filed.
- **`docs/STRUCT.md`** is known stale — it omits `ytdlp_downloader.py` — which is a
  structural description and therefore phase 09's. It *is* accurate on the one point this
  phase needed from it: `docs/STRUCT.md:11` records `__main__.py` as the
  `python -m vkdownloader` entry point.
- **Phase 08's `VAL-003`** — the pipeline pins a commit in the report header but records
  nothing about the tree it read. **Not re-filed.** Recorded here only to note that phase
  11's report does the right thing: its header states the working tree measured
  (`HEAD = a335b2a`, with named uncommitted edits to `cli.py` and `config.py`), and this
  run independently re-established that every manifest, lock and gate anchor it cites is
  byte-identical at `HEAD` and in the working tree.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 16 | `DEP-001`, `DEP-002`, `DEP-003`, `DEP-004`, `DEP-005`, `DEP-006`, `DEP-007`, `DEP-008`, `DEP-009`, `DEP-010`, `DEP-011`, `DEP-012`, `DEP-013`, `DEP-014`, `DEP-015`, `DEP-016` |
| Reclassified | 0 | — |
| Merged | 0 | no finding *in this report* was merged away; one **cross-phase** absorption is ruled below |
| Rejected | 0 | — |
| `VAL-` (cross-phase / rollout) | 0 | none minted — no conflict, no circular dependency, no hidden chain, no rollout blocker |
| **Severities re-derived** | **16 of 16; 0 changed** | 3 HIGH, 10 MEDIUM, 3 LOW — all confirmed |
| **Evidence enumerations corrected** | 2 | `DEP-005` (four paths → three), `DEP-013` (one orphan added, one generation added) |
| **Citation corrections (immaterial)** | 3 | `DEP-004` (`.gitignore:66` is `Shows/` not `Show/`), `DEP-007` (`yt_dlp` is imported in one file, not two), `DEP-011` (`TRN-001` is HIGH, not CRITICAL) |
| **Findings reproduced end-to-end** | **16 of 16** | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | **None.** All 16 findings reproduced in substance. Two enumerations drifted between the source run and this one (`DEP-005`, `DEP-013`); in both cases the subject, the root cause and the consequence reproduce unchanged, so the findings were **validated with a corrected current-tense file list** rather than rejected as stale. No finding met a rejection ground, so no rejection block is manufactured and no empty appendix is filled. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| `TST-005` (phase 10) | **`DEP-002` (phase 11)** | **One defect: `.github/workflows/packaging-check.yml:53` runs one module of 502 collected tests. One cause, one consequence, one remediation, one insertion point** — the two-line `- name:` / `run:` pair at the end of a 53-line job. Two fixes authored from two reports collide at the same two lines. `DEP-002` absorbs because it owns `.github/workflows/**` by phase 11's own boundary and already carries `SPEC-DEVIATION` / `mandatory` — which is now also what `TST-005` carries, so `VAL-125`'s classification-conflict premise is resolved and only the duplication remains. **RATIFIED by this run, which is the validator phase 10 deferred the decision to; not executed, because this phase writes one artifact and reads the rest.** The one element `TST-005` uniquely carries — that no coverage tool or threshold is declared anywhere in the repository — must be folded into `DEP-002`. **`TST-005` is marked absorbed. Do not land both fixes independently.** |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| — | — | — | **None.** No `Type` was changed. `DEP-016`'s `SPEC-DEVIATION` label is the one arguable label in this report and is **upheld** rather than reclassified, on the evidence that `docs/01-tools/installation.md:154-157` instructs a user to read the duplicated attribute — so a document and the code disagree about which copy is authoritative; the alternative reading (`BEST-PRACTICE`, duplicated constant) is recorded so a later run does not treat the label as settled beyond that evidence. |

---

## Report contract — block (i) findings on this pipeline

| Check | Result |
|---|---|
| Every decided finding carries a decision, a rationale and its cross-references | **satisfied** — 16 `Validation Note` blocks, one per finding, each with action, confirmed severity, evidence and `See also` |
| The field exists in the report format | **NO — the input defect this phase owns.** `templates/audit-findings.md:62-79` defines nine mandatory fields, none of which carries a decision, and the finding block runs from the heading straight into the field table. The `Validation Note` is written immediately below each heading and the deviation is stated once in this artifact's header. **The format must gain the slot.** |
| The retained content is present | **satisfied** — every finding's original description, evidence and recommendation is retained verbatim below its decision record |
| The tally reconciles | **satisfied** — 16 decisions recorded, 16 in the tally, difference none |
| No invented entries | **satisfied** — 0 `VAL-` findings minted; the only `VAL-` reference is `VAL-125`, which exists in phase 10's store and is cited, not re-issued |
| Pre-answered sections deleted | **satisfied, and stated once in the header** — the source report's `## Summary`, `## Mandatory Fixes`, `## Advisory Recommendations` and `## Doc Updates Needed` are removed. **A section every phase must delete is a defect of the format** — those four are groupings the format itself supplies pre-answered, so their removal is mandatory for every run that fills them, and the resulting burden is filed against the format by the phase that owns it, not against this report. |

---

## Second-pass re-entry index

Recorded so a re-run resumes at the first item below with no evidence, rather than at step 1.
**R0** corpus / identifier / decision-record maps — complete (scope table above).
**R1** copy — complete. **R2** cross-finding — complete (0 conflicts, 1 merge ratified,
2 complements). **R3** per-finding — complete, 16 of 16, severities re-derived, two
enumerations corrected. **R4** rollout — complete, 3 one-way constraints, 0 blockers.
Blocks **(a)** per-finding validity, **(b)** merge/conflict, **(c)** rollout, **(d)** label
adjudication, **(e)** dead-code reconciliation, **(f)** rejection discipline, **(i)** report
contract — complete.

**Block (e) result: not applicable, and no dead-code finding is filed in this report.**
The reconciliation was run before any absence-of-use claim was accepted, and no claim
reached it. `DEP-012` is the only near neighbour and is **not** dead code: the seven files
are index-tracked build detritus rather than components, and `stage_and_commit.bat` is
behaviour-bearing (it stages paths into the index). `DEP-016`'s `__version__` is referenced
by a shipped document (`installation.md:154-157`), so even the duplication candidate is
referenced. No reclassification to "missing integration" is warranted, and none was made.

**Blocks (g) and (h) — the audit pipeline's own execution claims and its documents — were
NOT executed by this run, and that is recorded as a scope boundary rather than a clean
result.** This run was given phase 11's findings and validated those 16. Executing (g) and
(h) requires the pipeline command documents, the report template and the agent role files
as the subject. One corpus-level fact was observed in passing and is cross-referenced rather
than filed: the tracked generation of the audit corpus
(`.ai/audit/01-audit-cli/` … `09-audit-quality/`, `99-validation/01-audit-cli-validated-findings.md` …)
is deleted in the working tree while the current generation
(`01-entry-architecture/` … `11-supply-chain/`, `01-entry-architecture-validated-findings.md` …)
is untracked — the write-path / check-path divergence **phase 08 already filed as
`VAL-001`–`VAL-005`**. Not re-filed here. A run that has the pipeline documents in scope
should confirm the `(g)` and `(h)` blocks against that store.









