# Audit Problems Report — Plan 12: Filesystem Artefacts Audit Fixes

**Audited plan:** `.ai/plans/12-filesystem-artifacts-audit-fixes.md`
**Audit date:** 2026-10-09
**Repository:** `vkdownloader` (`C:\py_exp\mko_vkideo`)
**Plan baseline (per plan):** `HEAD = 58bb7ce` (2026-10-03)
**Current HEAD:** `8825c69` (2026-10-09)
**Scope:** Verification of plan completion and problems found in code/docs during audit.

---

## Plan Completion Status: NOT COMPLETE — 1 OF 12 BLOCKS IMPLEMENTED

| Block | Finding(s) | Commit | Status |
|-------|-----------|--------|--------|
| P12-B1 (ART-002) | Component-wise traversal detection | — | **NOT implemented** |
| P12-B2 (ART-003, DF-004) | Warning reaches the user | — | **NOT implemented** |
| P12-B3 (ART-004) | Control characters in `sanitize_title` | `17b8831` | ✅ Implemented |
| P12-B4 | Length bound's true scope (option a) | `17b8831` (docstring only) | ⚠️ Partially |
| P12-B5 | Reserved device names / trailing dots | — | **NOT implemented** |
| P12-B6 (ART-003) | Sweeps match what the tree contains | — | **NOT implemented** |
| P12-B7 (ART-004) | Working-directory lifetime | — | **NOT implemented** |
| P12-B8 (ART-012) | Download-stage space, merge multiplier | — | **NOT implemented** |
| P12-B9 (DF-008) | Probe and cleanup name the right file | — | **NOT implemented** |
| P12-B10 (DEC-W R1) | Dedup by resolved output filename | — | **NOT implemented** |
| P12-B11 | Confinement posture for artefact paths | — | **NOT implemented** |
| P12-B12 (doc) | STRUCT.md description of ffmpeg_utils | — | **NOT implemented** |

### Implementation evidence

**P12-B3 (DONE):** Commit `17b8831` ("fix(security): strip control characters from filesystem-bound titles",
2026-10-05) added a `_CONTROL_CHARS` module constant
(`chr(0)`–`chr(31)` + `chr(127)`) and changed `sanitize_title` to iterate over
`'/\\:*?"<>|' + _CONTROL_CHARS` instead of the hardcoded 9-character set.
Tests added: `test_no_control_character_survives`, `test_newline_and_tab_do_not_produce_multiline`,
`test_null_byte_replaced_not_stripped`.

**P12-B4 (PARTIAL):** The same commit updated the `sanitize_title` docstring to
state "The length bound applies to this title component only, not to the full
output path." This resolves the documentation half of B4 (option-a: record the
scope). No separate decision or test exists for the full B4 acceptance criteria.

**Uncommitted changes are NOT from this plan:** The working tree currently shows
uncommitted modifications to `segment_downloader.py` (55 lines), `ffmpeg_utils.py`
(12 lines), `ytdlp_downloader.py` (2 lines), `downloader_throttle.py` (76 lines),
`config.py` (40 lines), and several test files. These are transport/concurrency
refactoring changes (the `max_concurrent_segments` setting rename, `build_client_timeout`
extraction, `_MERGE_STAGE_TIMEOUT` constant) introduced by another agent — they
do not touch any of the plan's 12 blocks (B1–B12).

### Findings still LIVE (verified at current HEAD)

Every finding the plan records was re-verified at `HEAD = 8825c69` and remains
unresolved:

- **ART-002:** `validate_output_path` still uses `".." in str(path)` substring test
  at two layers (lines 57 and 69 of `security.py`), not `path.parts` component-wise test.
- **ART-003 / DF-004:** `repo_root = Path(__file__).resolve().parent.parent.parent`
  (line 75 of `security.py`) still derives to `src/` (one level too deep). The
  warning at `_resolve_output_file` is still suppressed with `warning=False` (line 112).
- **ART-005:** `_cleanup_segments` still uses bare `f.unlink()` over `glob("*")`
  (line 449–450 of `segment_downloader.py`), no `missing_ok`, no `is_file()` guard.
- **ART-003 (tally):** `_tally_and_merge` still uses
  `len(list(segments_dir.glob("*.ts")))` (line 849) which counts `batch_*.ts` files.
- **ART-004:** `segments_dir.mkdir()` (line 1208) still runs before the playlist
  is fetched; the `finally` block (line 1242–1244) only logs, does not sweep.
  `_clear_stale_segments` (line 129–157) still uses `glob("*.ts")`, does not
  sweep `*.ts.tmp`.
- **ART-012:** `_required_merge_bytes` still returns `segment_bytes * 2 + _MERGE_SPACE_MARGIN_BYTES`
  (line 496 of `ffmpeg_utils.py`); the deferral comment (line 639) is unchanged.
- **DF-008:** The resume probe at `ytdlp_downloader.py` line 893–894 checks
  `validated_output.exists()` (the final name), not the `.part` file;
  `_build_ytdlp_cli_command` (line 706–787) still has no `--no-part` flag.
- **DEC-W R1:** No resolved-filename dedup exists. Only exact-URL dedup
  (`seen_urls` set in `batch_downloader.py` line 347) is present — that is
  URL-based, not filename-based as the plan's Decision A requires.

**No code changes were made by this audit pass.**

---

## Problem 1 — `docs/STRUCT.md` line 34: Misleading module description

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

### Plan's role

P12-B12. The plan records this as a one-line doc fix in §2.4.4. Not yet executed.

---

## Problem 2 — `docs/01-tools/vkdownloader-overview.md` line 16: Misleading ffmpeg description

**Severity:** LOW (documentation drift)
**File:** `docs/01-tools/vkdownloader-overview.md`, line 16

### Description

The overview states the product "combines yt-dlp for stream extraction with
ffmpeg for **direct HLS-to-MP4 conversion**." After TRN-001 (removal of
`DownloadMethod.FFMPEG`), ffmpeg is no longer a download transport — it is
exclusively the post-download segment merge engine. The phrase "direct HLS-to-
MP4 conversion" echoes the retired transport and conflicts with the CLI
reference (line 67: "The ffmpeg download method was removed; ffmpeg is still
required to merge downloaded segments").

### Evidence

- `docs/01-tools/vkdownloader-overview.md:16` → "...ffmpeg for direct HLS-to-MP4
  conversion..."
- `docs/99-reference/cli-reference.md:67` → "...The ffmpeg download method was
  removed; ffmpeg is still required to merge downloaded segments."
- `src/vkdownloader/models/enums.py` → `DownloadMethod.FFMPEG` was removed in
  `TRN-001` (`d572d96`)

### Plan's role

P12-B12 does not explicitly list this line, but the same §2.4.4 doc fix should
reconcile the overview's ffmpeg description with the post-TRN-001 reality.

---

## Problem 3 — Stale module line counts in `docs/01-tools/vkdownloader-overview.md`

**Severity:** LOW (documentation drift)
**File:** `docs/01-tools/vkdownloader-overview.md`, lines 283–287

### Description

The module architecture table lists stale line counts that no longer match the
current source tree. This reduces the guide's credibility as a structural
reference.

### Evidence

| Module | Doc claim | Actual (HEAD + uncommitted) |
|---|---|---|
| `downloader.py` | ~350 lines | 360 lines |
| `ytdlp_downloader.py` | ~722 lines | 1375 lines |
| `segment_downloader.py` | ~901 lines | 1275 lines |
| `ffmpeg_utils.py` | ~360 lines | 646 lines |

The plan (§2.4.4) only touches `docs/STRUCT.md`, not this overview table, but
the drift in the overview is in the same doc file the plan references for B12.

---

## Problem 4 — `docs/11-guides/vkdownloader-limitations.md` line 98: Stale setting name

**Severity:** LOW (documentation drift)
**File:** `docs/11-guides/vkdownloader-limitations.md`, line 98

### Description

The "Segment Merge Disk Space" section's introductory note says
"When `max_concurrent_downloads=1` (sequential mode), the downloader applies:..."
but the sequential-mode anti-detection delay is now triggered by
`max_concurrent_segments=1`, not `max_concurrent_downloads=1`. The `max_concurrent_segments`
setting was added by phase 06 (the `max_concurrent_segments` rename visible in
the uncommitted `segment_downloader.py` and `config.py` changes). The limitations
guide was not updated.

### Evidence

- `docs/11-guides/vkdownloader-limitations.md:98` → "When `max_concurrent_downloads=1`
  (sequential mode)..."
- `src/vkdownloader/services/segment_downloader.py:1037` → `if result and not
  policy.is_bounded_batch and policy.max_concurrent_segments == 1:`

### Plan's role

Not in scope for P12. The plan's P12-B11 semantic scope is `docs/11-guides/configuration.md`
and `docs/01-tools/vkdownloader-overview.md` — the limitations guide is a separate
file. This drift is attributed to the phase 06 agent that introduced the
`max_concurrent_segments` setting without updating this guide.

---

## Problem 5 — Plan §3.9 references wrong docs file for Windows caveat

**Severity:** LOW (plan/documentation metadata)
**File:** `.ai/plans/12-filesystem-artifacts-audit-fixes.md`, §3.9 (P12-B11)

### Description

The plan states the semantic scope of P12-B11 as `docs/11-guides/configuration.md`
and `docs/01-tools/vkdownloader-overview.md` — "the two documents that already
state the Windows caveat for other artefacts." In reality, the Windows `os.chmod`
caveat for the cookie artefact appears only in `docs/11-guides/vkdownloader-limitations.md`
(lines 72, 78) and `docs/01-tools/vkdownloader-overview.md` (line 155).
`docs/11-guides/configuration.md` does **not** contain the Windows caveat.

### Evidence

- `.ai/plans/12-filesystem-artifacts-audit-fixes.md:§3.9` → references
  `docs/11-guides/configuration.md` for the Windows caveat
- `docs/11-guides/configuration.md` → no `os.chmod`, `0o600`, or Windows-caveat
  text found
- `docs/11-guides/vkdownloader-limitations.md:72,78` → contains the full
  Windows `os.chmod` caveat

### Plan's role

This is a reference error in the plan itself, not a code issue. When P12-B11 is
executed, the correct target file is `docs/11-guides/vkdownloader-limitations.md`,
not `docs/11-guides/configuration.md`.

---

## Plan disposition

**Recommendation: RENAME TO `_fix`.**

The plan is not stale: all findings were re-verified at `HEAD = 8825c69` and
remain live. The fixes described are architecturally sound — the plan explicitly
protects the ffmpeg merge engine as permanent surface (§2.4.4) and follows good
engineering practices (one commit per block, tests accompany new behaviour, no
breaking changes without declaration). Only 1 of 12 blocks has been implemented
(in B3); the remaining 11 blocks require code changes. Execution will not
violate architecture or quality.

**No code changes were made by this audit pass.**
