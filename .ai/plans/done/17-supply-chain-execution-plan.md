# Execution Plan — Plan 16 Supply Chain Audit Fixes

> **Plan file:** `.ai/plans/16-supply-chain-audit-fixes_fix.md`
> **Current HEAD:** `189614a` (43 commits past the plan's §0 reference `2289f6f`)
> **Status:** The plan's §0 table is stale. Several blocks were incidentally resolved by Plan 13/14 commits between `2289f6f` and `189614a`.

## Code Context (from Auditor)

### Baseline gates (all GREEN at HEAD `189614a`)

| Command | Result | Exit |
|---|---|---|
| `uv run pytest -q -rs` | 1084 passed, 3 skipped | 0 |
| `uv run ruff check src tests` | All checks passed! | 0 |
| `uv run ruff format --check src tests` | 56 files already formatted | 0 |
| `uv run mypy src` | Success: no issues found in 32 source files | 0 |
| `uv run pytest tests/test_packaging.py -q` | 14 passed | 0 |
| `uv lock --check` | Resolved 41 packages | 0 |

### Block status — final

| Block | Finding | Status | Commit | Notes |
|---|---|---|---|---|
| B0 | format gate | **DONE** | (no commit) | GREEN at HEAD — MOOT, no commit needed |
| B1 | DEP-004 + DEP-012 | **DONE** | `9f1095b` | 8 `.gitignore` rules fixed; `stage_and_commit.bat` removed |
| B2 | DEP-005 + DEP-006 | **DONE** | `3a1788d` | Root `.gitignore` scratch + agent block entries added |
| B3 | DEP-001 + DEP-002 | **DONE** | `9a218ae` | CI Python → 3.14; lint/format/mypy/coverage gates added |
| B4 | DEP-008 | **DONE** | `22c6228` | `py.typed` created; frozensets updated (71 sdist / 34 wheel / 4 dist-info) |
| B5 | DEP-009 | **DONE** | `22c6228` | `LICENSE` created; trove classifier removed; `license-files` declared; frozensets updated (72 sdist / 34 wheel / 5 dist-info) |
| B6 | DEP-007 | **DONE** | `eaea694` | `annotated-types` declared in dev group |
| B7 | DEP-010 | **DONE** | (earlier) | Stealth diagnostic in `browser.py` |
| B8 docs | ffmpeg wording + X-01–X-05 | **DONE** | `fec11e4` | ffmpeg requirement stated conditionally in README + installation.md |
| B9 | DEP-011 behaviour | **DONE** | (earlier) | OSError arms present; `check_ffmpeg_available()` return value consumed |
| B10 | DEP-014 | **DONE** | `5143dfc` | Python floor → 3.14; dev-tool floors raised; CI Python updated |
| B11 | DEP-016 | **DONE** | `22c6228` | `__version__` derived from `importlib.metadata.version()` with honest fallback |
| B12 | DEP-003 | **DONE** | `71820ab` | `.github/dependabot.yml` added; pip-audit advisory scan step added |
| B13 | DEP-015 | **DONE** | `49fd20a` | `release: types: [published]` removed; `uv build --out-dir dist/` + upload step added |
| B14 | DEP-013 | **DONE** | (no commit) | Bytecode cache cleaned; 0 orphan `.pyc` files; 0 cache generations |
| B15 | 3.14 toolchain + D-13 | **DONE** | `5143dfc` | All gates pass on 3.14 (1084 passed / 3 skipped); D-13 resolved (floors raised) |

### Critical risks — resolved

All three critical risks have been addressed:

1. **B3 CI Python mismatch** — Resolved by `9a218ae`: CI Python updated to `"3.14"`, matching `requires-python = ">=3.14"`. All 6 gates (lint, format, type, tests, coverage, packaging) now run on 3.14.
2. **B10 dev-tool floors (D-13)** — Resolved by `5143dfc`: Floors raised (`ruff>=0.14.7`, `mypy>=2.0.0`, `pytest>=8.4.0`, `pytest-asyncio>=1.1.0`).
3. **B14 cache generations** — Resolved: All `__pycache__` directories cleaned, 0 orphan `.pyc` files remain.

## Execution order (from §4.1, adjusted)

```
P16-B1  ──► P16-B2           (gitignore, 2 writers)
P16-B3  ──► P16-B12 ──► P16-B13   (.github/workflows, 3 writers)
P16-B4  ──► P16-B5  ──► P16-B6   (frozensets + pyproject.toml, 3 writers)
P16-B15                           (verification, no-commit; resolves D-13)
P16-B8  ──► P16-B10 ──► P16-B11  (README + installation.md, shared files)
P16-B14                           (bytecode tidy, no-commit, parallel-safe)
```

**B0, B7, B9 already done. B8 (X-01–X-05) already done; only docs-wording half remains.**

**pyproject.toml writer serialisation:** B5 (classifiers + license-files) → B6 (dev deps) → B10 (requires-python, target-version, python_version + dev floors)

**installation.md writer serialisation:** B8 (ffmpeg wording) → B10 (Python floor) → B11 (verification section)

**README.md writer serialisation:** B8 (ffmpeg + Playwright rows) → B10 (Python row)

## Block status — final

All 16 blocks (B0–B15 plus B14 no-commit) have been implemented and verified.
Final commit graph:

```
22c6228 supply-chain: ship py.typed PEP 561 marker, LICENSE file, and single version source (B4+B5+B11)
49fd20a build: remove release trigger + add dist build/upload step (B13)
71820ab build: add dependabot for uv ecosystem + advisory scan step (B12)
eaea694 build: declare annotated-types in dev group (B6)
9a218ae build: enforce CI verification gate with coverage (B3)
5143dfc build: raise Python floor to 3.14 + dev-tool floors per D-13 (B10)
fec11e4 fix: state ffmpeg requirement conditionally per D-6/D-7 ruling (B8)
3a1788d fix: complete gitignore coverage for scratch and agent paths (B2)
9f1095b fix: gitignore # rules and remove tracked debris (B1)
```

Final verification (at HEAD `22c6228`):
- `uv run ruff check src tests` — All checks passed
- `uv run ruff format --check src tests` — 56 files already formatted
- `uv run mypy src` — Success, 0 issues in 32 source files
- `uv run pytest tests/test_packaging.py -q` — 14 passed (real build)
- `uv run pytest -q` — 1084 passed, 3 skipped, 0 failed
