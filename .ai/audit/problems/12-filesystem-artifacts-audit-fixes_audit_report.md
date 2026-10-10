# Audit Problems Report — Plan 12: Filesystem Artefacts Audit Fixes

**Audited plan:** `.ai/plans/12-filesystem-artifacts-audit-fixes.md`
**Audit date:** 2026-10-10
**Repository:** `vkdownloader` (`C:\py_exp\mko_vkideo`)
**Plan baseline (per plan):** `HEAD = 58bb7ce` (2026-10-03)
**Current HEAD:** `c64376d` (2026-10-10)
**Scope:** Verification of plan completion and problems found in code/docs during audit.

---

## Plan Completion Status: NOT COMPLETE — 3 OF 12 BLOCKS IMPLEMENTED

| Block | Finding(s) | Commit | Status |
|-------|-----------|--------|--------|
| P12-B1 (ART-010) | Component-wise traversal detection | — | **NOT implemented** |
| P12-B2 (ART-009) | Warning reaches the user | — | **NOT implemented** |
| P12-B3 (ART-001) | Control characters in `sanitize_title` | `17b8831` | ✅ Implemented |
| P12-B4 (ART-011) | Length bound's true scope (option a) | `17b8831` (docstring only) | ⚠️ Partially |
| P12-B5 (ART-014) | Reserved device names / trailing dots | — | **NOT implemented** |
| P12-B6 (ART-003, ART-004, ART-013) | Sweeps match what the tree contains | — | **NOT implemented** |
| P12-B7 (ART-004, ART-005) | Working-directory lifetime | — | **NOT implemented** |
| P12-B8 (ART-012) | Download-stage space, merge multiplier | — | **NOT implemented** |
| P12-B9 (DF-008, ART-002) | Probe and cleanup name the right file | — | **NOT implemented** |
| P12-B10 (DEC-W R1) | Dedup by resolved output filename | — | **NOT implemented** |
| P12-B11 (ART-007) | Confinement posture for artefact paths | — | **NOT implemented** |
| P12-B12 (doc) | STRUCT.md description of ffmpeg_utils | — | **NOT implemented** |

> **Note (updated 2026-10-10):** Since the previous audit write at `HEAD = 8825c69`, a stash
> forward-port execution (see `.ai/plans/20-stash-forward-port-execution.md`) has been
> completed. Three commits landed on `main`:
> - `a9fdd4a` — fix(downloader): thread m3u8_url to yt-dlp child and support worst quality (B9 route-a from plan 07 / stash)
> - `2a8f60b` — fix(extractor): anchor VIDEO_ID_PATTERN and add scheme guard (B12 partial from plan 07 / stash)
> - `8783a8b` — test(ffmpeg_utils): pass m3u8_url to _download_with_ytdlp in boundary test
> - `c64376d` — chore(audit): remove stale audit problems report files
>
> These commits implement stash B9 and B12 **from plan 07** (network resilience), not plan 12's
> own B9/B12 blocks (which are about filesystem artefacts and docs respectively). However, they
> touch files that plan 12 also claims (`ytdlp_downloader.py` for P12-B9, `extractor.py` for B12's
> URL gate), so the line numbers in the "live findings" below have shifted.

### Implementation evidence

**P12-B3 (DONE, from previous audit):** Commit `17b8831` ("fix(security): strip control characters from filesystem-bound titles",
2026-10-05) added a `_CONTROL_CHARS` module constant
(`chr(0)`–`chr(31)` + `chr(127)`) and changed `sanitize_title` to iterate over
`'/\\:*?"<>|' + _CONTROL_CHARS` instead of the hardcoded 9-character set.
Tests added: `test_no_control_character_survives`, `test_newline_and_tab_do_not_produce_multiline`,
`test_null_byte_replaced_not_stripped`.

**P12-B4 (PARTIAL, from previous audit):** The same commit updated the `sanitize_title` docstring to
state "The length bound applies to this title component only, not to the full
output path." This resolves the documentation half of B4 (option-a: record the
scope). No separate decision or test exists for the full B4 acceptance criteria.

**Stash forward-port B9 route-a (DONE — stash B9/NET-003, not P12-B9):** Commit `a9fdd4a`
(2026-10-10) implemented:
1. `_resolve_format_selector()` helper — correctly maps `"worst"` → `"worst"` instead of the
   old inline ternary that silently mapped `"worst"` → `"best"`.
2. `m3u8_url` parameter added to `_download_with_ytdlp()` as 2nd positional argument.
3. `cmd.append(m3u8_url)` instead of `cmd.append(video_url)` (route-a: pass the selected
   HLS playlist URL as yt-dlp's positional argument).
4. `starting_ytdlp_download` logging now uses `m3u8_url` (not `video_url`).
5. Added `ytdlp_format_selected` structured logging with format selector and quality.
6. Updated `download_with_ytdlp_with_resume_fallback` to forward `m3u8_url`.
7. All ~31 test call sites in `test_hls_downloader.py` updated.
8. Added `test_cli_command_format_worst_for_worst_quality` and `test_child_receives_selected_address`.

**Stash forward-port B12 partial (DONE — stash B12/NET-012, not P12-B12):** Commit `2a8f60b`
(2026-10-10) implemented:
1. `_extract_video_segment()` helper with scheme guard (rejects non-http(s) schemes and bare tokens).
2. Anchored `VIDEO_ID_PATTERN` to `^video-(-?\d+)_(\d+)$`.
3. `is_valid_video_url` now uses `_extract_video_segment` + `fullmatch`.
4. `parse_video_id` now uses `_extract_video_segment` + `fullmatch` (preserving `tuple[str, str]` return type).
5. Split `test_extractor.py` accept/reject tables into `_ACCEPT_URLS` / `_REJECT_URLS` with 4 new parametrized test functions.

**Boundary test fix (DONE):** Commit `8783a8b` updated `TestBoundedYtDlpTranscript` boundary
test call sites to pass the new `m3u8_url` argument.

**Cleanup (DONE):** Commit `c64376d` removed three stale audit problems report files for
phases 05, 06, and 10 (no longer relevant).

### Gate verification (at HEAD = `c64376d`)

| Gate | Command | Result |
|------|---------|--------|
| Tests | `uv run pytest tests/ -q -rs` | **1043 passed, 3 skipped**, 1 warning |
| Lint | `uv run ruff check src tests` | **All checks passed!** |
| Format | `uv run ruff format --check src tests` | **55 files already formatted** |
| Type (src) | `uv run mypy src` | **Success: no issues found in 31 source files** |
| Type (tests) | `uv run mypy src tests` | Exit 1 (pre-existing, 86 errors, all in tests) |

The 3 skips are the `D-11` Windows mode oracles (two in `test_config.py`, one in
`test_hls_downloader.py::TestCreateTempCookieFile`), unchanged from baseline.

### Findings still LIVE (re-verified at current HEAD `c64376d`)

Every finding in the plan was re-verified. The stash forward-port commits changed
`ytdlp_downloader.py` and `extractor.py` but did **not** touch the filesystem-artifact findings
these blocks target:

- **ART-010 (P12-B1):** `validate_output_path` still uses `".." in str(path)` substring test
  at two layers (`utils/security.py`), not `path.parts` component-wise test. **Unchanged.**
- **ART-009 (P12-B2):** `repo_root = Path(__file__).resolve().parent.parent.parent`
  in `utils/security.py` still derives to `src/` (one level too deep); the warning at
  `_resolve_output_file` is still suppressed with `warning=False`. **Unchanged.**
- **ART-003 (P12-B6):** `_cleanup_segments` still uses bare `f.unlink()` over `glob("*")`
  in `segment_downloader.py`, no `missing_ok`, no `is_file()` guard. **Unchanged.**
- **ART-003 (tally, P12-B6):** `_tally_and_merge` still uses
  `downloaded_count = len(list(segments_dir.glob("*.ts")))` which counts `batch_*.ts` files. **Unchanged.**
- **ART-004 (P12-B7):** `segments_dir.mkdir()` still runs before the playlist is fetched;
  the `finally` block still only logs, does not sweep. `_clear_stale_segments` still uses
  `glob("*.ts")`, does not sweep `*.ts.tmp`. **Unchanged.**
- **ART-012 (P12-B8):** `_required_merge_bytes` still returns `segment_bytes * 2 + _MERGE_SPACE_MARGIN_BYTES`
  in `ffmpeg_utils.py`. **Unchanged.**
- **ART-002 (P12-B9):** The resume probe in `ytdlp_downloader.py` still checks
  `validated_output.exists()` (the final name), not the `.part` file. No `--no-part` flag exists.
  **Partially affected by stash B9:** the stash's route-a threading means the child now receives
  `m3u8_url` instead of `video_url`, but the probe-target mismatch (`.part` vs final name) is
  **not** addressed by that change — the stash implements stash B9 (NET-003: selected address +
  worst format), not plan 12 B9 (DF-008: probe and cleanup naming). The finding is **still live**
  for plan 12.
- **ART-007 (P12-B11):** `0o600` requested, `0o666` measured. Three `mkdir` sites remain
  with no mode argument; two `os.chmod` call sites survive. **Unchanged.**
- **DEC-W R1 (P12-B10):** No resolved-filename dedup exists. Only exact-URL dedup
  (`seen_urls` set in `batch_downloader.py`) is present — URL-based, not filename-based. **Unchanged.**

### Files affected by stash forward-port that plan 12 must account for

The stash commits changed line numbers in two files that plan 12 also tracks:

| File | Change | Plan 12 impact |
|------|--------|----------------|
| `ytdlp_downloader.py` | Added `_resolve_format_selector` (~16 lines), `m3u8_url` param, logging, docstring updates (~34 insertions) | P12-B9's line references are stale; the probe/cleanup logic is **unchanged** in structure, only shifted down by ~34 lines |
| `extractor.py` | Added `_extract_video_segment` (~19 lines), anchored pattern, restructured `is_valid_video_url` and `parse_video_id` (~40 insertions) | P12-B12 does not touch this file; B12 (stash) is from plan 07 |
| `test_hls_downloader.py` | All `_download_with_ytdlp` call sites updated with `m3u8_url`, new tests added | Test pin `T5` (`TestYtdlpCliCommand` asserts `--no-part` absent) still holds unchanged |
| `test_extractor.py` | Split accept/reject tables, 4 new parametrized tests | No plan 12 impact |

---

## Problem 1 — `docs/STRUCT.md` line 34: Misleading module description — **STILL LIVE (P12-B12)**

**Severity:** LOW (documentation drift, P12-B12)
**File:** `docs/STRUCT.md`, line 34

### Description

The structural map describes `ffmpeg_utils.py` as
`# FFmpeg discovery and stream concatenation`. This omits the shared subprocess
infrastructure (`iter_process_lines`, `cancel_subprocess`) and conflates
"discovery" with "concatenation" in a way that could mislead a reader into
thinking the discovery functions are disposable — the plan (§2.4.4) explicitly
protects the ffmpeg merge engine as permanent surface. The description should name
all three responsibilities: shared subprocess infrastructure, availability
discovery, and segment merge engine.

### Evidence

- `docs/STRUCT.md:34` → `# FFmpeg discovery and stream concatenation`
- `src/vkdownloader/services/ffmpeg_utils.py:65` → `def iter_process_lines(...)`
- `src/vkdownloader/services/ffmpeg_utils.py:58` → `async def cancel_subprocess(...)`
- `src/vkdownloader/services/ffmpeg_utils.py:81` → `def _probe_ffmpeg(...)`

This was **not** fixed by the stash forward-port commits. The STRUCT.md line
remains unchanged.

### Plan's role

P12-B12. The plan records this as a one-line doc fix in §2.4.4. Not yet executed.

---

## Problem 2 — `docs/01-tools/vkdownloader-overview.md` line 16: Misleading ffmpeg description — **STILL LIVE**

**Severity:** LOW (documentation drift)
**File:** `docs/01-tools/vkdownloader-overview.md`, line 16

### Description

The overview states the product "combines yt-dlp for stream extraction with
ffmpeg for **direct HLS-to-MP4 conversion**." After TRN-001 (removal of
`DownloadMethod.FFMPEG`), ffmpeg is no longer a download transport — it is
exclusively the post-download segment merge engine. The phrase "direct HLS-to-
MP4 conversion" echoes the retired transport.

### Plan's role

Not in scope for P12-B12 (which only touches `docs/STRUCT.md`), but flagged as
documentation drift.

---

## Problem 3 — Stale module line counts in `docs/01-tools/vkdownloader-overview.md` — **STILL LIVE, values shifted**

**Severity:** LOW (documentation drift)
**File:** `docs/01-tools/vkdownloader-overview.md`, lines 283–287

### Evidence (updated counts at HEAD = `c64376d`)

| Module | Doc claim | Actual (at `c64376d`) |
|---|---|---|
| `downloader.py` | ~350 lines | 360 lines |
| `ytdlp_downloader.py` | ~722 lines | ~1440 lines (grew from stash B9 additions) |
| `segment_downloader.py` | ~901 lines | ~1275 lines |
| `ffmpeg_utils.py` | ~360 lines | 646 lines |

---

## Problem 4 — `docs/11-guides/vkdownloader-limitations.md` line 98: Stale setting name — **STILL LIVE**

**Severity:** LOW (documentation drift)
**File:** `docs/11-guides/vkdownloader-limitations.md`, line 98

The "Segment Merge Disk Space" section says `max_concurrent_downloads=1` but the
sequential-mode anti-detection delay is now triggered by `max_concurrent_segments=1`.

---

## Problem 5 — Plan §3.9 references wrong docs file for Windows caveat — **STILL LIVE (plan metadata)**

**Severity:** LOW
**File:** `.ai/plans/12-filesystem-artifacts-audit-fixes.md`, §3.9 (P12-B11)

The plan states P12-B11's semantic scope as `docs/11-guides/configuration.md` and
`docs/01-tools/vkdownloader-overview.md`, but the Windows `os.chmod` caveat for
the cookie artefact appears in `docs/11-guides/vkdownloader-limitations.md`
(lines 72, 78) and `docs/01-tools/vkdownloader-overview.md` (line 155).
`docs/11-guides/configuration.md` does **not** contain the Windows caveat.

---

## Problem 6 — Stash forward-port B9/B12 commits do not advance plan 12 — **NEW (auditor observation)**

**Severity:** MEDIUM (plan tracking)
**Scope:** `.ai/plans/12-filesystem-artifacts-audit-fixes_fix.md`

### Description

The stash forward-port execution plan (`.ai/plans/20-stash-forward-port-execution.md`)
describes its work as "B9" and "B12" — but these labels map to **plan 07** (network
resilience) stash blocks `NET-003` and `NET-012`, **not** plan 12's own blocks.

Plan 12's B9 is about the `.part` file probe and `DF-008` cleanup naming (ART-002),
while stash B9/NET-003 is about threading `m3u8_url` to the yt-dlp child and fixing
the `worst` quality inversion. These are entirely different defects in the same file
(`ytdlp_downloader.py`).

The stash forward-port commits (`a9fdd4a`, `2a8f60b`) have **not** advanced any of
plan 12's 12 blocks. The plan's completion status remains **1 of 12 implemented**
(B3 only). The B9/B12 labels in commit messages are ambiguous without the plan
namespace prefix (`P07-B9` vs `P12-B9`).

### Recommendation

- The stash forward-port plan should qualify its block references as `P07-B9` and
  `P07-B12` to disambiguate from plan 12's blocks of the same number.
- The plan 12 status table should add a note that stash B9/B12 commits touched
  `ytdlp_downloader.py` and `extractor.py` but did not address any P12 findings.

---

## Plan disposition

**Recommendation: RENAME TO `_fix`.**

The plan is not stale: all filesystem-artefact findings were re-verified at `HEAD = c64376d`
and remain live. The stash forward-port commits did not affect these findings — they
fixed network-resilience defects (stash B9/NET-003, stash B12/NET-012) in the same files,
but the filesystem-artefact defects plan 12 targets (probe naming, sweep safety,
working-directory lifetime, free-space sizing, control characters, traversal guards,
dedup) are all untouched.

The fixes described in plan 12 are architecturally sound — the plan explicitly
protects the ffmpeg merge engine as permanent surface (§2.4.4) and follows good
engineering practices (one commit per block, tests accompany new behaviour, no
breaking changes without declaration). Only 1 of 12 blocks has been implemented
(B3); the remaining 11 blocks require code changes. Execution will not
violate architecture or quality.

**No code changes were made by this audit pass.**
