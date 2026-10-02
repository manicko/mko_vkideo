---
name: audit-findings
description: Phase 11 - Supply Chain audit findings
phase: 11-supply-chain
executor: audit-executor
template: .kilo/commands/audit/phases/11-audit-supply-chain.md
status: complete
validated: no
problems-only: true
---

# Phase 11 Audit Findings — Supply Chain

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/11-audit-supply-chain.md`
**Status:** complete
**Validated:** no

**Working tree measured:** `HEAD = a335b2a`, with uncommitted edits to `src/vkdownloader/cli.py`
and `src/vkdownloader/config.py` from a concurrent agent. `pyproject.toml`, `uv.lock`, `.gitignore`
and both workflow files are **not** modified in the working tree, so every manifest, lock and gate
anchor below is identical at `HEAD` and in the working tree. The two edited source files were
measured in the working tree; `git show HEAD:` sizes are recorded where an anchor depends on them.

**Baselines re-measured here (working tree):**

| Command | Result | Exit |
|---|---|---|
| `uv run --no-sync pytest -q -rs` | 498 passed, 4 skipped (502 collected) in 27.14s | 0 |
| `uv run --no-sync ruff check src tests` | All checks passed! | 0 |
| `uv run --no-sync ruff format --check src tests` | 52 files already formatted | 0 |
| `uv run --no-sync mypy src` | Success: no issues found in 30 source files | 0 |
| `uv run --no-sync mypy src tests` | Found 55 errors in 6 files (checked 52 source files) | 1 |
| `uv run --no-sync ruff check .` | Found 3 errors (all in untracked root scratch) | 1 |
| `uv run --no-sync pytest tests/test_packaging.py -v` | 14 passed in 2.32s | 0 |

The 4 skips, with reasons: `tests/test_config.py:337`, `tests/test_config.py:353`,
`tests/test_hls_downloader.py:533`, `tests/test_hls_downloader.py:678` — all
"Owner-only confinement is not offered on Windows: `os.chmod` there toggles only the read-only
attribute, so the measured mode is 0o666 rather than the requested 0o600 (D-11)". These are
filesystem-mode subjects belonging to phase 07; they are recorded here as skips, not as clean
results.

---

## Findings

### DEP-001: Lint, format check and type check are documented as the project's verification and enforced by no automation

| Field | Value |
|-------|-------|
| **ID** | DEP-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.github/workflows/**`, `pyproject.toml`, `.ai/context/commands.md`, `docs/01-tools/installation.md` |
| **Classification** | mandatory |

**Description:** The project states four verification commands as its own bar — `uv run pytest`,
`uv run ruff check`, `uv run ruff format --check`, `uv run mypy` — in `.ai/context/commands.md:15-18`
and again as the documented development workflow in `docs/01-tools/installation.md:94-110`. All three
tools are declared with configuration blocks the tools actually read (`[tool.ruff]` at
`pyproject.toml:67`, `[tool.mypy]` at `pyproject.toml:90` with `strict = true` at line 92). The
repository's complete automation set contains two definitions and neither runs any of them.
`ruff check`, `ruff format --check` and `mypy` are invoked by nothing: no workflow, no hook file, no
`tox`/`nox`/`make` target, no script. The only places the tool names appear outside their own
configuration blocks are `.ai/context/commands.md`, `docs/01-tools/installation.md` and the agent
command prompts under `.kilo/commands/` — none of which is an automation that runs.

The consequence is not hypothetical on this tree: `mypy` is configured `strict = true`, and
`uv run mypy src tests` currently exits 1 with 55 errors in 6 files, every one of them in `tests/`.
Nothing in the repository reports this. A commit that breaks a type contract in production code
merges green.

**Evidence (R9 — read the complete gate set):**

Complete enumeration. A filesystem walk for `*.yml`/`*.yaml` outside `.venv/`, `.kilo/`, `.ai/`,
`.temp/` returns exactly two files, and `git ls-files .github` returns exactly the same two — the
directory walk and the index-scoped listing agree:

```
.github/workflows/doc-lint.yml
.github/workflows/packaging-check.yml
```

There is no third definition, tracked or untracked. `.github/` contains no other file.

Per-definition trigger, filter, per-job commands and failure condition, complete:

| Definition | Trigger + filter | Job | Commands | Fails on |
|---|---|---|---|---|
| `packaging-check.yml` | `push`/`pull_request` on `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, `.env.example`, `src/**`, `tests/**`, `docs/**`; plus `release: [published]` | `packaging-check` | `uv sync --locked` (line 51); `uv run pytest tests/test_packaging.py -v` (line 53) | non-zero exit of either step |
| `doc-lint.yml` | `push`/`pull_request` on `docs/**` only | `nul-check` | `grep -rlaP '\x00' docs/` (line 22) | NUL byte found in `docs/` |

Neither file names the linter or the type checker outside `doc-lint`'s own `name:` key:

```
$ git grep -c -I -E "ruff|mypy" -- .github
(no matches)
```

Job-class enumeration required by R9 (test execution excluded — it is DEP-002):

| Class | Present | Evidence |
|---|---|---|
| Lint | **absent** | no `ruff` invocation in any definition |
| Format check | **absent** | no `ruff format` invocation in any definition |
| Type check | **absent** | no `mypy` invocation in any definition |
| Dependency scan | **absent** | see DEP-003 |
| Secret scan | **absent** | see DEP-003 |
| Lockfile check | present | `packaging-check.yml:51` `uv sync --locked` |
| Build and publish | partial (build-only) | see DEP-015 |

Trigger-admission verdicts (R9's three filter verdicts): `packaging-check.yml`'s filter **does**
admit a change to the source tree (`src/**`), the test tree (`tests/**`) and the manifest
(`pyproject.toml`). The filter is not the defect here; the job body is. `doc-lint.yml`'s filter
admits only `docs/**`, which is correct for the check it performs.

Measured counter-evidence that the tooling works and is simply never asked to run:
`uv run --no-sync ruff check src tests` -> `All checks passed!` (exit 0);
`uv run --no-sync mypy src` -> `Success: no issues found in 30 source files` (exit 0).

**Recommendation:** Add one job — or one step in the existing `packaging-check` job — that runs
`uv run ruff check src tests`, `uv run ruff format --check src tests` and `uv run mypy src` on the
path filter that already covers `src/**`, `tests/**` and `pyproject.toml`, failing the build on a
non-zero exit of any of the three. Type-check `src` first: it is the gate that is currently green
and worth protecting, and folding `tests` in (55 errors) into the same change would fail every PR
until those are cleared separately. No new tool is needed — all three are already declared,
already configured, and already run cleanly.

---

### DEP-002: No job in the repository executes the test suite; the only pytest invocation collects 14 of 502 tests

| Field | Value |
|-------|-------|
| **ID** | DEP-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.github/workflows/packaging-check.yml` |
| **Classification** | mandatory |

**Description:** R9's job-class enumeration requires recording, against the catalogue of recognised
classes, which exist and which do not. This finding files the **absence of the class from the
catalogue** and the shape of the one job that touches the test tree. It files nothing about whether
the tests prove anything — that is phase 10's, cited here and not merged.

`packaging-check.yml:53` runs `uv run pytest tests/test_packaging.py -v`. That path is a single
module. The full suite collected 502 tests when re-measured here. The consequence: 488 collected
tests are never executed by any automation in this repository, and a regression in any of them
merges green. A change to `tests/**` is admitted by the workflow's path filter and therefore *looks*
gated while running under 3% of the tree.

**Evidence (R9, with the local run of the exact CI command):**

```
$ uv run --no-sync pytest tests/test_packaging.py -v
============================= test session starts ==============================
platform win32 -- Python 3.12.1, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\py_exp\mko_vkideo
configfile: pyproject.toml
plugins: asyncio-1.4.0
collected 14 items
...
14 passed in 2.32s
EXIT=0
```

```
$ uv run --no-sync pytest -q -rs
498 passed, 4 skipped in 27.14s
```

No other definition invokes pytest: `doc-lint.yml` runs a single `grep` and nothing else. Four of
the 14 tests in `test_packaging.py` do not exercise the product at all —
`test_a_build_failure_that_is_not_a_network_error_fails_everywhere`,
`test_a_network_build_failure_fails_on_a_ci_runner`,
`test_a_network_build_failure_skips_on_a_developer_machine` and
`test_the_ci_variable_is_what_selects_the_outcome` (`tests/test_packaging.py:529-569`) all call
`_build_failure_outcome()` with hardcoded strings.

**Recommendation:** Add `uv run pytest tests/` as a step in the existing `packaging-check` job, or
as a separate `tests` job on the same path filter. Both `src/**` and `tests/**` are already in the
filter, so no trigger change is required. The 4 skips are Windows-`chmod` subjects and the runner is
`ubuntu-latest`, so they will not fire there; running with `-rs` in CI makes any runner-dependent
skip visible in the log rather than silent. Keep the existing `test_packaging.py` step — it is a
real artifact gate, not a substitute for the behavioural suite.

---

### DEP-003: No dependency scanner, no secret scanner, no update automation, no pre-commit control and no ownership file are configured anywhere in the repository

| Field | Value |
|-------|-------|
| **ID** | DEP-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.github/**`, `.pre-commit-config.yaml` (absent), `.github/dependabot.yml` (absent), `.github/CODEOWNERS` (absent) |
| **Classification** | advisory |

**Description:** R10(a) requires path-checking each recognised configuration for each scanning,
update-automation, ownership and pre-commit class and separately grepping tracked files for the tool
names each class implies. Both were run. Five classes are configured nowhere and nothing runs them.
The declared dependency surface is 8 runtime distributions and 4 development ones, resolved to 41
locked packages, none of which any control inspects for a known vulnerability and none of which any
automation proposes an update for.

This is filed against the *absence of a control*, never against the absence of material — the
committed-material sweep is a separate row and it returned zero (recorded as a measurement, not a
finding; see the documented-skips section for the advisory-database skip that pairs with this
finding).

**Evidence (R10a — path-check each recognised configuration, then grep tracked files):**

```
$ git ls-files | Select-String -Pattern "(?i)pre-commit|dependabot|renovate|CODEOWNERS|gitleaks|trufflehog|detect-secrets|safety|osv|pip-audit|trivy|grype|syft|\.secrets|sbom|cyclonedx|spdx"
(no matches)
```

Per-class tool-name hit counts over tracked files, excluding the lockfile, the agent tooling tree and
this audit's own corpus:

```
$ git grep -c -I -i -F -- "<tool>" -- . ':!uv.lock' ':!.kilo' ':!.ai'
pre-commit       files=0
gitleaks         files=0
trufflehog       files=0
detect-secrets   files=0
pip-audit        files=0
osv-scanner      files=0
osv              files=0
dependabot       files=0
renovate         files=0
trivy            files=0
grype            files=0
syft             files=0
CODEOWNERS       files=0
cyclonedx        files=0
sbom             files=0
hatch-audit      files=0
uv audit         files=0
```

(`safety` returned 10 file hits and was discarded as a false positive on the English word; no
class implies that literal.)

| Class | Configured | Run by |
|---|---|---|
| Dependency vulnerability scan | no | nothing |
| Secret scan | no | nothing |
| Dependency-update automation | no | nothing |
| Pre-commit | no | nothing |
| Ownership (`CODEOWNERS`) | no | nothing |

**Recommendation:** Two additions carry most of the value and neither is an enterprise pattern.
First, `.github/dependabot.yml` with `package-ecosystem: "uv"` — it is a 6-line file, it runs on
GitHub's schedule, and it turns the 12 open-ended lower bounds in `pyproject.toml` into reviewed
update PRs instead of silent drift. Second, a `uv run` step using an advisory scanner over
`uv.lock` in the existing `packaging-check` job, so a known-vulnerable transitive resolution fails
the same build that already asserts the artifact composition. Add `.pre-commit-config.yaml` only if
the team wants a local pre-flight — the CI gate from DEP-001 is the higher-leverage half and needs
no new configuration file at all.

---

### DEP-004: Seven root debris entries are index-tracked and the ignore rules that claim to exclude them are inert literal patterns

| Field | Value |
|-------|-------|
| **ID** | DEP-004 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.gitignore`, `%PYFILE%`, `Continue`, `Continue=SilentlyContinue`, `ErrorPreference=SilentlyContinue`, `cli_ruff_output.txt`, `temp_tests_output.txt`, `stage_and_commit.bat` |
| **Classification** | mandatory |

**Description:** `.gitignore:56-58` states the intent in prose: *"Root debris from earlier tool runs.
None of it is part of the project; every entry below is currently tracked and is listed so the reason
is recorded here and so the files cannot come back once they are untracked."* Each of the seven
entries at `.gitignore:59-65` puts a `#` comment **on the same line as the pattern**. Git starts a
comment only when `#` is the first character of a line, so each of those lines is one literal
pattern whose text includes the comment. The rules do not exclude the files they name; they exclude
filenames that do not exist and never will. The stated purpose — that the files "cannot come back
once they are untracked" — is not performed by the configuration, so `git rm --cached` on any of
them followed by one `git status` would show them as untracked-and-unexcluded, ready to be committed
again.

This is filed as `SPEC-DEVIATION`: the comment is a statement of intent that the adjacent line
contradicts, in the same file, six lines apart.

**Evidence (R12 — search tracked files, then path-check every candidate against the rules):**

`git check-ignore` consults the ignore rules and not the index, so its verdict is the rule's
verdict alone. Positive control first, then every candidate:

```
$ git check-ignore -v -- urls.txt
.gitignore:46:urls.txt      urls.txt          (control: the mechanism works)

$ git check-ignore -v -- "cli_ruff_output.txt         # captured ruff output"
.gitignore:63:cli_ruff_output.txt         # captured ruff output
                                                       (the line IS a literal pattern)

$ git check-ignore -q -- <name>; echo ignored=$?
%PYFILE%                          ignored=False
Continue                          ignored=False
Continue=SilentlyContinue         ignored=False
ErrorPreference=SilentlyContinue ignored=False
cli_ruff_output.txt              ignored=False
temp_tests_output.txt            ignored=False
stage_and_commit.bat             ignored=False
```

The second result is the proof: git matches that line against the *whole* text including the
comment, and reports it as the source rule. The bare names match nothing.

Line `.gitignore:66` (`Show/  # empty directory left behind by a stray shell command`) is a tenth
case of the same shape: `Show` does not exist in the working tree (`Test-Path Show` -> `False`), and
its line has a trailing comment so it would not exclude it if it reappeared. `.gitignore:34`
(`!/.env.example`) is the one negation in the file, it is anchored, and it behaves correctly —
verified: `git check-ignore -v -- .env.example` reports no match, which is the intended re-admission.

None of the seven reaches a built artifact: the sdist is governed by the allow-list at
`pyproject.toml:52-65`, and the enumeration in DEP-012 confirms the archive's 73 files contain none
of them. So the exposure is the index and every future commit, not the archive.

**Recommendation:** Put each `#` comment on its own line above its pattern, then `git rm --cached`
the seven tracked files. The rewrite is mechanical:

```
# empty file left by an unexpanded %PYFILE% variable
%PYFILE%
# PowerShell pipeline fragment: `Continue` with no argument
Continue
...
```

After the rewrite, `git check-ignore -q -- cli_ruff_output.txt` must return 0; that is the one-line
check that proves the fix landed, and it is worth adding to the packaging check because the
regression is silent — the rules are wrong today and nothing reports it.

---

### DEP-005: Four untracked-and-unexcluded scratch paths sit at the repository root and already break the project's own whole-tree verification command

| Field | Value |
|-------|-------|
| **ID** | DEP-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `probe_tmp.py`, `tmp/click_result.txt`, `tmp/click_test.py`, `tmp/click_test2.py`, `tmp/__pycache__/`, `.gitignore` |
| **Classification** | mandatory |

**Description:** R12 records three states as three — tracked-and-ignored, untracked-and-ignored,
untracked-and-unexcluded — and the third is the one to characterise. Four paths are in it. They are
excluded by no repository-carried rule, by no nested ignore file, and by no rule held outside the
repository: nothing names them. The exclusion sources for the neighbouring paths in the same
neighbourhood *are* carried (`.gitignore:40` for `.temp/`, `.gitignore:46` for `urls.txt`,
`.gitignore:13` for `*.mp4`), so this is not a machine-local configuration gap — the rules are
present and simply omit these four.

The consequence is already observable, not hypothetical. `ruff` discovers them:

```
$ uv run --no-sync ruff check .
I001 [*] Import block is un-sorted or un-formatted
   --> probe_tmp.py:2:1
I001 [*] Import block is un-sorted or un-formatted
 --> tmp\click_test.py:1:1
I001 [*] Import block is un-sorted or un-formatted
 --> tmp\click_test2.py:1:1
Found 3 errors.
[*] 3 fixable with the `--fix` option.
EXIT=1
```

```
$ uv run --no-sync ruff format --check .
Would reformat: probe_tmp.py
Would reformat: tmp\click_test.py
Would reformat: tmp\click_test2.py
3 files would be reformatted, 52 files already formatted
EXIT=1
```

The scoped form the project documents (`docs/01-tools/installation.md:97,103` — `uv run ruff check
src/`) still passes, which is why nothing has noticed. A contributor who runs the obvious
whole-tree invocation gets a red result for files that are not the project's. The second path to
the same files is `stage_and_commit.bat:5-6`, which runs `git add -A` — see DEP-012.

**Evidence (R12 — enumerate the working tree, classify every path the index does not track):**

```
$ git ls-files --others --exclude-standard | Select-String -NotMatch "^\.ai/"
probe_tmp.py
tmp/click_result.txt
tmp/click_test.py
tmp/click_test2.py
```

Full untracked-and-unexcluded set, `.ai/` audit-corpus paths excluded as this phase's own output:

| Path | Tracked? | Named by a repository rule? | Nested tool-written rule? |
|---|---|---|---|
| `probe_tmp.py` | no | no | no |
| `tmp/click_result.txt` | no | no | no |
| `tmp/click_test.py` | no | no | no |
| `tmp/click_test2.py` | no | no | no |

Contents read, per R12's requirement to say what each candidate is: `probe_tmp.py:1` describes
itself as *"Throwaway probe to learn stdout/stderr/logfile behavior for the new tests."* and
`tmp/click_test.py:1-8` is a 8-line Typer/Click rendering experiment. None is referenced by any
tracked file.

Do these reach a built artifact? No. The sdist's `include` allow-list (`pyproject.toml:52-65`) has
no entry that could admit them, and the 73-file enumeration in DEP-012 confirms it. So the subject
is the index boundary and the developer command, not the archive.

**Recommendation:** Add one rule to `.gitignore` next to the existing scratch entries at line 40 —
`/tmp/` and `/probe_tmp.py` — then delete the four files. Two lines, no build-configuration change,
and it removes the only reason `uv run ruff check .` currently exits 1. Once DEP-001 adds the lint
gate, this rule is what stops the gate from being the thing that discovers the next stray file.

---

### DEP-006: Two exclusions depend on a nested ignore file the repository does not carry

| Field | Value |
|-------|-------|
| **ID** | DEP-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.kilo/.gitignore`, `.kilo/agent-manager.json`, `.gitignore` |
| **Classification** | advisory |

**Description:** R4 requires recording every exclusion that depends on a file the repository does
not carry, because such an exclusion protects exactly one machine: a clean checkout has no
`.kilo/.gitignore`, so the two paths it excludes become ordinary untracked files there.
`.gitignore:48-54` shows the maintainer already reasoned about this seam for two neighbouring paths
— *"Ignored here as well as in .kilo/.gitignore because the build backend reads this file, not the
nested one, when it selects the files to package"* — and carried `.kilo/worktrees/` and
`.kilo/node_modules/` in the root file for that reason. Two entries were missed:
`.kilo/agent-manager.json` and `.kilo/.gitignore` itself.

`agent-manager.json` is a live file on this machine, and its top-level keys are `worktrees`,
`sessions`, `tabOrder`, `sessionsCollapsed` — agent-manager session state, one key of which is named
for sessions. The file's contents are **not** a subject of this phase; the *coverage* is.

**Evidence (R4 — for each excluded path, `git check-ignore -v` names the file the exclusion depends
on):**

```
$ git check-ignore -v -- .kilo/agent-manager.json .kilo/.gitignore .kilo/node_modules .kilo/worktrees
.kilo/.gitignore:8:agent-manager.json    .kilo/agent-manager.json
.kilo/.gitignore:7:.gitignore            .kilo/.gitignore
.kilo/.gitignore:1:node_modules          .kilo/node_modules
.gitignore:49:.kilo/worktrees/           .kilo/worktrees
```

The asymmetry is visible in the output: `worktrees` resolves to the tracked root `.gitignore`
(line 49), the other two resolve to the untracked nested file (lines 7 and 8). `node_modules` is
covered by both, so the root comment's claim for it holds.

```
$ git ls-files --others --ignored --exclude-standard | Select-String "^\.kilo"
.kilo/.gitignore
.kilo/agent-manager.json
```

`.kilo/.gitignore` is itself untracked — it is the second of the two, and it is the file that would
be missing from a clean checkout. It also lists itself at line 7, so a contributor who has never run
the agent tooling will never have it.

**Recommendation:** Add the two missing names to the root `.gitignore`, in the block that already
exists for this reason:

```
# Agent worktrees: each holds a complete second copy of src/vkdownloader/.
.kilo/worktrees/
.kilo/agent-manager.json
.kilo/.gitignore
```

Keep the nested file — it is correct for what it does and there is no reason to remove it. The
change is additive, three lines, and it makes the root file match the intent its own comment already
states. It is also the second half of the coverage question DEP-003 files: a rule that stops covering
a path is this phase's finding, and a scanner that would notice its loss is the control that is also
absent. Neither is present today.

---

### DEP-007: The test tree imports `annotated_types`, which no declaration mechanism names

| Field | Value |
|-------|-------|
| **ID** | DEP-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_config.py:472`, `pyproject.toml:110-116` |
| **Classification** | mandatory |

**Description:** R5 asks, for each name the manifest declares, whether anything reaches it; and the
converse question is the one that produced this finding. An AST-based import scan of the two
production and test trees found exactly one top-level module that is imported and is named by no
declaration mechanism anywhere in `pyproject.toml`. `tests/test_config.py:472` does
`from annotated_types import Ge, Le` inside a test. `annotated-types` is not in `[project.dependencies]`
(8 names) and not in `[dependency-groups].dev` (4 names). It resolves today only because
`pydantic>=2.0.0` declares it, so the name is present in `uv.lock` and the import succeeds.

The consequence is a correctness one: if `pydantic` ever drops, renames or vendors that dependency —
which its own maintainers may do without a major version bump — the suite fails at import with a
`ModuleNotFoundError` whose cause is invisible in this repository's manifest. Nothing here records
that the test tree depends on it.

**Evidence (R5 — read every declaration mechanism, then scan the source and test trees for the
import that would reach each name):**

Per-mechanism name sets and bounds, read from the parsed manifest:

| Mechanism | `pyproject.toml` | Names and bounds |
|---|---|---|
| `[project.dependencies]` | lines 19-28 | `playwright>=1.45.0`, `aiohttp>=3.9.0`, `pydantic>=2.0.0`, `pydantic_settings>=2.0.0`, `typer>=0.12.0`, `rich>=14.0.0`, `structlog>=24.0.0`, `yt-dlp>=2024.0.0` |
| `[dependency-groups].dev` | lines 110-116 | `ruff>=0.4.0`, `mypy>=1.10.0`, `pytest>=8.0.0`, `pytest-asyncio>=0.23.0` |
| `[project.optional-dependencies]` | absent | — |
| `[tool.hatch.build.targets.*]` | lines 37-65 | names paths, not distributions |
| `[build-system] requires` | lines 33-35 | `hatchling` (unbounded, build-time only) |
| `uv.lock` | — | 41 packages, 40 registry-sourced, 1 editable |

Per-name hit counts, index-scoped, with `__pycache__` excluded. Every declared runtime name is
reached by production source; every declared dev name is reached:

| Declared name | src | tests | Verdict |
|---|---|---|---|
| `playwright` | 6 files | 3 files | reachable |
| `aiohttp` | 2 files | 0 | reachable |
| `pydantic` | 4 files | 1 file | reachable |
| `pydantic_settings` | 1 file | 0 | reachable |
| `typer` | 2 files | 1 file | reachable |
| `rich` | 1 file | 2 files | reachable |
| `structlog` | 16 files | 0 | reachable |
| `yt_dlp` | 1 file | 1 file | reachable |
| `ruff` / `mypy` / `pytest` / `pytest-asyncio` | — | configured blocks and markers | reachable |

The undeclared import the scan produced, and the only one in either tree:

```
=== tests ===
annotated_types            1  [third-party/local]  tests/test_config.py
```

```
$ git grep -n "annotated_types" -- tests/
tests/test_config.py:472:        from annotated_types import Ge, Le
```

Lock cross-check: `annotated-types` is present in `uv.lock` only as a transitive entry of `pydantic`,
not as a direct requirement of either declared mechanism.

Duplication and conflicting-bounds rows, both empty: no distribution is declared by two mechanisms,
and no two mechanisms give one name different bounds. The wheel's metadata carries eight
`Requires-Dist` lines and no `Provides-Extra`, so the extras question in R2 has no duplicate to
report.

**Recommendation:** `uv add --dev annotated-types` (or, if the maintainer prefers to keep the dev
group minimal, import the constrained types from `pydantic` instead — the test needs the operator
types, not the package). One line either way; the point is that the test tree's real dependency set
becomes visible in the manifest instead of being inherited by accident.

---

### DEP-008: Neither built artifact carries a PEP 561 marker, so the published package's types are invisible to every consumer

| Field | Value |
|-------|-------|
| **ID** | DEP-008 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/`, `pyproject.toml:37-44` |
| **Classification** | advisory |

**Description:** R2 requires recording, from the source tree, whether a typed-distribution marker
exists at all. It does not. The package is fully annotated and is type-checked under
`strict = true` (`pyproject.toml:92`) with `mypy src` exiting 0 across all 30 source files. None of
that reaches an installer, because PEP 561 requires an empty `py.typed` marker file inside the
package, and neither the working tree nor the wheel contains one.

The consequence is at the consumer's end: after `pip install vkdownloader`, a downstream project
running mypy treats every `vkdownloader` import as untyped and skips it, so the annotations the
project maintains at real cost deliver nothing. Under `--strict` the same import surfaces as
`import-untyped` and, with `warn_unused_ignores` on the consumer's side, produces a second class of
noise. The project pays the full typing cost and ships none of the benefit.

Note the interaction with the existing artifact gate: `tests/test_packaging.py:146-180` pins the
wheel's entry set to an exact `frozenset`, so adding the marker will fail
`test_wheel_entry_set_matches_the_manifest` until `"vkdownloader/py.typed"` is added to
`EXPECTED_WHEEL_ENTRIES`. That is the gate working as designed; the change is two lines across the
manifest and the test.

**Evidence (R1 — build and enumerate; R2 — the wheel's own member list and the source tree):**

`py.typed` is absent from the working tree, from the index, and from the built wheel's central
directory:

```
$ git ls-files | Select-String "py.typed"
(no matches)
$ Test-Path src\vkdownloader\py.typed
False
```

Wheel member list, 35 entries, complete:

```
vkdownloader/__init__.py                       vkdownloader/services/progress_display.py
vkdownloader/__main__.py                       vkdownloader/services/quality.py
vkdownloader/cli.py                            vkdownloader/services/segment_downloader.py
vkdownloader/config.py                         vkdownloader/services/signal_handlers.py
vkdownloader/exceptions.py                     vkdownloader/services/ytdlp_downloader.py
vkdownloader/stealth.min.js                    vkdownloader/utils/__init__.py
vkdownloader/infrastructure/__init__.py         vkdownloader/utils/correlation.py
vkdownloader/infrastructure/browser.py         vkdownloader/utils/formatting.py
vkdownloader/infrastructure/network_monitor.py vkdownloader/utils/security.py
vkdownloader/models/__init__.py                vkdownloader/utils/url_sanitizer.py
vkdownloader/models/dtos.py
vkdownloader/models/enums.py                   vkdownloader-0.1.0.dist-info/METADATA
vkdownloader/models/video.py                   vkdownloader-0.1.0.dist-info/WHEEL
vkdownloader/services/__init__.py              vkdownloader-0.1.0.dist-info/entry_points.txt
vkdownloader/services/batch_downloader.py      vkdownloader-0.1.0.dist-info/RECORD
vkdownloader/services/concurrency.py
vkdownloader/services/cookies.py
vkdownloader/services/downloader.py
vkdownloader/services/downloader_throttle.py
vkdownloader/services/extractor.py
vkdownloader/services/ffmpeg_utils.py
```

Per-top-level breakdown: `vkdownloader` 31 entries / 245 583 bytes; `vkdownloader-0.1.0.dist-info`
4 entries / 9 515 bytes. There is no `py.typed` among the 31.

`[tool.hatch.build.targets.wheel]` (`pyproject.toml:37-44`) declares `packages` and `artifacts`;
neither names a marker, and neither is a mechanism that could add one — a marker must exist as a
file in the package directory.

**Recommendation:** Create an empty `src/vkdownloader/py.typed` and add the two lines the gate
needs: `"vkdownloader/py.typed"` in `EXPECTED_WHEEL_ENTRIES`
(`tests/test_packaging.py:146-180`) and nothing in the manifest, because `packages =
["src/vkdownloader"]` already admits any file inside the package directory, which
`tests/test_packaging.py:142-145` already documents. Verify with the existing job:
`uv run pytest tests/test_packaging.py -v` must stay at 14 passed.

---

### DEP-009: Both artifacts assert an MIT licence and ship no licence text

| Field | Value |
|-------|-------|
| **ID** | DEP-009 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `pyproject.toml:7`, `pyproject.toml:15`, `LICENSE` (absent) |
| **Classification** | advisory |

**Description:** `pyproject.toml:7` declares `license = "MIT"` and `pyproject.toml:15` adds the
trove classifier `License :: OSI Approved :: MIT License`. Both assertions reach the metadata of
both built artifacts. No licence text reaches either. Per this phase's scope the *licence claim
itself* is not the subject and is not filed; the subject is that a publishable artifact carries a
licence assertion with nothing behind it.

The consequence is at the distribution end. PEP 639 separates the SPDX expression (what the
metadata asserts) from the licence file (what a redistributor needs in order to comply), and the
builder emits a `License-File` entry only when it can find a licence file to point at. It finds
none, so the metadata has `License-Expression: MIT` and no `License-File` at all. An index listing
shows MIT; a downloader that mirrors, vendors or re-licences the package has nothing to reproduce
and no notice obligation it can discharge.

**Evidence (R2 — read the built wheel's `.dist-info` entry list and metadata block; separately, the
two existence answers from the source tree):**

`pyproject.toml:7` and the classifier at line 15:

```
license = "MIT"
classifiers = [ ..., "License :: OSI Approved :: MIT License", ... ]
```

The wheel's `.dist-info` entry list, complete — four entries, none of which is a licence:

```
vkdownloader-0.1.0.dist-info/METADATA  (6257 bytes)
vkdownloader-0.1.0.dist-info/WHEEL  (87 bytes)
vkdownloader-0.1.0.dist-info/entry_points.txt  (54 bytes)
vkdownloader-0.1.0.dist-info/RECORD  (3117 bytes)
```

The metadata header, complete:

```
Metadata-Version: 2.5
Name: vkdownloader
Version: 0.1.0
Summary: VK Video Downloader - Download videos from VKontakte
Author: VK Video Downloader Team
License-Expression: MIT
Keywords: downloader,playwright,video,vkontakte
Classifier: Development Status :: 3 - Alpha
Classifier: Intended Audience :: Developers
Classifier: License :: OSI Approved :: MIT License
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3.12
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
```

`License-Expression: MIT` is present. `License-File` appears nowhere in the block.

The two existence answers from the source tree and from both artifacts:

```
$ git ls-files | Select-String -Pattern "(?i)licen|copying|notice"
.kilo/skills/agent-md-refactor/LICENSE
.kilo/skills/artifacts-builder/LICENSE
.kilo/skills/artifacts-builder/LICENSE.txt
```

All three are third-party licence files belonging to bundled agent skills under `.kilo/skills/`; none
is this project's, and `.kilo/` is an excluded sdist prefix
(`tests/test_packaging.py:186-190`), so none can serve.

```
licence text in the wheel:  NONE
licence text in the sdist:  NONE
```

The sdist is 73 files: `.env.example` 1, `.gitignore` 1, `.python-version` 1, `PKG-INFO` 1,
`README.md` 1, `pyproject.toml` 1, `uv.lock` 1, `docs` 13, `src` 31, `tests` 22. No licence file
among them, and none can be added without an `include` entry at `pyproject.toml:52-65`, which
`test_sdist_entry_set_matches_the_manifest` pins exactly.

**Recommendation:** Add a `LICENSE` file at the repository root with the MIT text and point the
manifest at it using the PEP 639 `license-files` key. The builder will then emit a `License-File`
entry and hatchling will add the file to the sdist automatically; both changes are picked up by the
existing packaging test with the two expected-set additions it already demands. While doing it,
delete the now-redundant `License :: OSI Approved :: MIT License` classifier at `pyproject.toml:15`
— PEP 639 tooling treats the classifier as a deprecated duplicate of the `License-Expression` field
and some index validators warn on having both.

---

### DEP-010: The one runtime data file the product loads is declared in both build targets; its loss is reported at no log level

| Field | Value |
|-------|-------|
| **ID** | DEP-010 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py:32,112-114` |
| **Classification** | mandatory |

**Description:** `src/vkdownloader/infrastructure/browser.py:32` derives a path from the module's
own location — `Path(__file__).parent.parent / "stealth.min.js"` — and `:112-113` reads it when
`create_stealth_page` runs. This is the only file the installed product reads by a path derived
from its own location.

The **declaration** half of this question is satisfied and is not filed: `pyproject.toml:44` names
it in `[tool.hatch.build.targets.wheel].artifacts`, `pyproject.toml:55` names it in the sdist
`include` list, and the built artifacts carry it at `vkdownloader/stealth.min.js` (2 608 bytes) and
`src/vkdownloader/stealth.min.js` respectively.

The **observability** half is not. The guard is `if self._stealth_path.exists():` and the
`else`-equivalent is nothing: no `else` branch, no `warning`, no `error`. The only log line in
`create_stealth_page` that mentions the script is `logger.debug("stealth_script_applied")` at
line 114, which fires on the *present* path. When the file is absent the product proceeds to launch
a page with no anti-automation masking, at default log level, with nothing written anywhere. The
consequence is a silent capability downgrade: the download proceeds, the CDN's automation detection
starts rejecting the request, and the operator sees a generic extraction failure with no line
anywhere saying the masking script did not load.

**Evidence (R3 — extract every runtime-read path from the built wheel, read the admitting
declaration, then read the load site):**

(a) The runtime-read file, from the wheel's central directory, with its size:

```
vkdownloader/stealth.min.js    2608
```

There is no other path derived from `__file__` in the package. The only other `__file__` use in
`src/` is `src/vkdownloader/utils/security.py:65`, which computes a repository root for a path-safety
warning and reads nothing.

(b) The admitting declarations, both present:

```
pyproject.toml:44   artifacts = ["src/vkdownloader/stealth.min.js"]
pyproject.toml:55   "/src/vkdownloader/stealth.min.js",
```

(c) The load site, the guard's form, and the reporting level:

```python
# src/vkdownloader/infrastructure/browser.py
32:        self._stealth_path = Path(__file__).parent.parent / "stealth.min.js"
...
112:        if self._stealth_path.exists():
113:            await page.add_init_script(path=str(self._stealth_path))
114:            logger.debug("stealth_script_applied")
115:
116:        return page
```

Guard form: an `if self._stealth_path.exists():` with no `else`. Reporting level on the taken
branch: `debug`. Reporting level on the not-taken branch: **none at any level**. The path that would
fail without the file is unreachable by construction, which is why the guard exists — the finding is
that the product's stated requirement (that this file "must ship in both artefacts",
`pyproject.toml:41-42`) is defended against a packaging regression by nothing observable.

**Recommendation:** Add an `else` that logs the absence at `warning` — the level
`config.py`'s logger already uses for comparable degradations such as `ffmpeg_not_found`
(`src/vkdownloader/services/ffmpeg_utils.py:81-88` logs `warning` for exactly this shape of event).
One branch, four lines, and the failure mode becomes visible in the same log stream as the rest of
the run. The `exists()` guard should stay: the file being optional at runtime is a reasonable design
choice, but it should be a *stated* choice rather than an invisible one.

---

### DEP-011: The ffmpeg binary is discovered at runtime with no version constraint recorded anywhere in the repository

| Field | Value |
|-------|-------|
| **ID** | DEP-011 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py:66-89`, `docs/01-tools/installation.md:26-48`, `README.md:112` |
| **Classification** | advisory |

**Description:** R7's question — is anything invoked, and is the rule set the project does use
already covering the named tool's function — has an external-binary arm that the declaration
mechanisms cannot express. `ffmpeg` is not a distribution; it is a native binary the product
discovers on `PATH` and executes. The product's entire declaration of what it needs from that binary
is the following:

```python
# src/vkdownloader/services/ffmpeg_utils.py
80:        _ffmpeg_available = shutil.which("ffmpeg") is not None
```

Presence, never version. No minimum version is recorded in `pyproject.toml`, in `docs/`, in
`README.md`, in the CI workflow, or in a test. A repository-wide search for a version constraint on
the binary returns exactly one hit, and it is a `shutil.which` docstring:

```
$ git grep -n -I -E "\-version|version_info|shutil.which" -- src/
src/vkdownloader/services/ffmpeg_utils.py:69:    Results are cached within the process so the (cheap) ``shutil.which``
src/vkdownloader/services/ffmpeg_utils.py:80:        _ffmpeg_available = shutil.which("ffmpeg") is not None
```

This is filed strictly as a pinning-policy question, and the runtime consequence is **not** re-derived
here. Phase 05 owns the observed failure (`TRN-001`, CRITICAL): the installed build
`N-117624-g9eb7e8d2a4-20241023` does not honour `ffmpeg @<argfile>`, so `--method ffmpeg` silently
downgrades to the segment downloader. What belongs to this phase is the observation that made that
failure shippable: the product added a capability against a specific behaviour of an unbounded
external tool and recorded nothing that would have told the next maintainer which builds are
trustworthy. The documentation prescribes install commands (`choco install ffmpeg`,
`brew install ffmpeg`, `apt-get install ffmpeg` — `docs/01-tools/installation.md:32,37,42`) with no
version, and the only verification offered is `ffmpeg -version` at line 47, whose output nothing
compares against.

A second instance of the same shape: the Playwright browser binaries. `docs/01-tools/installation.md:74`
prescribes `playwright install chromium`, unpinned; the `playwright` distribution is declared at
`pyproject.toml:20` with `>=1.45.0` and no ceiling, so the browser build that gets installed is
whatever the resolver picked on the day of the sync.

**Evidence (R5/R7 — read the manifest, then search the bounded corpus for a version constraint; the
runtime behaviour is phase 05's):**

| Subject | Declaration in `pyproject.toml` | Version constraint recorded | Enforced by |
|---|---|---|---|
| `ffmpeg` (native binary) | none possible | **none** | nothing |
| Playwright browser build | transitively, via `playwright>=1.45.0` (line 20) | distribution floor only, no ceiling | nothing |
| `ffprobe` | none | none | nothing — and no `ffprobe` reference exists in `src/` or `tests/` at all |

R6's projection does not change this: `uv sync --dry-run` exits 0 with "Would make no changes", so
the Python-side default provisioning path is sound. The gap is entirely on the native-binary side,
which no Python manifest can close.

**Recommendation:** Record the constraint where a developer will meet it, not in code. Add one line
to `docs/01-tools/installation.md`'s ffmpeg section stating the minimum build the product is
verified against (derived from the `N-117624` behaviour phase 05 recorded, plus whatever the
argfile path needs), and turn the existing `ffmpeg -version` check at line 47 into a check that
compares. For a CLI, a `--version`-style preflight that warns when the discovered binary is older
than the recorded floor costs about ten lines in `ffmpeg_utils.py` next to
`check_ffmpeg_available()` and converts an entire class of silent downgrade into a visible warning.
This is deliberately not a hard failure: a user on an older distro build should get a clear message,
not a refusal to run.

---

### DEP-012: Seven index-tracked files at the repository root are read by no tool, and one of them runs `git add -A`

| Field | Value |
|-------|-------|
| **ID** | DEP-012 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `%PYFILE%`, `Continue`, `Continue=SilentlyContinue`, `ErrorPreference=SilentlyContinue`, `cli_ruff_output.txt`, `temp_tests_output.txt`, `stage_and_commit.bat` |
| **Classification** | advisory |

**Description:** R12 requires every index-tracked entry no tool reads to be identified with its
content read. `git ls-files` filtered to root-level entries returns 13 paths; six of them are the
project (`pyproject.toml`, `uv.lock`, `README.md`, `.gitignore`, `.python-version`,
`.env.example`) and seven are not. Each was read in full. None is referenced by any tracked file,
none is imported, and none is a Python module — `%PYFILE%` is a script body with a `.py` script's
content and no `.py` name, so it is inert to the import system.

The seventh is not inert in the same way. `stage_and_commit.bat:3-6`:

```bat
cd /d C:\py_exp\mko_vkideo
echo Step 1: Stage all changes
git add -A
```

`git add -A` stages every untracked-and-unexcluded path in the working tree. DEP-005 established
that four such paths exist right now (`probe_tmp.py`, `tmp/click_result.txt`, `tmp/click_test.py`,
`tmp/click_test2.py`). A contributor who runs this tracked script commits all four. The script also
hardcodes one contributor's absolute checkout path, and its 30-line commit message describes a
refactor that has long since landed — it is a one-off artifact, not a maintained tool.

**Evidence (R12a — `git ls-files` filtered to root-level entries, each candidate read):**

```
$ git ls-files | Where-Object { $_ -notmatch '/' }
%PYFILE%
.env.example
.gitignore
.python-version
Continue
Continue=SilentlyContinue
ErrorPreference=SilentlyContinue
README.md
cli_ruff_output.txt
pyproject.toml
stage_and_commit.bat
temp_tests_output.txt
uv.lock
```

| File | Size | What it is |
|---|---|---|
| `%PYFILE%` | 97 B | a 2-line append-to-file Python script, left by an unexpanded shell variable |
| `Continue` | 0 B | empty; a PowerShell pipeline fragment |
| `Continue=SilentlyContinue` | 0 B | empty; a PowerShell pipeline fragment |
| `ErrorPreference=SilentlyContinue` | 0 B | empty; a PowerShell pipeline fragment |
| `cli_ruff_output.txt` | 1 078 B | captured ruff output naming `cli_test.py` / `cli_test2.py`, files that no longer exist |
| `temp_tests_output.txt` | 3 336 B | captured pytest output, ending `325 passed in 12.75s` — a stale count |
| `stage_and_commit.bat` | 1 342 B | one-off `git add -A` + `git commit` script with a hardcoded absolute path |

Per-candidate ignore verdict: **none of the seven is named by any working ignore rule** — see
DEP-004, which files the mechanism and the proof.

Did any reach the built source archive? **No.** The 73-file enumeration in DEP-009 lists every
member; none of the seven is among them, and `tests/test_packaging.py:191-200` independently pins
all seven names in `FORBIDDEN_SDIST_ENTRIES`. The sdist allow-list at `pyproject.toml:52-65` is the
mechanism that keeps them out, and it is working.

**Recommendation:** Delete all seven from the index and the working tree — `git rm --cached` plus a
local delete — as part of the DEP-004 fix, which already rewrites the rules meant to describe them.
`stage_and_commit.bat` is the one to prioritise: it is the mechanism by which the DEP-005 scratch
files would enter the index, and it has no reason to exist in a repository. No tool reads any of
them, so removal is behaviour-free; the only change is that a stale `325 passed` count and a
one-contributor absolute path stop living in the project's history.

---

### DEP-013: Compiled bytecode for six deleted module names survives in the source and test trees, in two coexisting cache generations

| Field | Value |
|-------|-------|
| **ID** | DEP-013 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/__pycache__/`, `tests/__pycache__/`, `__pycache__/` (repository root) |
| **Classification** | advisory |

**Description:** R13 diffs the module-name set derived from compiled cache files against the source
basenames. Six names have no source beside them, and two cache generations coexist, so a cleanup
that clears one leaves the other and the class survives the fix.

**Evidence (R13 — enumerate compiled cache files with the cache directories excluded from every
other row's search, strip the interpreter and test-plugin tags, diff against the source basenames):**

Compiled file count under the source and test trees, excluding `.venv/`, `.kilo/node_modules/`,
`.ai/builders/` and `.temp/`: **77**.

Orphaned module names — 8 files across 6 names, every one with no `.py` beside it:

| Orphaned name | Cache file | Nearest existing source |
|---|---|---|
| `adaptive_throttle` | `src/vkdownloader/infrastructure/__pycache__/adaptive_throttle.cpython-312.pyc` | none — `infrastructure/` holds only `__init__.py`, `browser.py`, `network_monitor.py` |
| `http_client` | `src/vkdownloader/infrastructure/__pycache__/http_client.cpython-312.pyc` | none — same directory |
| `test_http_client` | `tests/__pycache__/test_http_client.cpython-312-pytest-9.1.1.pyc` | none — no `tests/test_http_client.py` |
| `test_smoke_resume` | `tests/__pycache__/test_smoke_resume.cpython-312-pytest-9.0.3.pyc` | none — no `tests/test_smoke_resume.py` |
| `test_mock_vk_server` | `tests/integration/__pycache__/test_mock_vk_server.cpython-312-pytest-9.0.3.pyc` and `-9.1.1.pyc` | none — `tests/integration/` holds only `__init__.py` |
| `_test`, `main`, `test_script` | `__pycache__/` at the repository root, 3 files | none — no such `.py` at the root |

Coexisting cache generations: `cpython-312-pytest-9.0.3` and `cpython-312-pytest-9.1.1` both sit in
`tests/__pycache__` and in `tests/integration/__pycache__`. The plugin version changed between runs
and neither generation was cleared. The repository-root `__pycache__` is a fourth location, holding
bytecode for scripts that no longer exist at the root.

Ignore verdict for the class: **already covered, and that is why this is LOW.** `.gitignore:2`
declares `__pycache__/` and `.gitignore:3` declares `*.py[oc]`, so all 77 files are untracked *and*
ignored — confirmed by `git status --porcelain --ignored`, which lists every `__pycache__/`
directory under `!!`. Do any reach a built artifact? **No.** The wheel's 35-entry listing has none
(DEP-008) and the sdist's 73 files have none (DEP-009): the `include` allow-list
(`pyproject.toml:52-65`) admits directories, but hatchling excludes `__pycache__` by default, and
the enumeration confirms it empirically rather than by assumption. CPython will not import a
`__pycache__/*.pyc` whose source is absent, so the files are inert at runtime as well as at build
time. The subject is disk hygiene only.

**Recommendation:** Delete the three `__pycache__` directories that no longer have a full set of
sources under them — the repository-root one, and the two `tests/` ones that hold the 9.0.3
generation — or simply run `find . -name __pycache__ -type d -prune -exec rm -rf {} +` outside
`.venv/`. Worth doing once and not worth a rule: the ignore coverage is already correct, so this is
a one-time tidy, not a gate that should be added. If the two-generation split recurs regularly, the
cause is a pytest upgrade in the environment rather than the repository, and nothing here needs to
change.

---

### DEP-014: The shipped README and the installation guide both promise Python 3.10+ while the artifact they ship in requires 3.12

| Field | Value |
|-------|-------|
| **ID** | DEP-014 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `README.md:111`, `docs/01-tools/installation.md:20`, `pyproject.toml:6` |
| **Classification** | mandatory |

**Description:** A document claim about packaging, provisioning, publication or installation is this
phase's subject, and this one ships inside the wheel. `pyproject.toml:6` declares
`requires-python = ">=3.12"`, and the built metadata carries `Requires-Python: >=3.12`. Two documents
a user reads before installing tell them something different:

- `README.md:111` — this file is `readme = "README.md"` (`pyproject.toml:5`), so its `## Requirements`
  section is embedded verbatim in the wheel's `METADATA` long description, on the index listing and
  on `pip show vkdownloader`. It reads `- Python 3.10+`.
- `docs/01-tools/installation.md:20` — under `## Prerequisites`, it reads `- Python 3.10 or higher`.

The same installation guide's step 2 (`docs/01-tools/installation.md:61-64`) offers
`pip install -e .` as the supported path. On Python 3.10 or 3.11 that command fails at resolution
with a `Requires-Python` error, after the user has followed the guide's prerequisite check and
believed it passed. The wheel's own classifier list corroborates the real floor —
`Programming Language :: Python :: 3.12` is the only version classifier present.

**Evidence (R2 — read the built artifact's metadata block, and the source documents that feed it):**

```
pyproject.toml:6      requires-python = ">=3.12"
```

From the built wheel's `METADATA`:

```
Requires-Python: >=3.12
Classifier: Programming Language :: Python :: 3
Classifier: Programming Language :: Python :: 3.12
```

The conflicting claims, located by line:

```
$ Select-String -Path README.md -Pattern "Python 3"
README.md:111:- Python 3.10+

$ Select-String -Path docs\01-tools\installation.md -Pattern "Python 3"
installation.md:20: - Python 3.10 or higher
```

Both files are in the sdist — `README.md` via `pyproject.toml:61` and the whole `docs` tree via
`pyproject.toml:57` — so the same contradiction is reproduced in the source archive, not only in
the index listing. The sdist's 73-file enumeration (DEP-009) confirms both are present.

**Recommendation:** Change both lines to `3.12` in the same commit. `README.md:111` becomes
`- Python 3.12+` and `docs/01-tools/installation.md:20` becomes `- Python 3.12 or higher`. Two
characters each. If the maintainer would rather support 3.10, the fix is the other direction —
relax `pyproject.toml:6` and re-verify — but that is a code decision, not a documentation one, and
the `.python-version` pin and the single `3.12` classifier both currently say 3.12. `README.md:113`
("Playwright browsers (auto-installed)") is worth a second look in the same pass: nothing in the
codebase installs browsers automatically — a repository-wide search for `playwright install`
returns exactly one hit, and it is the manual step at `docs/01-tools/installation.md:74` — so the
accurate wording is the one the installation guide already uses.

---

### DEP-015: The gate set has a `release` trigger that produces and verifies no artifact, and no build-and-publish job exists

| Field | Value |
|-------|-------|
| **ID** | DEP-015 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.github/workflows/packaging-check.yml:31-32,50-53` |
| **Classification** | advisory |

**Description:** R9's job-class list includes `build and publish`. Half of it exists. The job builds
both artifacts and asserts their composition — genuinely useful work — but it does not upload
anything, does not record what it built, and does not verify anything about a published artifact.
The `release: types: [published]` trigger at line 31-32 fires *after* a human has already published
a GitHub Release, which means by the time this job runs the release exists. It re-derives the answer
from the released ref on a different machine at a different moment and asserts only that the entry
sets match.

The consequence: nothing in the repository ties what an installer downloads to what CI checked. A
release is assembled and uploaded by hand, from a working tree whose uncommitted state is unknown;
the green check that accompanies the release attests to a rebuild, not to the upload. A
`git status`-dirty tree, a stale `uv.lock`, or a different `uv` version on the uploader's machine
all produce a release that the green check cannot detect. `permissions: contents: read` at line 34-35
confirms the job is deliberately unable to publish.

**Evidence (R9 — per definition, the trigger, the per-job commands and the failure condition):**

```
packaging-check.yml
  on.push / on.pull_request  paths: pyproject.toml, uv.lock, .python-version, README.md,
                                       .env.example, src/**, tests/**, docs/**
  on.release                 types: [published]                    <-- fires after publication
  permissions: contents: read                                      <-- cannot publish
  jobs.packaging-check:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - uses: actions/setup-python@v5
      - run: uv sync --locked                                     (line 51)
      - run: uv run pytest tests/test_packaging.py -v             (line 53)
      no upload, no hash recording, no publish action
```

No publish tooling is configured anywhere in the repository:

```
$ git grep -n -I -E "twine|hatch publish|uv publish|__token__|PYPI_|pypi.org" -- . ':!uv.lock' ':!.kilo'
tests/test_packaging.py:525:NETWORK_BUILD_ERROR = "error: failed to fetch https://pypi.org/simple/hatchling/"
```

The single hit is a test fixture string, not a configuration. There is no `[project.urls]`, no
`publish` table and no upload action in either definition.

R9's class table therefore records `build and publish` as **partial**: build yes, publish no. The
build half is real — the local run of the exact command produced 14 passed, exit 0, and
`tests/test_packaging.py:142-145` documents that the wheel's entry set was previously correct only
by accident and is now pinned.

**Recommendation:** Decide which of two states the project wants, and make the configuration say
so. Either (a) the package is not published from CI and the GitHub Release is the release — in
which case drop the `release: types: [published]` trigger, because a check that fires after the fact
and can act on nothing gives false assurance, and add a `steps` upload of the two built artifacts as
CI artifacts so the exact bytes that were checked are retained; or (b) the package is published to
an index, in which case add a `build` job that runs on tags, records `sha256sum` of both artifacts
into the job summary, and publishes with trusted publishing so no long-lived token exists in the
repository. Option (a) is two lines and matches the project's current state; option (b) is a
publishing decision, not a configuration one, and should be made deliberately.

---

### DEP-016: The version is declared twice — in the manifest and in `__init__.py` — with nothing that keeps them equal

| Field | Value |
|-------|-------|
| **ID** | DEP-016 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/__init__.py:3`, `pyproject.toml:3`, `docs/01-tools/installation.md:154-157` |
| **Classification** | advisory |

**Description:** The distribution version has two sources of truth and no check between them.
`pyproject.toml:3` declares `version = "0.1.0"`, which is what the builder stamps into the wheel's
`METADATA` and the sdist's `PKG-INFO`. `src/vkdownloader/__init__.py:3` hardcodes
`__version__ = "0.1.0"`, which is a second, independent copy that ships as ordinary package code.
`docs/01-tools/installation.md:154-157` documents exactly that attribute as the post-install
verification step, so a user is told to check a value that nothing keeps in sync.

The consequence: the next release bump updates one copy and the published package's own
`__version__` reports the previous release, while `importlib.metadata.version("vkdownloader")`
reports the new one. Two correct answers from two sources is the failure mode; neither
`tests/test_packaging.py` (which pins entry sets, not versions) nor any workflow compares them.

**Evidence (R2 — read the built artifact's metadata block against the package source):**

```
pyproject.toml:3            version = "0.1.0"
src/vkdownloader/__init__.py:3   __version__ = "0.1.0"
```

From the built wheel's `METADATA`:

```
Name: vkdownloader
Version: 0.1.0
```

and from the wheel's payload, the shipped copy of the same value:

```
vkdownloader/__init__.py    118 bytes
```

```
$ Get-Content src\vkdownloader\__init__.py
"""VK Video Downloader - Download videos from vkvideo.ru with quality selection support."""

__version__ = "0.1.0"
```

The two agree today. That is the state, not the guarantee: nothing in the repository would report it
if they diverged.

**Recommendation:** Delete `__version__` from `src/vkdownloader/__init__.py:3` and derive it —
`__version__ = importlib.metadata.version("vkdownloader")` — so the manifest stays the single
source and the documented verification step keeps working. This costs one import and removes a
class of release-day error. If the project prefers the attribute to stay dependency-free, the
alternative is a one-line assertion in `tests/test_packaging.py` comparing `__version__` against the
parsed `pyproject.toml` value, which turns a silent drift into a red build.

---

## Documented skips

Emitted in the fixed wording, because under `problems-only` silence reads as "no finding".

1. **Live advisory-database access** (which dependencies carry a known vulnerability) — *not
   performed.* It requires a network an advisory database is not reachable from here. **No
   vulnerability count is asserted.** What remains verifiable, and was verified: the resolved
   dependency set is 41 locked packages (`uv.lock`, format version 1, revision 3), every one of the
   40 registry-sourced entries carries a `sha256` hash on every `sdist` and `wheel` artifact
   (hash-presence count: 40 of 40; missing-hash list: empty), and `uv lock --check` exits 0 with
   "Resolved 41 packages in 2ms", so the resolution record is in sync with the manifest. The
   fileable subject is the absence of a scanner from the gate set, filed as DEP-003.

2. **Publishing to a real index** (what a real release would expose) — *not performed.* Nothing was
   uploaded anywhere and no index was contacted. What remains verifiable, and was verified: the
   archive's measured composition from the build and enumeration — 73 files in the sdist, 35
   entries in the wheel, per-top-level counts and byte totals recorded in DEP-008 and DEP-009, with
   no vendored tree, no worktree, no audit corpus and no user data among them. The publication
   consequence is stated as a projection only, in DEP-015.

3. **A real install from source** (what a consumer's build does with the archive) — *not performed
   offline.* No separate environment was constructed and the archive was not installed into one.
   The R11 invocation-form matrix (both the declared form and the form the package structure
   permits, five cases each) was executed against the current editable development environment, not
   against a clean install of the built wheel. What remains
   verifiable, and was verified: the archive's contents, and the fact that the product's own
   `.venv` has the console script and the module form both working with identical exit statuses
   (0 for `--help`, 2 for no arguments, an unknown command, and a missing required argument on both
   `download` and `batch`). The fileable subject is the archive's contents, enumerated above.

4. **Scratch directory outside the repository** (R1's stated prerequisite) — *deviation recorded.*
   The environment denies writes to any path outside the workspace, so `uv build --out-dir` was
   pointed at `.temp/dist/` instead. `.temp/` is excluded by the repository-carried rule at
   `.gitignore:40` and by `[tool.ruff] extend-exclude` at `pyproject.toml:70`, and the sdist
   `include` allow-list (`pyproject.toml:52-65`) has no entry that could admit it. A clean
   working-tree check was run after the build and the four untracked-and-unexcluded paths are
   unchanged from their pre-build state (DEP-005 lists them); no build residue entered the index.
   `tests/test_packaging.py:397-415` performs the same build into a
   `tempfile.mkdtemp()` path outside the repository and asserts the project's top-level entries are
   unchanged afterwards, and that module passed in the run recorded in the baselines table.

5. **Live behaviour of a third-party transport, downloader or browser library** — *out of scope by
   design.* `yt_dlp`, `aiohttp` and `playwright` were read as declarations and as import sites;
   nothing about their runtime behaviour, their network behaviour or their vulnerability status is
   asserted or guessed here.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 10 |
| LOW | 3 |

## Mandatory Fixes

- **DEP-001** (HIGH, SPEC-DEVIATION) — lint, format check and type check are documented as the
  project's verification and are run by no automation. Add them to the existing `packaging-check`
  job; start with `mypy src`, which is currently green.
- **DEP-002** (HIGH, SPEC-DEVIATION) — no job executes the test suite; the only pytest invocation
  collects 14 of 502. Add `uv run pytest tests/` on the filter that already admits `tests/**`.
  (Seam: whether the tests prove anything is phase 10's.)
- **DEP-004** (HIGH, SPEC-DEVIATION) — the seven debris rules in `.gitignore:59-65` are literal
  patterns because each carries an inline `#` comment; the rule that claims to stop them coming
  back does not. Move the comments above the patterns and `git rm --cached` the files.
- **DEP-005** (MEDIUM, SPEC-DEVIATION) — four untracked-and-unexcluded scratch paths at the
  repository root already make `uv run ruff check .` exit 1. Add `/tmp/` and `/probe_tmp.py` to
  `.gitignore` and delete them.
- **DEP-007** (MEDIUM, SPEC-DEVIATION) — `tests/test_config.py:472` imports `annotated_types`, which
  no declaration mechanism names; it resolves only as a transitive of `pydantic`.
  `uv add --dev annotated-types`.
- **DEP-010** (MEDIUM, BEST-PRACTICE) — the runtime-read `stealth.min.js` is correctly declared in
  both build targets, but its absence from an installed product is reported at no log level. Add the
  `else` branch at `browser.py:112` logging a `warning`.
- **DEP-014** (MEDIUM, DOC-UPDATE) — `README.md:111` and `docs/01-tools/installation.md:20` promise
  Python 3.10+; the artifact they ship in requires `>=3.12`.

## Advisory Recommendations

- **DEP-003** (MEDIUM) — no dependency scanner, secret scanner, update automation, pre-commit
  control or `CODEOWNERS`. Start with a 6-line `dependabot.yml` for the `uv` ecosystem.
- **DEP-006** (MEDIUM) — `.kilo/agent-manager.json` and `.kilo/.gitignore` are excluded only by an
  untracked nested ignore file, so a clean checkout has no such exclusion. Three lines in the root
  `.gitignore`.
- **DEP-008** (MEDIUM) — no PEP 561 marker in either artifact, so the annotations the project
  maintains never reach a consumer. Add `src/vkdownloader/py.typed` and one entry to
  `EXPECTED_WHEEL_ENTRIES`.
- **DEP-009** (MEDIUM) — both artifacts assert `License-Expression: MIT` and ship no licence text.
  Add a root `LICENSE` and the PEP 639 `license-files` key.
- **DEP-011** (MEDIUM) — `ffmpeg` is discovered by `shutil.which` with no version constraint
  recorded anywhere. Record a minimum build in the installation guide and warn below it.
  (Cross-reference: phase 05's `TRN-001` is the observed failure; only the pinning policy is
  filed here.)
- **DEP-015** (MEDIUM) — the `release` trigger fires after publication and can act on nothing; no
  build-and-publish job exists.
- **DEP-012** (LOW) — seven index-tracked root files no tool reads, one of which runs
  `git add -A` over the DEP-005 scratch paths.
- **DEP-013** (LOW) — compiled bytecode for six deleted module names across two coexisting cache
  generations. Already correctly ignored; a one-time tidy only.
- **DEP-016** (LOW) — the version is declared twice with nothing keeping the copies equal.

## Doc Updates Needed

- **DEP-014** — `README.md:111` (`- Python 3.10+`) and `docs/01-tools/installation.md:20`
  (`- Python 3.10 or higher`) must state `3.12` to match `pyproject.toml:6` and the built
  `Requires-Python` field. `README.md:113`'s "Playwright browsers (auto-installed)" is also
  inaccurate as written: `docs/01-tools/installation.md:74` prescribes `playwright install chromium`
  as a separate step, and nothing in the codebase invokes it.
- **DEP-011** — `docs/01-tools/installation.md:26-48` prescribes three ffmpeg install commands and
  a `ffmpeg -version` check with no version floor, which is the documentation half of the pinning
  gap.

## Cross-phase references (not re-filed here)

- **Phase 06** owns the runtime credential and secret handling. Its SEC-005/007 concerns a value
  transformed on one surface and not another, and a real `yt_dlp.utils.DownloadError` reaching a log
  record verbatim. This phase checked only whether the declared dependency set covers what is
  imported, and it does for `yt_dlp` (`pyproject.toml:27`, reached at
  `src/vkdownloader/services/extractor.py:7` and `src/vkdownloader/services/ytdlp_downloader.py`).
  No finding is filed on the leak itself.
- **Phase 05** owns subprocess, ffmpeg and browser invocation. Its `TRN-001` (CRITICAL) is the
  observed `ffmpeg @<argfile>` downgrade. DEP-011 files only the pinning-policy consequence: no
  version constraint is recorded for the discovered binary. The argfile behaviour was not
  re-derived.
- **Phase 09** owns the mypy profile and the unmarked-dependency policy. Its `QLT-009` (the three
  `Any` keys absent from the profile, `yt_dlp` the sole unmarked dependency) is adjacent to R5 and
  is cited, not re-filed. The mypy profile's absence of those keys is why `uv run mypy src tests`
  reports 55 errors in `tests/` while `uv run mypy src` is clean.
- **Phase 10** owns the tests themselves and the test-execution job. DEP-002 files only the
  catalogue gap — that no definition executes the suite — and makes no claim about what the 502
  collected tests prove.
- **Phase 02** owns settings and env parsing; `CFG-001`/`CFG-002` are fixed as of `ea44b3d` and were
  not re-examined.
- **`.ai/plans/done/01-confirmed-code-defects_DONE.md`** is the archived defect register. Its line
  210 describes an earlier manifest shape (`[project.optional-dependencies] dev` holding `ruff`,
  `mypy`, `pytest`, `pytest-asyncio`, `black`, `isort`, `pyyaml`) and its line 216 describes a
  `uv sync` projection that uninstalled the verification tooling. Neither describes the manifest as
  it stands: the dev group is now `[dependency-groups].dev` at `pyproject.toml:110-116` with four
  names and no `black`, `isort` or `pyyaml`, and `uv sync --dry-run` currently reports "Would make
  no changes" with all four verification commands resolving. The historical formatters are not
  present, so R7's "a formatter declared beside a linter that already owns its function" produced
  no finding. The register is a `.ai/plans/done/` document and is cited, not filed.
- **`docs/STRUCT.md`** is known stale — it omits `ytdlp_downloader.py` — which is a structural
  description and therefore phase 09's. It *is* accurate on the one point this phase needed from
  it: `docs/STRUCT.md:11` records `__main__.py` as the `python -m vkdownloader` entry point, so the
  second invocation form R11 exercised is documented even though the manifest declares only
  `[project.scripts]`.
