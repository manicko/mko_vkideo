# Phase 07 — Filesystem Artefacts and Name Derivation

**Auditor:** architecture auditor (phase 07)
**Date:** 2026-09-29
**Commit measured:** `a335b2a2e0270414f9f2923d1b4a8e038a8998b5` (`refactor(cli): extract one shared command bootstrap`)
**Platform:** `win32` / `os.name == "nt"` / CPython 3.12.1 / `Windows-10-10.0.17763-SP0`
**Tree state note:** this phase began at `ea44b3d` and `a335b2a` landed mid-run at 21:40. `git diff --stat ea44b3d a335b2a -- src tests` is `cli.py | 52 +-` and `tests/test_cli.py | 73 +` only. Every `src/` anchor outside `cli.py` is unchanged by that commit and was re-measured at `a335b2a`; the one `cli.py` anchor this phase cites (the list reader) moved from `:290` to **`:306-314`** and the current value is used throughout. Two earlier anchors from the phase brief were re-checked and still hold: NET-001's `ffmpeg_utils.py:314-317` and `:511-515`. CFG-002's anchor `services/downloader.py:652-653` **no longer points at anything** — `model_copy` has zero occurrences in `src/`; CFG-002 is fixed by `ea44b3d` and is not re-filed here.
**No code was changed.** `git status --short src tests` is empty. All scratch lives under the gitignored `.temp/` and is enumerated under Documented Skips §3.

---

## Summary

Fourteen findings. Nothing was filed on the basis of a placeholder, a naming preference, a coverage count, or a reference to another phase's list.

| ID | Severity | Type | Classification | One line |
|---|---|---|---|---|
| ART-001 | CRITICAL | RUNTIME-ERROR | mandatory | Control characters survive the sanitiser; the resulting name makes the product raise an untyped `OSError`/`ValueError`. |
| ART-002 | HIGH | RUNTIME-ERROR | mandatory | The partial probe and the retry-exhaustion cleanup both target the final name; the child writes `<name>.part`. |
| ART-003 | MEDIUM | RUNTIME-ERROR | mandatory | `_cleanup_segments` unlinks every entry with a bare `unlink()`; one non-regular entry turns a completed download into an exception. |
| ART-004 | HIGH | RUNTIME-ERROR | mandatory | A leftover `batch_NNNNN.ts` is counted as a segment and the staleness check never reconciles it. |
| ART-005 | MEDIUM | RUNTIME-ERROR | mandatory | The working tree is created before the playlist is fetched; the empty tree is removed only from the success path. |
| ART-006 | HIGH | RUNTIME-ERROR | mandatory | Two list entries deriving one name share one final artefact, one working tree and one partial; nothing deduplicates. |
| ART-007 | HIGH | BEST-PRACTICE | mandatory | Mode guarantee: requested `0o600`, measured `0o666`, access state not confining, zero independent controls, zero oracles that can fail here. |
| ART-008 | HIGH | RUNTIME-ERROR | mandatory | The ffmpeg argfile survives a forced termination carrying the signed CDN URL; nothing in the tree can find it. |
| ART-009 | MEDIUM | RUNTIME-ERROR | mandatory | No containment root; the single comparison is warn-only and is suppressed at the call site that creates the output directory. |
| ART-010 | MEDIUM | RUNTIME-ERROR | mandatory | A legitimate directory named with a double dot is refused under a "Path traversal detected" label. |
| ART-011 | MEDIUM | SPEC-DEVIATION | mandatory | The truncation bounds a component of the path, not the path. |
| ART-012 | MEDIUM | RUNTIME-ERROR | mandatory | Peak working set measured at 3.15× the final artefact; the only ceiling covers the merge stage, not the download that precedes it. |
| ART-013 | HIGH | RUNTIME-ERROR | mandatory | An interruption between the write and the move leaves `NNNNN.ts.tmp`, matched by no sweep, no count and no index enumeration. |
| ART-014 | LOW | BEST-PRACTICE | advisory | The shared sanitiser handles no device name and no trailing dot; the derivation's fixed suffix is the only barrier. |

**Admissible rows used, and what was ruled out.** Nine of the fourteen findings are the block-(c) rows verbatim (a legitimate path refused, no containment root, an unhandled name failure, a residue class no sweep can reconcile, cleanup reachable only from the success path, a cleanup that targets a name the child never creates, a removal that raises, a path reached by two writers, a name the current derivation cannot produce). Five are the block-(f) rows (the requested/mode-in-force pair plus a confining control, the enclosing directory, the platform mapping and the oracle verdict) and the block-(b)/(d) rows (shared working tree, the position that reaches only one fallback branch, silent destruction, truncation scope, a measured working-set peak, a cap that does not exist). None was filled in from an anchor, from a test's assertion, or from another phase's list. Ruled out: mode oracles, and reserved-device-name *removal* semantics (both are harness assumptions, refuted below and carried as caveats).

**Cross-phase boundaries held.** The child's partial file *name* is phase 05's; its residue is this phase's. What the process *emits* — including the `count > 0` guards that let a residue pass in silence — is phase 08's. Docstrings and comments are phase 09's: the `sanitize_title` docstring's completeness claim and the `FileNotFoundError` rationale at `ffmpeg_utils.py:474-478` are cross-referenced, not filed. Cookie-file material is phase 06's and is measured here for inventory completeness only. Phase 01 owns entry ordering and logging configuration; phase 02 owns env parsing.

**Independent verification of the phase-05 claim TRN-001.** It is **confirmed** on this host. Driven through the product's own `_temp_argfile`/`_format_argfile` and the installed muxer `C:\ffmpeg\ffmpeg.exe`, the command vector `["ffmpeg", "@<argfile>"]` returns **4294967274** (`-22`, `EINVAL`) with `[AVFormatContext @ …] Unable to choose an output format for '@C:\Users\NMATVE~1\AppData\Local\Temp\vk_ffmpeg_tk6kkdjk.args'`. The `@` token is taken as a literal output filename; the argfile is never read. Consequences inside this phase: (a) the argfile's `chmod 0o600` protects a file the muxer never opens (ART-007); (b) the argfile's whole life cycle is a write-then-unlink of a file nothing consumes, which is why the residue class in ART-008 is so cheap to create; (c) `--method ffmpeg` always falls through to the segment downloader, which makes the segment-path findings reachable at that opt-in and unreachable at the default (see Reachability below). Evidence: `.temp/evidence/trn001.txt`.

**Reachability ledger for this phase.** Stated on every finding, as the phase requires:

| Subject | Reached at | Gate |
|---|---|---|
| `_resolve_output_file` name derivation | **default** | every download, single and batch |
| `validate_output_path` (3 call sites) | **default** | every download |
| yt-dlp path: `_download_with_ytdlp`, partial probe, DF-008 cleanup, `<name>.part` residue | **default** | `--method auto` is the default (`cli.py:105`) |
| log file | **opt-in** | `log_file: Path \| None = None`; written only when `VKDOWNLOADER_LOG_FILE`/`--log-file` is set |
| ffmpeg argfile | **opt-in** | `--method ffmpeg`; written before the ffmpeg branch is taken |
| segment path: working tree, segments, batch merge, concat lists, `.signature`, `NNNNN.ts.tmp` | **opt-in** | `--method ffmpeg`, or `_attempt_segment_resume` — whose own precondition (`ytdlp_downloader.py:416`, the final name must exist) is never satisfied on the yt-dlp path. Given TRN-001, `--method ffmpeg` always fails and therefore always reaches the segment downloader. |

The last row is load-bearing: **five of the fourteen findings live behind an explicit opt-in.** They are filed at the severity the taxonomy row assigns, with the gate stated, and not promoted on the strength of the gate.

---

## Findings

### ART-001 — A control character in a title survives sanitisation and the resulting name makes the product raise an untyped error

- **ID:** ART-001
- **Severity:** CRITICAL
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness; an unhandled failure)
- **Category:** runtime error, not caught

**Affected location**
- `src/vkdownloader/utils/security.py:15-23` — `sanitize_title`. `_INVALID_FILENAME_CHARS` is `/\\:*?"<>|`; the docstring at `:18` states the purpose as "characters that are invalid on Windows/Unix filesystems". Nothing in the function touches `0x00-0x1F` or `0x7F`.
- `src/vkdownloader/utils/security.py:105-109` — the derived name `f"{safe_title}_{video.id}.mp4"` / `f"{index}_{video.id}.mp4"`; `safe_title` carries the control character straight through.
- `src/vkdownloader/services/segment_downloader.py:897-898` — `segments_dir = output_file.parent / f".{output_file.stem}_segments"` then `segments_dir.mkdir(parents=True, exist_ok=True)`. `Path.stem` preserves the control character, so the product's own `mkdir` is the call that fails.
- `src/vkdownloader/services/ytdlp_downloader.py:547` — `except (ExtractionError, OSError):` around the whole `_attempt_segment_resume` body, which contains the segment call.
- `src/vkdownloader/services/downloader.py:554` — the `--method ffmpeg` fallback call, uncaught.

**Observation.** Driven through the product's own `sanitize_title` and `_resolve_output_file`, then the platform's own create:

| input title | sanitised | derived last component | create result |
|---|---|---|---|
| `before\x00after` | unchanged | `before\x00after_456239018.mp4` | `ValueError: embedded null character` |
| `a\x01\x02\x1f\x7fb` | unchanged | `a\x01\x02\x1f\x7fb_456239018.mp4` | `OSError: [Errno 22] Invalid argument` |
| `line1\nline2` | unchanged | `line1\nline2_456239018.mp4` | `OSError: [Errno 22] Invalid argument` |
| `line1\rline2` | unchanged | `line1\rline2_456239018.mp4` | `OSError: [Errno 22] Invalid argument` |
| `a\tb` | unchanged | `a\tb_456239018.mp4` | `OSError: [Errno 22] Invalid argument` |
| `a\x7fb\u00e9\u4e2d` (DEL + non-ASCII) | unchanged | — | created, read back, `0o666` |

`sanitize_title` replaces exactly the nine characters on its list — measured, all nine, `pre<char>post` → `pre_post` for each of `/ \ : * ? " < > |` — and nothing else. `0x7F` and every code point above it are already legal in a Windows filename, so the boundary the function misses is exactly `0x00-0x1F` and `0x7F`-inclusive-of-NUL.

**Why this is CRITICAL.** The taxonomy row is "a name derived from a string the origin supplied causes an unhandled failure, so one bad title ends the run with a generic error." The runtime consequence is observed; the trigger is not, and is marked as such below. One title is enough: in the segment path the `OSError` from `segments_dir.mkdir` is either swallowed by `ytdlp_downloader.py:547` and relabelled `failed_to_refresh_token` (`:548-552`) — a message that names a token refresh, not a filename — or, on the `--method ffmpeg` fallback at `downloader.py:554`, propagates to `cli.py`'s `except Exception` as "An error occurred during download", exit 1, with no output file and no indication of which name was rejected. The product's typed error hierarchy (`DownloadError` and its subclasses) is not involved anywhere on this path.

**UNVERIFIED marker — trigger.** The origin of the string is real and is recorded: `services/extractor.py:220` — `title = info.get("title") or info.get("fulltitle")` — the origin's own metadata, passed through `extractor.py:141` into `VideoWithStreams.title`, which is the only input to the derivation. **What the real origin supplies is not asserted by this run.** No real network request was made and no real VK response was seen. The structural fact and the runtime consequence are both established; whether a control character ever reaches `sanitize_title` from the origin is unverified.

**Reachability gate.** `_resolve_output_file` is reached at the declared default by every download. The *unhandled Python error* is reached only on the segment path, i.e. behind the explicit `--method ffmpeg` opt-in (or behind `_attempt_segment_resume`, whose own precondition the product's probe at `ytdlp_downloader.py:416` never satisfies). On the default `auto` path the name is handed to yt-dlp on the command line and the child fails in its own terms instead.

**Recommendation.** Strip `0x00-0x1F` and `0x7F` in `sanitize_title` alongside the nine replacement characters, or replace them with `_` for consistency with the rest of the function. This is one line in a shared utility and it removes the whole class. The function has two callers — `security.py:105` (derivation) and `downloader.py:666` (display) — so the change is visible in both, which is the correct outcome. Effort: trivial. Priority: recommended, on the strength of the unhandled failure rather than of any observed real-world trigger.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-002 — The partial probe and the retry-exhaustion cleanup both target the final name; the child writes `<name>.part`

- **ID:** ART-002
- **Severity:** HIGH
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness; a cleanup that cannot reach a survivor)
- **Category:** runtime error, not caught

**Affected location**
- `src/vkdownloader/services/ytdlp_downloader.py:415-417` — `validated_output = validate_output_path(output_file, warning=False)`; `if not validated_output.exists() or validated_output.stat().st_size == 0: return None`. The probe looks at the **final** name.
- `src/vkdownloader/services/ytdlp_downloader.py:442-446` — "DF-008: Clean up partial output file left by yt-dlp on failure"; `validated_output.unlink(missing_ok=True)`. The cleanup looks at the **final** name.
- `src/vkdownloader/services/ytdlp_downloader.py:260-288` — the child command; `-o str(output_file)` at `:280`.
- `src/vkdownloader/services/ytdlp_downloader.py:531` — `_attempt_segment_resume` unlinks `output_file` (final name) before retrying.

**Observation.** Driven end to end through the product's own `download_with_ytdlp_with_resume_fallback` against a loopback origin on `127.0.0.1`, with the child's own naming:

| end condition | mechanism | survivor after the run | what the cleanup targeted |
|---|---|---|---|
| E1 completes | process returned | `Synthetic Title_456239018.mp4` (5 605 125 B, `0o666`) | n/a |
| E2 child returns non-zero | process returned | `<empty>` | `Synthetic Title_456239018.mp4` — which never existed |
| E3 retries declared as 2 | process returned | `<empty>` | same |
| E4 forced termination | `taskkill /PID <pid> /T /F` → `rc=0 SUCCESS: The process with PID … has been terminated.` | **`Synthetic Title_456239018.mp4.part` (31 744 B, `0o666`)** | never reached |

The two paths are different strings. `.part` is what the child writes while the transfer is in flight; the final name is what the child renames to on success. The product's probe and its cleanup both name the second.

Two consequences follow, both observed.

**1. The declared retry loop runs at most once.** With `max_retries=2` (E3) the child log contains exactly one `starting_ytdlp_download` and then `download_failed`; there is no second attempt and no `max_retries_exceeded` record, because `ytdlp_downloader.py:416` sees a non-existent final name and returns `None` on the first pass. The `while retry_count <= settings.max_retries` loop and the `logger.error("max_retries_exceeded", …)` at `:437-441` are unreachable for a failed direct-media transfer.

**2. The partial grows without bound and is reclaimed only by the child's own rename.** Driven through three consecutive runs in one directory:

| run | end condition | inventory after |
|---|---|---|
| 1 | killed mid-transfer | `Synthetic Title_456239018.mp4.part` — 7 168 B |
| 2 | fails cleanly | `Synthetic Title_456239018.mp4.part` — **1 246 380 B** |
| 3 | succeeds | `Synthetic Title_456239018.mp4` — the `.part` is gone |

Run 2 appended to run 1's survivor and the product removed nothing; run 3 consumed it because yt-dlp's own rename ran, not because the product did. So the answer to the matrix's fourth cell is: the residue class is not reclaimed by the product on any end, only incidentally by the child on a success.

**Reachability gate.** **Default.** `--method auto` is the default (`cli.py:105`), and `download_with_ytdlp_with_resume_fallback` is its first branch (`downloader.py:552`).

**Cross-reference.** The `.part` file's *name* as an yt-dlp interface is phase 05's; its residue, retention and growth here are this phase's. The child's own intermediate set on a fragment-resume path, which this run does not reach, is recorded as documented skip §2.4. The fact that no log line is emitted about the surviving partial is phase 08's.

**Recommendation.** Point both the probe at `ytdlp_downloader.py:415-417` and the cleanup at `:442-446` at the name the child actually writes, or at the set the child can write. The cheapest correct form is to resolve the partial name once and test/unlink that, which restores the retry loop as documented and removes a growing orphan. Note the interaction with phase 05's TRN-001: the two changes are independent, and neither requires the other. Effort: small. Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-003 — `_cleanup_segments` unlinks every entry with a bare `unlink()`; one non-regular entry turns a completed download into an exception

- **ID:** ART-003
- **Severity:** MEDIUM
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness)
- **Category:** runtime error, not caught

**Affected location**
- `src/vkdownloader/services/segment_downloader.py:418-419` — `for f in segments_dir.glob("*"): f.unlink()`. No `missing_ok`, no `is_file()` guard, no `try` around the loop.
- `src/vkdownloader/services/segment_downloader.py:617-618` — `_cleanup_segments(segments_dir)` runs **only** `if result:` — i.e. only after a successful merge.

**Observation.** The product's own `_cleanup_segments` driven against a working tree holding four regular entries and one subdirectory:

```
working tree before: ['.signature', '00000.ts', '00001.ts', '00002.ts', 'a_subdirectory']
_cleanup_segments RAISED builtins.PermissionError winerror=5:
    [WinError 5] Access is denied: '…\.Synthetic Title_456239018_segments\a_subdirectory'
working tree after : ['a_subdirectory']
```

The loop is not atomic and not resumable: it deleted four of five entries, then raised, leaving the tree in a state that is neither the state it started in nor empty. Because the call sits on the success branch at `:617-618`, the merged artefact is already on disk when the exception is raised; `_tally_and_merge` → `_process_downloaded_segments` → `_run_download_session` → `download_hls_with_resume` all propagate it, `download_hls_with_resume`'s `finally` runs the preservation reporter, and the caller sees a failure for a download that actually completed.

The same shape appears in five other removals, all bare `.unlink()`:

| site | what it removes |
|---|---|
| `ffmpeg_utils.py:316` | one merged batch's input segments |
| `ffmpeg_utils.py:317` | the batch concat list |
| `ffmpeg_utils.py:358` | the final concat list |
| `ffmpeg_utils.py:360` | every batch temp |
| `ytdlp_downloader.py:531` | the partial before the segment resume |

and the five that *do* guard are `ffmpeg_utils.py:515`, `segment_downloader.py:134`, `segment_downloader.py:178`, `ytdlp_downloader.py:444`, `downloader.py:124` (all `missing_ok=True`).

**Why MEDIUM and not higher.** The runtime failure is observed and the consequence is real, but the trigger is bounded and the bound is stated: the product never creates a non-regular entry in its own working tree. The routes that do put one there are a user, another process, or a second run sharing the tree — the last of which is reachable in principle via ART-006 but was not observed. The finding is filed as a correctness defect in a removal loop that has no guard where its five sibling removals do, not as an observed production failure.

**Reachability gate.** **Opt-in** — the segment path (`--method ffmpeg`).

**Recommendation.** Give `_cleanup_segments` the same `missing_ok=True` treatment the other five removals already have, and skip directories explicitly (`if f.is_file()`), so a stray entry costs nothing and cannot convert a completed download into an error. The `rmdir` at `:420-423` already tolerates failure, which shows the intent; the unlink loop just does not share it. Effort: trivial. Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-004 — A leftover merge batch is counted as a segment and the staleness check never reconciles it

- **ID:** ART-004
- **Severity:** HIGH
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness; a residue class the tree cannot reconcile)
- **Category:** runtime error, not caught

**Affected location**
- `src/vkdownloader/services/ffmpeg_utils.py:288` and `:291` — `batch_list_path = segments_dir / f"batch_list_{batch_num}.txt"`, written with a plain `open(..., "w")`.
- `src/vkdownloader/services/ffmpeg_utils.py:314-317` — the batch's input segments and its concat list are unlinked right after that batch merges.
- `src/vkdownloader/services/ffmpeg_utils.py:335` and `:338` — `final_list.txt`, written the same way.
- `src/vkdownloader/services/ffmpeg_utils.py:356-361` vs `:363-364` — the temp files and the final list are unlinked on the success branch only; the failure branch returns `False` and leaves `final_list.txt` on disk.
- `src/vkdownloader/services/segment_downloader.py:599` — `downloaded_count = len(list(segments_dir.glob("*.ts")))`.
- `src/vkdownloader/services/segment_downloader.py:125-128` — `_clear_stale_segments` returns early when `.signature` matches, before its `*.ts` removal at `:130-134` (count at `:130`, unlink loop at `:133`).
- `src/vkdownloader/services/ffmpeg_utils.py:495-497` — the existence check that decides the merge.

**Observation.** A surviving working directory of the shape a kill during the merge stage produces — 120 real segments, one `batch_00000.ts`, one `batch_list_0.txt`, and a `.signature` that matches the current playlist — driven through the product's own staleness check and then the product's own merge:

```
surviving directory: 123 entries
segments_dir.glob('*.ts') sees 121 .ts files      <- 250 real segments are expected
staleness check: before=123 after=123
batch_00000.ts still present after the check : True
batch_list_0.txt still present after the check: True
subsequent merge RAISED builtins.FileNotFoundError:
    Missing segment files for merge: ['00120.ts', '00121.ts', … ]
```

The chain is now fully observed, link by link. (1) `batch_00000.ts` is written by the product's own merge and is not removed when the process ends between the batch merge and the `finally`. (2) `segments_dir.glob("*.ts")` at `:599` counts it as a segment, because `batch_00000.ts` matches `*.ts` exactly as `00120.ts` does. (3) The staleness check short-circuits at `:125-128` on the matching `.signature` and never reaches its own `*.ts` removal, so the file it should have reconciled is exactly the file it does not. (4) The subsequent merge's existence check at `:495-497` raises, naming the *missing* files — an accurate diagnosis that never mentions the extra one, which stays on disk.

**Documented skip §2.2 is therefore not a skip.** The phase anticipated that link (3) of this chain might remain unobserved. It is observed: a subsequent merge was driven and its outcome recorded. The chain is closed, and the finding is filed rather than skipped.

**What is *not* claimed.** The order in which `_merge_batch_segments` destroys its inputs (`:314-317`) and the `finally` at `:511-515` destroying the batch temps is **NET-001, phase 03's, and is cross-referenced here, not re-filed.** What is this phase's is the *residue*: the two names the merge writes, the fact that one of them is indistinguishable from a segment to the product's own count, and the fact that the sweep designed to reconcile the directory is gated off exactly when the residue is present.

**Reachability gate.** **Opt-in** — the segment path (`--method ffmpeg`).

**Recommendation.** Give the merge intermediates a name the segment glob cannot match — the batch temps are already distinguishable by their `batch_` prefix, and the cheapest fix is to enumerate the merge's own files by the index form the merge uses rather than by a pattern, or to exclude `batch_*.ts` from the `:599` count. The second is a one-line change and it removes the false membership; the first also removes the false membership in the staleness sweep. Either way the residue becomes visible to a sweep that already exists. Effort: small. Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-005 — The working tree is created before the playlist is fetched, and the empty tree is removed only from the success path

- **ID:** ART-005
- **Severity:** MEDIUM
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness)
- **Category:** runtime error, not caught

**Affected location**
- `src/vkdownloader/services/segment_downloader.py:897-898` — `segments_dir.mkdir(parents=True, exist_ok=True)`, at the top of `_run_download_session`.
- `src/vkdownloader/services/segment_downloader.py:798` — the playlist fetch, which happens **after** the directory exists.
- `src/vkdownloader/services/segment_downloader.py:930-939` — `_log_preserve_segments`; the count is taken at `:937` and guarded by `if segment_count > 0` at `:938`.
- `src/vkdownloader/services/segment_downloader.py:617-618` — the only call that removes a directory, on the merge-success branch.

**Observation.** The product's own `download_hls_with_resume` driven against a loopback origin whose playlist endpoint returns 404:

```
SEGMENT-PATH END CONDITION S2 playlist unreachable
  product returned : None
  INVENTORY AFTER THE RUN:
    directory entries: [('.Synthetic Title_456239018_segments/', '0o777')]
    work dir present: True
```

A hidden, empty directory, `0o777`, left in the user's download directory. Followed through every sweep the tree owns:

```
  _log_preserve_segments against it   -> nothing (guarded on segment_count > 0)
  after the staleness check            -> entries=['.signature']   directory still present: True
  after a second visit                 -> entries=['.signature']   directory still present: True
```

The staleness check *adds* to the residue — it writes the `.signature` into the empty tree — and no code path in the tree removes the directory except `_cleanup_segments`, which is reachable only from `:617-618`, i.e. only after a merge that cannot happen when the playlist was never fetched. One such directory per video whose playlist fetch failed, in the directory the user chose.

The taxonomy row is exact: "A residue class is left only because its cleanup is reachable solely from the success path."

**Reachability gate.** **Opt-in** — the segment path (`--method ffmpeg`). A playlist fetch that never succeeds is an ordinary transient failure, not an edge case.

**Cross-reference.** That no log line accompanies the residue — the `count > 0` guard in the reporter — is phase 08's, and is named here only to mark the boundary. NET-001's note that the inventory at merge exit is not empty because `final_list.txt` survives is consistent with this and is not re-filed.

**Recommendation.** Create the working tree after the playlist is parsed and the segment list is known, and remove the directory on every exit that did not reach a merge. Both are small; the first is the better one because it removes the class rather than the instance. Effort: small. Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-006 — Two list entries deriving one name share one final artefact, one working tree and one partial; nothing deduplicates

- **ID:** ART-006
- **Severity:** HIGH
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness; silent destruction)
- **Category:** runtime error, not caught

**Affected location**
- `src/vkdownloader/utils/security.py:99-111` — `_resolve_output_file`. The name is a pure function of `(safe_title, video.id)` with no existence test, no suffix, no disambiguation. `output_index` reaches the name only in the `else` branch at `:109`.
- `src/vkdownloader/cli.py:306-314` — the list reader; every valid line is appended at `:314` with no deduplication.
- `src/vkdownloader/services/segment_downloader.py:897` — `segments_dir = output_file.parent / f".{output_file.stem}_segments"`, derived from the same final name.
- Overwrite behaviour: `services/downloader.py:286` and `services/ffmpeg_utils.py:257` both pass `-y`; `services/ytdlp_downloader.py:260-288` contains no `--no-overwrites` or `--no-clobber`; `services/segment_downloader.py:176` is an unconditional `os.replace`.

**Observation.**

*One derived path, written twice:*
```
after write 1: Collide_111.mp4 -> b'FIRST-WRITE'          size=11
after write 2: Collide_111.mp4 -> b'SECOND-WRITE-IS-LONGER' size=22
first write survives: False   (destroyed without prompt or warning)
```

*Two list entries that derive one name, driven through the product's own reader and resolver:*
```
position=0 url=…/video-1_222   name='Same Title_222.mp4'  work_tree='.Same Title_222_segments'  partial='Same Title_222.mp4.part'
position=1 url=…/video-1_222   name='Same Title_222.mp4'  work_tree='.Same Title_222_segments'  partial='Same Title_222.mp4.part'
position=2 url=…/video-1_999   name='Same Title_999.mp4'  work_tree='.Same Title_999_segments'  partial='Same Title_999.mp4.part'

(f) entries sharing the final name   : 2
    entries sharing the working tree : ['.Same Title_222_segments']
    entries sharing the partial name : ['Same Title_222.mp4.part']
```

The taxonomy row is verbatim: "one path reached by two concurrent writers, with the first artefact destroyed without a prompt or a warning." The batch runner admits both entries as separate tasks at once (`max_concurrent_downloads` defaults to 4, `config.py:189-191`), so the two writers are concurrent, and the first artefact is gone with nothing said.

**The position reaches the name in exactly one branch.** Measured:
```
with a title    : positions 0,1 -> Same Title_222.mp4, Same Title_222.mp4
without a title : positions 0,1 -> 0_222.mp4, 1_222.mp4
```
`security.py:107` and `:109` are the two branches. The batch position disambiguates only when the sanitised title is empty — the one case where the title contributes nothing and the two names would otherwise differ only by the id. With any title present, the position is discarded and two entries that share a title and an id produce one path. The phase's own row — "A position that reaches only one fallback branch is a finding" — is met.

**Deduplication count.** A source-wide search of `src/` for `dedup|unique|collision|disambig|suffix`-on-a-derived-name returns **0** relevant matches (the single hit is an unrelated docstring at `services/quality.py:103`). `cli.py:306-314` does not compare entries against each other.

**Reachability gate.** **Default.** Batch mode with a URL list is a first-class command (`cli.py`), and a repeated URL is a plain user input error, not an exotic one.

**Cross-reference.** Whether the artefact that survives is a *corrupt* interleaving is phase 03's transfer subject and is **not asserted here** — this finding claims only that the first write is destroyed silently and that the three names are shared.

**Recommendation.** Decide what the product means by a repeated entry and make it visible. The two coherent answers are to reject the duplicate in the reader at `cli.py:306-314` (a set membership test, and the reader already logs a `skipped_count` for invalid lines, so the shape exists), or to disambiguate the name in `_resolve_output_file` the way the empty-title branch already does, by folding `output_index` into the name whenever the path is already occupied. Effort: small for the reader, medium for the resolver (it must know what "occupied" means when the previous run left a file). Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-007 — The mode guarantee: requested `0o600`, measured `0o666`, access state not confining, zero independent controls, zero oracles that can fail here

- **ID:** ART-007
- **Severity:** HIGH
- **Type:** BEST-PRACTICE
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (a confidentiality guarantee that is not delivered)
- **Category:** ineffective fix / unstated assumption

**Affected location**
- `src/vkdownloader/config.py:340` — `log_path.parent.mkdir(parents=True, exist_ok=True)`, **no mode argument**.
- `src/vkdownloader/config.py:353-356` — `log_path.touch(mode=0o600)` and, in the other branch, `log_path.chmod(0o600)`.
- `src/vkdownloader/config.py:345` — the stated reason: "so subprocess output sanitized for SEC-002 is not readable by other local users".
- `src/vkdownloader/services/downloader.py:111-121` — `tempfile.mkstemp(suffix=".args", prefix="vk_ffmpeg_")` then `os.chmod(path, 0o600)` at `:119`.
- `src/vkdownloader/services/downloader.py:282-284` — the argfile's content: the m3u8 URL "containing signed CDN tokens and the cookie file path".
- `src/vkdownloader/services/segment_downloader.py:898` and `src/vkdownloader/utils/security.py:103` — the other two `mkdir` calls, **no mode argument**.
- Control families in `src/`, counted: `os.chmod` — 3 call sites (`downloader.py:119`, `ytdlp_downloader.py:82`, `config.py:356`); `Path.touch(mode=…)` — 1 (`config.py:354`); ACL / security-descriptor / ownership-change / creation-mask / `umask` — **0**.

**Observation.** Every artefact this phase names, created the way the product creates it, with the requested value, the measured value and the verbatim `icacls` listing:

| artefact | requested | measured | `icacls` principals |
|---|---|---|---|
| log file (`setup_logging`) | `0o600` | **`0o666`** | `NT AUTHORITY\SYSTEM:(I)(F)`; `BUILTIN\Administrators:(I)(F)`; `ADVMOSCOW\NMatveichev:(I)(F)`; a bare SID `(I)(F)` |
| ffmpeg argfile `vk_ffmpeg_*.args` | `0o600` | **`0o666`** | the same four, all `(I)` inherited |
| ffmpeg argfile's parent (system `TEMP`) | none (OS-provided) | `0o777` | the same four, `(I)(OI)(CI)(F)` |
| log file's parent (`logs/nested`) | **none — `mkdir` with no mode** | `0o777` | the same four, `(I)(OI)(CI)(F)` |
| working directory `.<stem>_segments` | **none — `mkdir` with no mode** | `0o777` | the same four, `(I)(OI)(CI)(F)` |
| output directory (`security.py:103`) | **none — `mkdir` with no mode** | `0o777` | the same four, `(I)(OI)(CI)(F)` |
| segment temp `NNNNN.ts.tmp` | none (plain `open`) | `0o666` | the same four, `(I)(F)` |
| segment final `NNNNN.ts` (post-`os.replace`) | none | `0o666` | the same four, `(I)(F)` |
| merge intermediate `batch_NNNNN.ts` | none (ffmpeg creates it) | `0o666` | the same four, `(I)(F)` |
| concat lists `batch_list_N.txt`, `final_list.txt` | none (plain `open`) | `0o666` | the same four, `(I)(F)` |
| playlist signature `.signature` | none (`write_text`) | `0o666` | the same four, `(I)(F)` |
| final artefact `<title>_<id>.mp4` | none (product never opens it) | `0o666` | the same four, `(I)(F)` |
| cookie file *(06's subject, listed for inventory only)* | `0o600` | `0o666` | the same four, `(I)(F)` |

The two values differ, the access state grants full control to four inherited principals with no deny entry and no explicit grant, the count of independent confining controls anywhere in the tree is **zero**, and the enclosing directories are created with no mode at all. All four of the quantities the phase's binding rule requires are measured.

**R3 — the oracle verdict, run out of band.** The suite contains **four** mode oracles and **all four are skipped** on the declared platform:

| oracle | guard | assertion body executes here? | value it would assert | out-of-band measurement of the same artefact |
|---|---|---|---|---|
| `tests/test_config.py:343` | `@pytest.mark.skipif(os.name == "nt")` | **no** | `mode == 0o600` | `0o666` |
| `tests/test_config.py:359` | `@pytest.mark.skipif(os.name == "nt")` | **no** | `mode == 0o600` | `0o666` |
| `tests/test_hls_downloader.py:539` | `@pytest.mark.skipif(os.name == "nt")` | **no** | `mode == 0o600` | `0o666` |
| `tests/test_hls_downloader.py:685` | `@pytest.mark.skipif(os.name == "nt")` | **no** | `mode == 0o600` | `0o666` |

`uv run pytest tests/ -q -rs` → `498 passed, 4 skipped`, and all four skips carry the same D-11 reason. Running the same measurements with the guard out of the equation gives `0o666` for every artefact an oracle names, so **each of the four would fail if it were allowed to run.** The phase's binding rule is satisfied: a guarantee with no oracle that can fail on the declared platform is a finding about the guarantee.

**Correction to a premise in the phase brief, recorded before the conclusion.** The brief states that "three of the suite's four mode oracles are inline-guarded and report success while executing no assertion body." The measured form is different: they are decorator-level `@pytest.mark.skipif(os.name == "nt")`, they **report as skips** rather than as passing, and pytest's `-rs` output names all four with their reason. They are not silent green; they are honest skips. The finding below does not rest on the premise as written and survives its correction. **Cited, not filed:** whether a skip is the right guard shape is phase 10's test-design subject and nothing is filed against it here.

**What the code already says, and is not the defect.** `config.py:347-352` and `downloader.py:114-118` both state, accurately, that `touch(mode=…)` is ignored on Windows and that `chmod` toggles only the read-only attribute, and both conclude that confinement is not offered there. The wording is not stale and no finding is raised against it. Phase 06's validator applied the same reasoning to SEC-001 and reclassified it `SPEC-DEVIATION → BEST-PRACTICE`; this finding takes the same type for the same reason. What remains after the accurate comment is the structural fact the comment does not address: **nothing in the tree confines these artefacts by any other means, and no test can fail on the platform where the work happens.**

**Severity rationale.** The taxonomy row is "the requested mode and the mode in force differ for an artefact and no other control in the tree compensates," which is what the table above shows. It is not the "stale reason for a mode that does not hold" row, because the stated reason is accurate, and the artifact is not named after a mode that has drifted.

**UNVERIFIED marker — POSIX.** The enforcement outcome on a POSIX host was **not** observed. `os.chmod(path, 0o600)` and `Path.touch(mode=0o600)` deliver owner-only confinement there; that is the behaviour the code documents and the behaviour the four oracles assert. This finding makes no claim about it, and no severity is stated for a host that was not observed. It is a finding about the declared platform's outcome and about the absence of any compensating control, nothing more.

**Documented skip §2.1 applies.** A second local identity was not available, so the ACL is reported from `icacls` and from the measured mode, and no read by another principal was attempted.

**Reachability gate.** The log file is **opt-in** (`VKDOWNLOADER_LOG_FILE` / `--log-file`; the field default is `None`). The argfile is **opt-in** (`--method ffmpeg`). Every artefact requested with no mode at all — the working tree, the output directory, the segments, the concat lists, the final artefact — is reached at the **default**.

**Cross-reference.** The cookie file is phase 06's; it appears in the table above for inventory completeness and **nothing about it is filed here**. Phase 05's TRN-001, confirmed independently in this run, means the argfile the `chmod` protects is never opened by the muxer at all — that sharpens the finding rather than softening it, and it is context here, not a claim.

**Recommendation.** Two changes, and the first is the one that matters. (1) Decide what the product wants for the log file and the argfile on a host where POSIX modes do not apply, and implement it with a mechanism that does apply — an explicit DACL, or a directory the product creates with a restrictive mode and confines — or state plainly in the configuration documentation that the artefact is not confined there. (2) Move at least one of the four oracles off the platform guard: the artefact's *requested* mode is observable everywhere (a `stat` on a Windows file reports `0o666` whatever was asked for, and the request is visible in the source), so an oracle that asserts the request is enforced where the platform enforces it and asserts the request is *recorded* where it does not would run on every host and fail when either half drifts. Effort: small for (2), medium for (1). Priority: recommended for (2), recommended for (1) — the confidentiality claim at `config.py:345` is the product's own and it is not currently met on the platform the product ships against.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-008 — The ffmpeg argfile survives a forced termination carrying the signed CDN URL, and nothing in the tree can find it

- **ID:** ART-008
- **Severity:** HIGH
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (a residue class the tree cannot match or reconcile)
- **Category:** runtime error, not caught

**Affected location**
- `src/vkdownloader/services/downloader.py:111` — `fd, path = tempfile.mkstemp(suffix=".args", prefix="vk_ffmpeg_")`, in the system TEMP directory.
- `src/vkdownloader/services/downloader.py:113-121` — close, `chmod`, write, `yield`; `:123-124` — the `finally` that unlinks.
- `src/vkdownloader/services/downloader.py:282-284` — the content: the m3u8 URL "containing signed CDN tokens and the cookie file path".
- `.gitignore:22` — `*_cookies.txt`, the nearest ignore pattern.

**Observation.** The product's own `_temp_argfile` entered in a child process, then that process ended without a chance to clean up:

```
before: 3 vk_ffmpeg_*.args in the system TEMP directory
while the child is inside _temp_argfile: vk_ffmpeg_x1m255km.args
  size=193  measured mode=0o666
  content carries a signed CDN URL and the cookie file path
end condition: taskkill /PID <pid> /T /F
after : 4 vk_ffmpeg_*.args in the system TEMP directory
  SURVIVOR: vk_ffmpeg_x1m255km.args  size=193  mode=0o666
```

**Per-pattern verdicts for this residue class**, against every sweep the tree owns:

| pattern the product uses | matches `vk_ffmpeg_*.args`? |
|---|---|
| `_temp_argfile`'s `finally` unlink | yes — and it is not reached when the process is ended |
| `segments_dir.glob("*")` / `glob("*.ts")` (all working-tree sweeps) | **no** — the file lives in the system TEMP directory, not in a working tree |
| `ytdlp_downloader.py:444` DF-008 unlink | **no** — different name, different directory |
| `.gitignore` | **no** — `*_cookies.txt` does not match `vk_ffmpeg_*.args`, and the file is not in the repository anyway |

There is **no enumeration of the system TEMP directory anywhere in `src/`.** The only removal is the `finally` at `downloader.py:123-124`, and a forced termination does not reach a `finally`. The three pre-existing `vk_ffmpeg_*.args` this run found on entry are the same accumulation phase 06's validator recorded for the cookie artefacts, observed independently here for the argfile.

**UNVERIFIED marker.** The **content** of the argfile in this run is the product's own generated content, with a synthetic token substituted for the URL by the probe. That the real signed CDN token reaches this file is the product's stated intent at `downloader.py:282-284` and is corroborated by the file's 193 measured bytes; the real token's value is not asserted.

**Reachability gate.** **Opt-in** — `--method ffmpeg`. The file is written at `downloader.py:282`, before the ffmpeg branch's subprocess spawn.

**Cross-reference.** Phase 05's TRN-001, confirmed independently in this run, means the muxer never opens this file — so the residue carries a live URL into a directory where nothing will read it and nothing will remove it. That is context for the recommendation, not a claim of this phase's. The credential *file* is phase 06's; the argfile is assigned to this phase by the phase brief and is filed here on that basis.

**Recommendation.** Put the argfile where the product already knows how to sweep — inside the working tree — or give the system TEMP directory one sweep that is safe to run (a name-prefixed, age-bounded sweep of `vk_ffmpeg_*.args`, which cannot collide with a concurrent instance's live file because the name is per-invocation and `mkstemp` guarantees uniqueness). The first is cleaner and reuses `_cleanup_segments`. Effort: small. Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-009 — No containment root; the one comparison is warn-only and is suppressed at the call site that creates the output directory

- **ID:** ART-009
- **Severity:** MEDIUM
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness; a guard that refuses nothing)
- **Category:** ineffective fix / unstated assumption

**Affected location**
- `src/vkdownloader/utils/security.py:26-79` — `validate_output_path`. The only two tests are the literal substring `".."` (`:47` and `:59`) and one `relative_to(repo_root)` (`:66-67`).
- `src/vkdownloader/utils/security.py:65` — `repo_root = Path(__file__).resolve().parent.parent.parent`.
- `src/vkdownloader/utils/security.py:75-77` — the failure branch of the containment comparison: `except ValueError: pass`.
- Call sites: `security.py:102` (`warning=False`, followed by `mkdir` at `:103`); `segment_downloader.py:895` (default `True`); `ytdlp_downloader.py:415` (`warning=False`).

**Observation — what the guard admits.** Driven through the product's own validator, both `warning` values, in a temp directory:

| subject | `warning=True` | `warning=False` |
|---|---|---|
| `C:\Windows\System32` | ACCEPTED | ACCEPTED |
| `Path("/etc")` | ACCEPTED → `C:\etc` | ACCEPTED → `C:\etc` |
| `\\server\share\video.mp4` | ACCEPTED | ACCEPTED |
| `//server/share/video.mp4` | ACCEPTED | ACCEPTED |
| `D:\somewhere\else` | ACCEPTED | ACCEPTED |
| the declared repository root | ACCEPTED | ACCEPTED |
| the source tree | ACCEPTED | ACCEPTED |
| `<tmp>\a..b` | **REJECTED** `PATH_TRAVERSAL` | **REJECTED** `PATH_TRAVERSAL` |

Everything outside any directory the operator chose is admitted, on a network path and on a system directory alike. The taxonomy row is verbatim: "no containment root, so nothing refuses a path outside any directory the operator chose."

**Observation — the comparison, as two values, recorded as a warn-only comparison.** `Path(security.py).resolve().parent.parent.parent` measured **`C:\py_exp\mko_vkideo\src`**; the declared repository root is **`C:\py_exp\mko_vkideo`**. The two are not equal, so the variable named `repo_root` at `:65` is the `src/` directory, and the warning a user would see names a root one level too deep. Per the phase's rule, the comparison is recorded as warn-only: its failure branch is `pass`, it raises nothing, and it is the *sole* containment control in the tree. A source-wide search for `ALLOW|allowlist|allowed_|is_relative_to\(|commonpath` returns **no** containment primitive — the eight hits are unrelated `continue`/`allow` comments in other modules.

**Which call sites enable the comparison and which suppress it — recorded as a set.** Three sites, two of which suppress it, and **the one that creates the output directory is one of them**:

| site | subject it validates | `warning` | what it is immediately followed by |
|---|---|---|---|
| `security.py:102` | a **directory** | `False` | `mkdir(parents=True, exist_ok=True)` at `:103` |
| `segment_downloader.py:895` | a **whole file path** | `True` (default) | `segments_dir` composed at `:897`, `mkdir`'d at `:898` |
| `ytdlp_downloader.py:415` | a **whole file path** | `False` | partial-existence probe; DF-008 unlink at `:444` |

Neither composed path re-enters the validator: the derived **final name** at `security.py:107`/`:109` is never validated after the directory it will be written into is, and the **working directory** at `segment_downloader.py:897` is composed from a validated prefix and a validated stem but is never itself validated. The diagnostic is therefore suppressed at the composition site, which is exactly where it would have had content.

**Also recorded, without a separate finding — directory creation where the validator's subject is written.** `security.py:103` is not guarded against the output path already existing as a file. Measured: `builtins.FileExistsError winerror=183 errno=17: [WinError 183] Cannot create a file when that file already exists: '…\not_a_dir'`. `exist_ok=True` does not suppress that when the existing object is not a directory. The exception is untyped and uncaught, so the user receives `cli.py`'s generic "An error occurred during download" and exit 1 with no indication of which path was at fault. The quality of that message is phase 08's subject and is not filed here.

**Reachability gate.** **Default.** All three call sites are on the ordinary path of every download.

**Recommendation.** Decide what the guard is for. Either give it a root — the configured `download_dir` is the obvious candidate and already exists as a setting — and make the comparison refuse rather than warn, or remove the containment comparison and the `repo_root` variable entirely and keep the `..` check, which is doing real work. Half a control, disabled at its only interesting call site, is the worst of the three options; the current state is the middle one. Fix the `repo_root` derivation either way, or the diagnostic that does fire reports the wrong directory. Effort: small. Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-010 — A legitimate directory named with a double dot is refused under a "Path traversal detected" label

- **ID:** ART-010
- **Severity:** MEDIUM
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness)
- **Category:** ineffective fix / unstated assumption

**Affected location**
- `src/vkdownloader/utils/security.py:47` — `if ".." in path_str:` — a **substring test**, not a path-component test.
- `src/vkdownloader/utils/security.py:48-50` — the refusal: `DownloadError(f"Path traversal detected in output path: {path}", ErrorCode.PATH_TRAVERSAL)`.
- `src/vkdownloader/utils/security.py:59` — the same test, in the string branch.

**Observation.** Driven through the product's own validator:

```
<tmp>\a..b   warning=True   REJECTED  DownloadError  code=ErrorCode.PATH_TRAVERSAL
                                  msg=Path traversal detected in output path: C:\…\a..b
<tmp>\a..b   warning=False  REJECTED  (identical)
```

`a..b` is an ordinary directory name, legal on every supported filesystem, containing no parent-directory component at all. The substring test cannot tell the two apart. The taxonomy row is verbatim: "a guard that refuses a legitimate user path under a security-labelled error" — and the label is the part that matters operationally, because `ErrorCode.PATH_TRAVERSAL` tells the operator they were blocked for a security reason when in fact their directory name contains two dots.

**The refused form has a double-dot directory that is a real, common case.** Any user whose folder is `Season 2..3`, `v1.0..v1.1`, `part 1 (2019..2020)`, or who has a directory left behind by an extraction tool that uses `..` in a name cannot use `--output` against it. The only workaround is to move the download, and the error says nothing about that.

**Reachability gate.** **Default.** `_resolve_output_file` calls the validator at `security.py:102` on every download.

**Recommendation.** Test path **components** rather than the joined string: `if ".." in path.parts`. That is the standard formulation, it is a one-line change, and it keeps every genuine traversal refused while letting a legitimate name through. If the substring test is deliberate for defence in depth, keep it as a secondary check but refuse with a message that names the real reason. Effort: trivial. Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-011 — The truncation bounds a component of the path, not the path

- **ID:** ART-011
- **Severity:** MEDIUM
- **Type:** SPEC-DEVIATION
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (correctness)
- **Category:** ineffective fix / unstated assumption

**Affected location**
- `src/vkdownloader/utils/security.py:23` — `return title.replace(_INVALID_FILENAME_CHARS, "_").strip()[:100]`. The bound is on the sanitised title, and nothing downstream re-applies it.
- `src/vkdownloader/utils/security.py:107` and `:109` — the name is composed from that bounded title plus `video.id`, which is unbounded.
- `src/vkdownloader/utils/security.py:103` and `src/vkdownloader/services/segment_downloader.py:895` — the validated subjects; neither is length-checked.
- The cap that exists, precisely: `security.py:23`, 100 characters of title.

**Observation.** Driven through the product's own sanitiser and resolver:

```
title component  = 300 chars in, 100 out                       <- bounded
derived last component length = 114
full path length             = 355
  C:\Users\…\Temp\vk_r4_root_…\DDDD…(180)…\AAA…(100)…_456239018.mp4
  created at that path: YES
deep path length = 777 -> building file ...
  created at deep path: YES
```

The truncation is real and does bound what it claims to bound: a 300-character title produces a 100-character component. What it does not bound is the last component (114 characters) or the path that contains it. No length check exists anywhere on the path — a source-wide search for a path-length or artefact-size ceiling returns one unrelated constant, `MAX_JSON_BODY_BYTES` at `infrastructure/network_monitor.py:23`, which bounds an HTTP response body, not a file.

**UNVERIFIED marker — the failure was not observed.** The taxonomy row for this finding is "the truncation bounds a component of a path but not the path," and it is filed on that structural fact. **The runtime failure was not reproduced on this host**: Windows accepted both a 355-character and a 777-character path, and the file was created and read back at each. The marker is required by the phase's rules and is recorded here: the structural gap is established, the write failure it would eventually cause on a host with a shorter path limit is not. The path-length limit that would bite is a property of the host's filesystem and the calling API, and no such limit was reached on this one.

**Why SPEC-DEVIATION.** The docstring at `security.py:17-20` describes the bound as `[:100]` of the title, which is accurate; the deviation is between that bound and the property the caller actually needs, which is a usable path. The docstring's own wording is phase 09's subject and nothing is filed there.

**Reachability gate.** **Default.** `_resolve_output_file` runs on every download. The observed 777-character path needs a deeply nested `download_dir`, which a user can supply through configuration.

**Recommendation.** Decide which component of the problem to bound and say so. If the intent is "the file name will not be absurdly long", the current `[:100]` already does that and the finding is closed by documenting it as a title bound rather than a path bound. If the intent is "the write will succeed", the bound belongs on the composed path, applied after the id and the extension are in, with the truncation applied to the *parent* directory when the full path does not fit. The first is a comment; the second is a small helper. Effort: trivial for the first, small for the second. Priority: recommended for the second only if the product intends the stronger guarantee; recommended either way to make the bound say what it bounds.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-012 — The working set peaks at 3.15× the final artefact and the only ceiling covers the merge stage, not the download that precedes it

- **ID:** ART-012
- **Severity:** MEDIUM
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (operational)
- **Category:** design weakness

**Affected location**
- `src/vkdownloader/services/ffmpeg_utils.py:367-395` — `_required_merge_bytes`: `total_segment_size * 2 + _MERGE_SPACE_MARGIN_BYTES (64 MiB)`.
- `src/vkdownloader/services/ffmpeg_utils.py:398-448` — `_check_merge_space`; `shutil.disk_usage(segments_dir).free` at `:417`.
- `src/vkdownloader/services/ffmpeg_utils.py:483-486` — the probe, evaluated **once**, before the first batch.
- `src/vkdownloader/services/segment_downloader.py:598-616` — the download stage, which accumulates every segment on the volume with no ceiling of any kind.

**Observation.** A real batched merge, driven through the product's own `_merge_segments_batched` with the muxing binary on PATH, sampled at 10 ms cadence throughout:

```
(a) muxing binary on PATH: C:\ffmpeg\ffmpeg.EXE
(d) input total  : 2585000 bytes across 250 segments
    merge returned: …\Synthetic Title_456239018.mp4  in 1.42s
    samples taken : 56 at 10 ms cadence
(c) PEAK total   : 3627300 bytes at t+0.59s
    final artefact: 1149894 bytes
(e) peak / artefact = 3.154
(e) peak / input    = 1.403
(e) non-numbered files at the peak: ['batch_00000.ts', 'batch_list_0.txt']
(c) last sample     : 0 bytes        work dir after: 0 entries
```

The peak is a **transient** the endpoints do not show: the directory ends empty and the artefact is 1.15 MB, while the high-water mark was 3.63 MB. The non-numbered files present at the peak are the merge intermediates, which ART-004 covers separately and which are named here only because the phase's own row asks for them.

**Caveat that travels with the ratio.** The synthetic segment set is 250 copies of one 10 340-byte MPEG-TS stream, which carries per-segment container overhead a real CDN segment set would not; that inflates the ratio against the *final artefact* (3.15×) well above what a real download would produce. The ratio against the *input* (1.40×) is the transferable figure, and it is the one that describes the algorithm: the merge holds, at most, the remaining inputs plus the batch temps it has written, and then the batch temps plus the growing output.

**Which ceilings exist, measured against the question.** The taxonomy row is "the working set peaks at a multiple of the final artefact with no ceiling above it and no free-space probe anywhere."

- Artefact size cap: **none.**
- Output size cap: **none** (the one size constant in `src/` bounds an HTTP body).
- Free-space probe: **one**, and it is at `ffmpeg_utils.py:417` — so the row's second clause is not satisfied as written, and the finding is filed on the first clause plus the probe's scope.
- **The cap that exists, with what it bounds:** `_required_merge_bytes` bounds the free space required *at the merge stage*, computed from the bytes already on disk. On the observed run it required 2 × 2 585 000 + 67 108 864 = **72 278 864 B (68.9 MiB)** against a measured peak of 3 627 300 B (3.5 MiB) — conservative, and not the defect. What is unbounded is the stage **before** it: the download writes every segment to the volume, and nothing probes the volume, declares a size, or stops the download at any point in that stage.

**Cross-reference.** The archived register at `.ai/plans/done/01-confirmed-code-defects_DONE.md` carries `D-09 · MEDIUM · Merge amplification is unbounded` with a measured 2.96× and the note "no output-size or free-space ceiling." The free-space probe is the part that landed in `eedfff0`; this finding is the remaining half — the download-stage accumulation — and is filed on the current tree, not on the register's. The register's line references have drifted and were not used.

**Reachability gate.** **Opt-in** — the segment path (`--method ffmpeg`).

**Recommendation.** Two bounds, in order of value. (1) Probe free space **before the download stage** the way the merge already does, using the segment count and the highest observed segment size, and stop with the product's own typed error rather than filling the volume. This is the same helper with a different input. (2) Decide whether a declared artefact-size ceiling is a product promise or not; if it is not, the merge probe's `2 ×` is a heuristic that should be named as one in the comment at `ffmpeg_utils.py:367-395`. Effort: small for (1), trivial for (2). Priority: recommended for (1).

**Validation Note.** *(empty — awaiting validation)*

---

### ART-013 — An interruption between the write and the move leaves `NNNNN.ts.tmp`, which no sweep, no count and no index enumeration matches

- **ID:** ART-013
- **Severity:** HIGH
- **Type:** RUNTIME-ERROR
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** mandatory (a residue class the tree cannot match or reconcile)
- **Category:** runtime error, not caught

**Affected location**
- `src/vkdownloader/services/segment_downloader.py:170-180` — the sequential unit: `temp_path = output_path.with_suffix(suffix + ".tmp")` (`:172`), `with open(temp_path, "wb")` (`:174-175`), `os.replace(temp_path, output_path)` (`:176`), and `except: temp_path.unlink(missing_ok=True)` (`:178`) then `raise`.
- `src/vkdownloader/services/segment_downloader.py:236-244` — the parallel unit, identical shape.
- The sweeps: `segment_downloader.py:418-419` (`glob("*")`), `:599` (`glob("*.ts")` count), `:133` (`glob("*.ts")` removal), `:937` (`glob("*.ts")` count for the reporter), and `ffmpeg_utils.py:492` (index enumeration `{i:05d}.ts`).

**Observation.** The product's own `_download_segment` writing a 120 MiB unit, with the parent ending the process the moment the temporary name appeared:

```
(a) temporary name        : 00000.ts.tmp
    final name            : 00000.ts
    operation that moves  : os.replace(temp_path, output_path)
    write-failure path    : except -> temp_path.unlink(missing_ok=True) -> raise
(c) end condition         : process killed 1.083s after start
    mechanism             : taskkill /PID <pid> /T /F
(b) measured mode of the temp name while it existed: 0o666
INVENTORY AFTER THE KILL:
    00000.ts.tmp             size=124080000    mode=0o666
temp name survives : True
final name exists  : False
```

**Per-pattern verdicts for this residue class**, against every sweep the tree owns:

| pattern the product uses | matches `00000.ts.tmp`? |
|---|---|
| `_cleanup_segments` — `segments_dir.glob("*")` at `:418` | **yes** — and it is reachable only from the merge-success branch at `:617-618` |
| `_log_preserve_segments` — `glob("*.ts")` at `:937` | **no** — not counted, so the reporter's count is short by one and the `if segment_count > 0` guard at `:938` can pass on a tree that holds only this |
| `_clear_stale_segments` — `glob("*.ts")` unlink loop at `:133` | **no** — never removed, even when the signature differs |
| the merge's own enumeration — `{i:05d}.ts` at `ffmpeg_utils.py:492` | **no** — the merge asks for `00000.ts`, which does not exist; it never asks for the temp |
| `.gitignore` `*_segments/` | matched only via the parent directory, so the residue is ignored in the repository by accident of location, not by design |

One of five patterns matches, and that one runs only when the merge has already succeeded — which is the one end on which the unit's `except` branch at `:178` would also have removed it. On every end where the process actually dies, the class survives unmatched.

**The measured bound.** 124 080 000 B for the 120 MiB unit this probe used. A real segment is one HLS segment of a real video; the shape, not the magnitude, is the finding, and the magnitude is stated only so the number is not mistaken for a real segment size.

**Reclaimability, stated precisely.** The unit temp is reclaimed only if and only if the **same segment index** is downloaded again, because the write overwrites the same name and the `os.replace` then consumes it. A playlist change does not reclaim it: `_clear_stale_segments` globs `*.ts` and the temp is not one, so it survives a change of playlist as readily as it survives a failure.

**UNVERIFIED marker.** POSIX rename atomicity is **not** claimed. On this host the rename was observed to carry the source entry's mode to the destination (`0o666` before, `0o666` after); the atomicity guarantee is a property of that host's filesystem and is not exercised by this finding.

**Reachability gate.** **Opt-in** — the segment path (`--method ffmpeg`).

**Cross-reference.** NET-001 (phase 03) governs the destruction order of the *batch* temps in the same working tree and is cross-referenced here, not re-filed. This finding is about the per-unit temp, which NET-001's accounting does not include.

**Recommendation.** Two lines, both of which close the gap without changing the write's atomicity. (1) Extend the stale-segment removal at `segment_downloader.py:133` to the temp form (`*.ts.tmp` alongside `*.ts`), so a playlist change and a partial write are both reconciled by the sweep that already exists. (2) Either make `_cleanup_segments` reachable on the failure paths — which is ART-005's recommendation and shares the fix — or accept that the temp survives and make the sweep at (1) the only reclaim path, in which case it must not be gated on the signature matching. Effort: trivial. Priority: recommended.

**Validation Note.** *(empty — awaiting validation)*

---

### ART-014 — The shared sanitiser handles no reserved device name and no trailing dot, and the derivation's fixed suffix is the only barrier

- **ID:** ART-014
- **Severity:** LOW
- **Type:** BEST-PRACTICE
- **Phase:** 07 — filesystem artefacts and name derivation
- **Classification:** advisory (best practice, recommended)
- **Category:** design weakness

**Affected location**
- `src/vkdownloader/utils/security.py:15-23` — `sanitize_title`, a **shared utility** with two callers: `security.py:105` (name derivation) and `services/downloader.py:666` (display via `title_callback`).
- `src/vkdownloader/utils/security.py:107` and `:109` — the derivation, which always appends `_{video.id}.mp4` or `{index}_{video.id}.mp4`.

**Observation — the creation half only.**

| name attempted | created? | `is_file()` | size | mode |
|---|---|---|---|---|
| `control.txt` (ordinary control) | yes | `True` | 2 | — |
| `CON` | "yes" | **`False`** | 0 | `0o0` |
| `CON.txt` | "yes" | **`False`** | 0 | `0o0` |
| `NUL` | "yes" | **`False`** | 0 | `0o0` |
| `AUX.txt` | **no** — `FileNotFoundError: [Errno 2]` | — | — | — |
| `CON_456239018.mp4` (the derived shape) | yes | `True` | 1 | `0o666` |
| `NUL_456239018.mp4` (the derived shape) | yes | `True` | 1 | `0o666` |

The bare device names do not fail loudly. A write to `CON` or `NUL` returns without error and leaves **no file at all** — the bytes went to the device, and the caller has no signal. `AUX.txt` is worse: it raises an unrelated `FileNotFoundError` on a path that plainly exists.

**The caveat, and it travels with the result in both directions.** The **removal** half of this observation is **confounded** and no claim is made from it in either direction. Removing `CON`, `CON.txt` and `NUL` all returned `PermissionError winerror=5`; that is a device-resolution artefact of the path and says nothing about whether a residue was left behind. Only the creation half is evidence. This is the binding rule's demand that a confounded observation be stated and then bounded, and the bound here is that the finding rests entirely on the creation column.

**The measured bound, and the scope rule applied.** The last component the product derives **can never equal a bare device name**, because `security.py:107` and `:109` always append `_{video.id}.mp4` or `{index}_{video.id}.mp4` — at minimum eleven characters after the title. `CON_456239018.mp4` and `NUL_456239018.mp4` are ordinary files, created and removed cleanly, as the table shows. Trailing dots behave the same way: `title...` sanitises to `title...` and derives `title..._456239018.mp4`, which is created and read back fine, because the dot is never last.

So this is **a property of a shared utility, filed as a best practice with that scope stated** — not a write failure that occurs today, and not claimed to be one. The utility has two callers; the display caller has no filesystem exposure at all, and the derivation caller's fixed suffix removes the exposure. The finding is that the utility is named and documented as a filename sanitiser and is not one, and the only thing standing between it and a device write is an accident of a different line.

**Reachability gate.** `_resolve_output_file` is reached at the **default**; the device-name branch is not reachable through the current derivation at all, and that is the point of the scope statement.

**Recommendation.** Either rename the utility to what it is — a display-and-derivation title normaliser — or make it a real filename sanitiser: strip trailing dots and spaces, and prefix a device basename with an underscore. The second is a few lines and makes the utility safe for the next caller that does not append an id. Do not do it only because of a hypothetical: the value is that the function's name and docstring then match what it does, which is what stops the next caller from trusting it. Effort: trivial. Priority: recommended, as a best practice.

**Cross-reference.** The docstring's own completeness claim at `security.py:18` is phase 09's subject; nothing is filed there. Phase 10 owns whether a shared utility without a direct unit test for these cases is a gap; no coverage finding is filed here.

**Validation Note.** *(empty — awaiting validation)*

---

## Retention matrix — the four adjacent paths

Every cell below was driven through the product's own code against a loopback origin on `127.0.0.1`. "Survivor" is what the inventory showed after the process ended; "matched by" is the set of the product's own patterns that find that class.

| residue class | E1 completes | E2 non-zero | E3 retries exhausted | E4 forced termination | matched by |
|---|---|---|---|---|---|
| final artefact `<title>_<id>.mp4` | present (intended) | absent | absent | absent | n/a — the deliverable |
| child partial `<title>_<id>.mp4.part` | absent (renamed away) | absent | absent | **present, 31 744 B** | nothing in the tree; `.gitignore:16` `*.part` only affects the repository |
| working tree `.<stem>_segments/` | removed | **present, empty, `0o777`** | present, 249 segments + `.signature` | present, 8 segments + `.signature` | `_cleanup_segments` (`glob('*')`) — success path only |
| unit temp `NNNNN.ts.tmp` | consumed by the move | n/a | n/a | **present, 124 080 000 B** | `_cleanup_segments` only — and that on the success path |
| merge intermediate `batch_NNNNN.ts` | consumed by the final merge | n/a | n/a | present if killed mid-merge | `glob('*.ts')` in the count **and** in the staleness sweep — which is the defect (ART-004) |
| concat list `batch_list_N.txt` / `final_list.txt` | consumed | n/a | n/a | present if killed mid-merge | `_cleanup_segments` only |
| ffmpeg argfile `vk_ffmpeg_*.args` | consumed by the `finally` | consumed | consumed | **present, 193 B** | the `finally` only; nothing enumerates the system TEMP directory |
| playlist signature `.signature` | removed with the tree | written on the next visit | written | written | `_cleanup_segments` only |

**Does a later run reclaim a survivor?** Measured, not assumed:

- **Segment-path residue** (S4: 8 segments + `.signature`): a later run over the same playlist **does** reclaim it — the working tree is gone and the artefact exists. The reclaim is the resume working, not a sweep.
- **Child partial** (`<name>.mp4.part`): a later run that **fails** leaves it and grows it (7 168 B → 1 246 380 B across two runs); a later run that **succeeds** consumes it, because yt-dlp's own rename runs. The product removes it on no end.
- **Argfile**: no reclaim path exists at all — nothing in `src/` enumerates the system TEMP directory. Three pre-existing `vk_ffmpeg_*.args` were present on entry to this phase's measurement.

**Merge-path residue after a mid-merge kill** is covered in ART-004, including the fact that the staleness check short-circuits on a matching signature and never reaches its own removal.

**The free-space probe is a recorded fact, not a gap.** `ffmpeg_utils.py:398-448` computes the requirement from the bytes already on disk, evaluates it once at `:483-486` before the first batch, and raises the product's own typed `DownloadError` with three recovery suggestions. It is a working, tested mechanism — `tests/test_hls_downloader.py` has 5 matches for `_required_merge_bytes` — and this phase does not file against it. Its scope, and the stage it does not cover, are ART-012.

---

## Verification baselines (R10a), measured at `a335b2a`

| command | result |
|---|---|
| `uv run pytest tests/ -q -rs` | **498 passed, 4 skipped** — all four skips are the D-11 mode oracles, named with their reason |
| `uv run ruff check src tests` | exit 0 — `All checks passed!` |
| `uv run ruff format --check src tests` | exit 0 — `52 files already formatted` |
| `uv run mypy src` | exit 0 — `Success: no issues found in 30 source files` |
| `uv run mypy src tests` | exit 1 — 55 errors, **0 in `src/`**, all 55 in six test files. Recorded as the baseline; phase 10's test-typing subject. |

Evidence: `.temp/evidence/r10_pytest.txt`, `r10_ruff.txt`, `r10_ruffformat.txt`, `r10_mypy_a335b2a.txt`.

## Coverage counts (R10b) — cited for this phase's subjects, no finding filed

Per-symbol match counts in `tests/`, excluding `.kilo/worktrees/`:

| symbol | matches | | symbol | matches |
|---|---|---|---|---|
| `sanitize_title` | 9 | | `_cleanup_segments` | 4 |
| `_resolve_output_file` | 8 | | `_clear_stale_segments` | **0** |
| `validate_output_path` | 50 (mostly patch targets) | | `_log_preserve_segments` | **0** |
| `download_hls_with_resume` | 29 | | `_check_merge_space` | **0** |
| `_merge_segments_batched` | 33 | | `_tally_and_merge` / `downloaded_count` | **0** |
| `_merge_batch_segments` | 7 | | `os.replace` | **0** |
| `_perform_final_merge` | 7 | | `_required_merge_bytes` | 5 |
| `_temp_argfile` | 8 | | `_download_segment_sequential` | 10 |
| `final_list` / `batch_list` | 7 | | `chmod` / `0o600` | 18 (4 oracles, all skipped) |

The zeros are recorded because they bear on which findings a reader can expect to be caught by the suite, not as a finding. Phase 10 owns the coverage question and nothing is filed here. The coverage counts are a health indicator, and the phase brief's rule that no finding may be filed on the basis of a coverage count is honoured: ART-005, ART-013 and ART-014 are all filed on an observed artefact or an observed exception, with the counts cited only so a validator can tell whether a regression test can be written against them.

---

## Documented Skips (recorded, not clean results)

### §1 Declared-platform limits, recorded before any finding

| # | Limit | What was still established |
|---|---|---|
| 1.1 | The host is Windows; POSIX permission-bit enforcement was not exercised. | The requested value per artefact, the measured value per artefact, the verbatim `icacls` listing per artefact, the per-family count of independent confining controls, and the mode of each parent directory. Filed as ART-007 with the POSIX enforcement outcome marked **UNVERIFIED**; no severity is stated for a host that was not observed. |
| 1.2 | A second local identity was not available. | The effective access state from `icacls` and from the measured mode. No read by another principal was attempted or claimed. |
| 1.3 | No real network, no real CDN, no real origin. | A loopback `127.0.0.1` origin with a synthetic payload, driven through the product's own code. The **content** the real origin supplies is never asserted — recorded as an UNVERIFIED marker on ART-001 (title), ART-008 (signed CDN token) and ART-012 (segment shape). |

### §2 Items that could not be executed, and are not clean results

| # | Item | Why | Consequence recorded |
|---|---|---|---|
| 2.1 | POSIX `os.chmod` enforcement of `0o600` on the log file and the argfile. | Host is Windows. | ART-007's severity rests on the declared platform's measured outcome and on the absence of any compensating control. The POSIX outcome is UNVERIFIED. |
| 2.2 | *Anticipated as a possible skip; **not a skip**.* A subsequent merge over a directory holding a leftover `batch_NNNNN.ts`. | — | **Executed.** The merge was driven and raised `FileNotFoundError: Missing segment files for merge: ['00120.ts', …]`. ART-004 is filed on the observed chain, not on a recorded absence. |
| 2.3 | *Anticipated as a possible skip; **not a skip**.* A leftover `NNNNN.ts.tmp` inside the working tree. | — | **Executed.** The product's real segment write was interrupted between the write and the move and the class observed at 124 080 000 B. ART-013 is filed on the observation. |
| 2.4 | yt-dlp's own intermediate set on a fragment-resume path (`.ytdl`, `.temp` and the per-fragment names). | A direct media URL over HTTP does not exercise the fragment path. | The `.part` class is observed and filed (ART-002). The fragment intermediates are **not** claimed to be absent and not claimed to be present; any sweep that would need to match them does not exist in `src/` either, and that statement rests on the source search, not on an executed fragment download. |
| 2.5 | ffmpeg's behaviour when it exits mid-write, leaving a partially written `batch_NNNNN.ts` or a partial final artefact. | Cannot be forced deterministically with the installed binary. | Not claimed. The `batch_*.ts` residue in ART-004 is reached by process termination, which was driven, not by a truncated ffmpeg write. |
| 2.6 | Two product processes running concurrently over one working tree (the route by which ART-003's non-regular entry could arise productively). | One process per invocation in this audit's harness. | The ART-003 trigger bound is stated on the finding and this is the route it names as unobserved. |
| 2.7 | Windows `MAX_PATH` behaviour at the limit. | Python's long-path handling accepted 777 characters here. | ART-011's UNVERIFIED marker. The structural gap is filed; the write failure is not claimed. |
| 2.8 | The ffmpeg/segment path at the **default** configuration. | `--method auto` never reaches it — see the reachability ledger. | Five findings are filed with the opt-in gate stated and are **not** promoted to default reachability. |
| 2.9 | `icacls` verification that the ACL is effective for a non-inheriting principal. | Single-identity host. | ART-007's access-state claim is from the listing and the measured mode only. |

### §3 Scratch inventory, all under the gitignored `.temp/`, all removed at the end of this phase

`.temp/r2_modes.py`, `.temp/r4_names.py`, `.temp/r1_matrix.py`, `.temp/r1_child.py`, `.temp/r1_segments.py`, `.temp/r1_seg_child.py`, `.temp/r1_tail.py`, `.temp/r1_argfile.py`, `.temp/r7_child.py`, `.temp/r7_r8_r9.py`, `.temp/trn001.py`, `.temp/origin.py`, `.temp/media/{video,seg,big}.mp4`, `.temp/media/seg.ts`, `.temp/runs/`, `.temp/segruns/`, `.temp/r7/`, `.temp/r8/`, `.temp/r8f/`, `.temp/r9/`, `.temp/ytdlp_survivor/`, `.temp/evidence/` (twelve evidence files: `r2_modes.txt`, `r4_names.txt`, `r1_matrix.txt`, `r1_segments.txt`, `r1_tail.txt`, `r1_argfile.txt`, `r7_r8_r9.txt`, `trn001.txt`, `r10_pytest.txt`, `r10_ruff.txt`, `r10_ruffformat.txt`, `r10_mypy.txt`, `r10_mypy_a335b2a.txt`, `r10_skips.txt`).

`git status --short src tests` is empty at the end of this phase. No file under `src/` or `tests/` was created, modified or deleted.

### §4 Explicitly not filed, and where it went

| Not filed here | Owner | Why |
|---|---|---|
| The child's partial file *name* as an yt-dlp interface; the ffmpeg argfile's role in keeping the URL off the command line | phase 05 (TRN-001, independently **confirmed** in this run) | The claim is about the subprocess boundary. Its residue half is ART-008. |
| The `count > 0` guards that let a residue pass in silence; `failed_to_refresh_token` as a mislabel; the generic "An error occurred during download" | phase 08 | What the process emits, not what it leaves on disk. |
| `sanitize_title`'s docstring claim; the `FileNotFoundError` rationale at `ffmpeg_utils.py:474-478`, which is wrong (`FileNotFoundError` **is** an `OSError` subclass, so the stated reason for raising it does not hold) | phase 09 | Docstrings and comments. The *consequence* — the precise missing-segment error being swallowed and relabelled by `ytdlp_downloader.py:547` — is a diagnostics defect and is phase 08's. |
| Cookie-file material: mode, path shape, enumeration, retention | phase 06 (SEC-001..004) | Measured here for inventory completeness and filed nowhere. |
| Whether the suite's four skipped mode oracles should be skipped | phase 10 | Test guard shape. The absence of an executable oracle **is** filed, as ART-007, because the phase's binding rule makes it a fact about the guarantee. |
| Whether a residue class is gitignored | phase 11 | Coverage adequacy of the ignore file. The per-class verdicts are given above so that phase can use them. |
| Whether the second artefact of a colliding pair is corrupt | phase 03 | Transfer integrity. ART-006 claims only that the first write is destroyed silently. |
| NET-001: the order in which `_merge_batch_segments` destroys its inputs and the `finally` destroys the batch temps | phase 03 | Re-filed in no form. Cross-referenced in ART-004, ART-012 and ART-013. |
| CFG-002 (`model_copy` bypassing `ge=1/le=10`) | phase 02 | **Fixed** by `ea44b3d`: `model_copy` has zero occurrences in `src/`, and the commit message names CFG-002 as closed. Not re-filed. |



