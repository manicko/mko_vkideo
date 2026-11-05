# Block E Audit Findings — durable per-segment checkpoint and safe content identity

**Author:** auditor
**Validated by:** not run
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no
**Commit measured:** 469e1d8afdd1094a479c878978037faf0d980013
**Working-tree state:** dirty
**Dirty paths:** .ai/plans/01-MKO_VKIDEO_Refactoring_Execution.md, .ai/tasks/task_E_checkpoint.yaml

## Verification performed

- `pytest tests/test_checkpoint.py tests/test_segment_downloader.py tests/test_hls_downloader.py` -> 354 passed, 1 skipped.
- `pytest tests/test_checkpoint.py` -> 18 passed.
- `ruff check src tests` -> All checks passed.
- `ruff format --check src tests` -> 64 files already formatted.
- `git diff --check` -> no whitespace errors.
- `mypy src/vkdownloader/services/checkpoint.py src/vkdownloader/services/hls_parser.py src/vkdownloader/services/segment_downloader.py` -> 17 errors in Block E modules (explicit `Any`, untyped defs, `object` attribute access).
- `pytest tests/test_packaging.py` -> 3 failed (sdist/wheel manifest not updated for new Block E modules).
- `pytest tests/test_cli.py` -> many failures, reproduced identically on base commit 35e9fe6; not attributed to Block E.

## Findings

### BE-001: Checkpoint reconciliation quarantines a whole generation on a single corrupt segment

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection of `_reconcile_checkpoint`.
> - **See also:** BE-003

| Field | Value |
|-------|-------|
| **ID** | BE-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** `_reconcile_checkpoint` computes `all_verified` over every segment record and, when any record fails `verify_segment_record`, falls through to `quarantine_generation`. That discards all already-verified segments and forces a full redownload, contradicting the Block E acceptance criterion that a corrupt segment is redownloaded individually. The correct behaviour is to quarantine only on identity mismatch or an unreadable checkpoint; on identity match, retain the checkpoint and let `_iter_pending_segment_tasks` skip verified segments and redownload only the corrupt/missing ones.

**Evidence:** `src/vkdownloader/services/segment_downloader.py` lines 226-246:
```python
if ok:
    all_verified = all(
        _cp.verify_segment_record(rec, segments_dir) for rec in existing.segments.values()
    )
    if all_verified:
        return existing
# mismatch or corrupt -> quarantine
try:
    _cp.quarantine_generation(segments_dir, existing.generation_id)
except Exception:
    pass
```

**Recommendation:** Split the two cases: quarantine only when `verify_checkpoint` returns False or the checkpoint cannot be read. When identity matches, return `existing` regardless of per-segment verification results, so corrupt segments are handled by `_iter_pending_segment_tasks`.

### BE-002: `quarantine_generation` does not sanitize `generation_id` used in a filesystem path

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection.

| Field | Value |
|-------|-------|
| **ID** | BE-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/checkpoint.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** `quarantine_generation` builds `gen = str(generation_id or "gen")` and uses it directly in `quarantine_root / gen`. A checkpoint containing a traversal-style `generation_id` (for example `../../outside`) can escape the intended `generations/` root because no confinement or basename validation is applied. Checkpoint data is local, but a tampered or malformed checkpoint should not be able to relocate the working directory.

**Evidence:** `src/vkdownloader/services/checkpoint.py` lines 309-315:
```python
gen = str(generation_id or "gen")
target = quarantine_root / gen
if target.exists():
    index = 1
    while (quarantine_root / f"{gen}-{index}").exists():
        ...
```

**Recommendation:** Validate that `generation_id` is a single safe path component (reject separators, `.`, `..`, empty, and NUL) before using it, falling back to a sanitized constant such as `"gen"` when invalid.

### BE-003: Reconciliation swallows quarantine and checkpoint-write failures

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection.

| Field | Value |
|-------|-------|
| **ID** | BE-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** Both `quarantine_generation` and `write_checkpoint_atomic` are called inside bare `except Exception: pass` blocks. If quarantine fails, the old segments and checkpoint remain in place while a new checkpoint is written on top of them, mixing generations. If the initial checkpoint write fails, the function still returns a checkpoint that was never persisted, so resume will reload stale state.

**Evidence:** `src/vkdownloader/services/segment_downloader.py` lines 242-246 and 265-268.

**Recommendation:** Do not silently ignore these failures. If quarantine fails, abort the download (or explicitly mark the generation as untrusted) instead of continuing with mixed artifacts. If the initial write fails, propagate or return `None` rather than an unpersisted checkpoint.

### BE-004: Checkpoint fields typed as `object` defeat type safety and mypy

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `mypy` reports `attr-defined` on `policy.checkpoint.segments` and `checkpoint.generation_id`. |

| Field | Value |
|-------|-------|
| **ID** | BE-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** `DownloadPolicy.checkpoint` and `_reconcile_checkpoint`'s `checkpoint` parameter/return are typed as `object | None` / `object`, although they always hold a `JobCheckpoint`. This forces `getattr` access and produces mypy errors (`"object" has no attribute "segments"` / `"generation_id"`), weakening the type-safety requirement of the project rules.

**Evidence:** `src/vkdownloader/services/segment_downloader.py` lines 118, 209, 210.

**Recommendation:** Type these as `JobCheckpoint | None` / `JobCheckpoint` (import under `TYPE_CHECKING` if needed) and replace `getattr(policy, "checkpoint", None)` with direct attribute access.

### BE-005: `stream_variant_id` defaults to `"unknown:unknown"` because media-playlist identity is incomplete

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection. |

| Field | Value |
|-------|-------|
| **ID** | BE-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py, src/vkdownloader/services/hls_parser.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** `parse_media_playlist` never populates `codecs` or `resolution` (a media playlist does not carry them), and `_run_download_session` therefore sets `stream_variant_id` to `"unknown:unknown"` whenever the caller does not supply one. That collapses distinct variants into one identity and can allow segment reuse across different qualities/variants. Block F is expected to populate this field, but the fallback should not be a constant that defeats identity.

**Evidence:** `src/vkdownloader/services/segment_downloader.py` lines 1440-1446 and 1456-1460.

**Recommendation:** Derive a non-trivial fallback variant id from the available data (for example the m3u8 URL host/path, quality, or a hash of the variant URL) and document that Block F must override it with the master-playlist variant id.

### BE-006: Playlist fingerprint omits target duration and version

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection. |

| Field | Value |
|-------|-------|
| **ID** | BE-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/hls_parser.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** `compute_playlist_fingerprint` includes media/discontinuity sequences, init-map identity, endlist/live flags, and segment structure, but not `target_duration` or `version`. Two playlists that differ only in those fields would receive the same fingerprint and could reuse segments incorrectly.

**Evidence:** `src/vkdownloader/services/hls_parser.py` lines 405-445 (`structural` dict).

**Recommendation:** Add `target_duration` and `version` to the fingerprint's structural payload.

### BE-007: Packaging manifest not updated for Block E modules

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `tests/test_packaging.py` fails with unexpected entries. |

| Field | Value |
|-------|-------|
| **ID** | BE-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_packaging.py, src/vkdownloader/services/checkpoint.py, src/vkdownloader/services/hls_parser.py |
| **Classification** | advisory |
| **Verification** | observed |

**Description:** The sdist/wheel manifest expectations in `tests/test_packaging.py` were not updated when Block E added `checkpoint.py`, `hls_parser.py`, and `test_checkpoint.py`. The packaging tests now fail with unexpected entries (sdist +3, wheel +2).

**Evidence:** `tests/test_packaging.py` failures: `unexpected (3): ['src/vkdownloader/services/checkpoint.py', 'src/vkdownloader/services/hls_parser.py', 'tests/test_checkpoint.py']` and `unexpected (2): ['vkdownloader/services/checkpoint.py', 'vkdownloader/services/hls_parser.py']`.

**Recommendation:** Update `EXPECTED_SDIST_ENTRIES` and `EXPECTED_WHEEL_ENTRIES` to include the new Block E modules and test file, or regenerate the manifest through the project's documented process.

### BE-008: `quarantine_generation` can create unexpected empty directories when input is absent

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection. |

| Field | Value |
|-------|-------|
| **ID** | BE-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/checkpoint.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** When `segments_dir` does not exist, `quarantine_generation` creates an empty `target` directory under `generations/` and recreates `segments_dir`. This side effect is surprising for a "quarantine" operation and can leave empty generation directories behind.

**Evidence:** `src/vkdownloader/services/checkpoint.py` lines 323-326.

**Recommendation:** Only create the quarantine target when there is something to move; otherwise return the intended target path without creating empty directories.

### BE-009: Signed query tokens remain in `HLSMediaSegment.uri`

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection. |

| Field | Value |
|-------|-------|
| **ID** | BE-009 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/hls_parser.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** `HLSMediaSegment.uri` retains the full segment URL including signed query parameters. The checkpoint itself correctly stores no URLs, but any logging, serialization, or diagnostic dump of the parsed playlist would expose live tokens. The fingerprint code already strips queries for init-map identity, but the segment URIs are not redacted.

**Evidence:** `src/vkdownloader/services/hls_parser.py` `HLSMediaSegment.uri` and `parse_media_playlist` (segment URI assignment).

**Recommendation:** Keep the full URI for downloading, but ensure no code path logs or serializes parsed playlist models verbatim; alternatively store a redacted display form alongside the executable URI. Verify with a secret canary test.

### BE-010: Legacy no-checkpoint path still trusts any non-empty `.ts` file

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection. |

| Field | Value |
|-------|-------|
| **ID** | BE-010 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** When no checkpoint is present, `_iter_pending_segment_tasks` falls back to `segment_path.exists() and segment_path.stat().st_size > 0` and skips the file. A partial or corrupt segment left by an older version will be treated as complete and merged.

**Evidence:** `src/vkdownloader/services/segment_downloader.py` lines 1336-1355 (fallback branch).

**Recommendation:** This is inherent to legacy data; document that directories without a checkpoint are untrusted and should be cleared before resume, or compute a hash on first load to seed a checkpoint.

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 6 |
| LOW | 2 |

## Mandatory Fixes

- BE-001: Separate identity mismatch from segment corruption in `_reconcile_checkpoint`.
- BE-002: Sanitize `generation_id` in `quarantine_generation`.
- BE-003: Do not swallow quarantine/checkpoint-write failures.

## Advisory Recommendations

- BE-004: Type checkpoint fields as `JobCheckpoint`.
- BE-005: Improve fallback `stream_variant_id`.
- BE-006: Include target duration/version in fingerprint.
- BE-007: Update packaging manifest expectations.
- BE-008: Avoid empty quarantine directories.
- BE-009: Prevent token leakage from parsed playlist URIs.
- BE-010: Document or seed checkpoints for legacy directories.

## Doc Updates Needed

- BE-007: Update packaging manifest oracle counts after adding Block E modules.
