# Phase 05 — Subprocess and browser boundary: findings

Scope of this phase: the lifecycle of every process the application causes
(the yt-dlp child, the ffmpeg muxer, the Playwright driver and browser), the
argument vector and named temporary resources each is handed, the discovery
probe, the reader/reaper/verdict structure, and the acquire side of the browser
manager.

Problems only: findings that survive a test of whether they change the result.
Clean surfaces are listed in §Skips and §Checked-and-clean, not filed.

| ID | Severity | Title |
| --- | --- | --- |
| TRN-001 | HIGH | The muxer transport's response file is never opened: the tool no longer supports the convention the whole concealment design rests on |
| TRN-002 | HIGH | The response file is destroyed before the child opens it, and a failed destroy skips the guarantee that the child is signalled |
| TRN-003 | HIGH | No process boundary around any invocation: a process the child creates for itself outlives the command on every exit path |
| TRN-004 | HIGH | A reader failure becomes the verdict, and the reaper can then never return |
| TRN-005 | HIGH | The muxer's reader stops at its own end-of-stream marker; the unbounded re-wait behind it never returns |
| TRN-006 | HIGH | A non-numeric value on the muxer's progress stream kills the reader and the exception is swallowed |
| TRN-007 | MEDIUM | The re-wait after output consumption carries no bound of its own |
| TRN-008 | MEDIUM | The discovery probe's answer is discarded; a missing dependency changes no branch and surfaces three different ways |
| TRN-009 | MEDIUM | The redaction applied to child output cannot match a filesystem path, and the terminal echo applies none at all |
| TRN-010 | MEDIUM | The two transports carry different vectors, and only one has any concealment mechanism |
| TRN-011 | MEDIUM | Child output is accumulated without a bound: 50 MiB of it cost the parent 106.6 MiB of peak working set |
| TRN-012 | MEDIUM | The termination ladder reports "not clean" for a process that is already gone |
| TRN-013 | LOW | One batch bound is a literal where configured values sit beside it |
| BRW-001 | HIGH | The launch failure's cause is discarded, and the failure-handling statement itself raises before the application error exists |
| BRW-002 | MEDIUM | The context created on every acquire is bound to no release |
| BRW-003 | MEDIUM | The injected asset's absence is silent at every log level |

---

## TRN-001 — HIGH — The response file is never opened: the convention the design rests on is gone

**Type** `[SPEC-DEVIATION]`
**Subject** the muxer transport's argument vector, `src/vkdownloader/services/downloader.py:92-124`
(`_temp_argfile`), `:302-309` (the invocation), `:96-99` (the stated purpose of
the convention), `:96-99` and `pyproject.toml:39-40` (the asset is packaged).

**What was observed.** The application writes every muxer argument into a
temporary file and invokes `ffmpeg @<path>`. The purpose, stated in the code's
own docstring, is that "sensitive values (signed CDN URLs, cookie file paths)
never appear in the process command-line arguments". The muxer this application
discovers on `PATH` does not expand `@file` at all: it takes the token as a
literal output filename.

`C:\ffmpeg\ffmpeg.exe`, `ffmpeg -version` → `ffmpeg version N-117624-g9eb7e8d2a4-20241023`
(an ffmpeg 7.x-lineage build; ffmpeg 7.0 replaced the whole-argument `@file`
form with `-/opt <path>`, which loads option *values* from a file and is not a
substitute here). `ffmpeg -h full` contains no `@file` entry.

Twenty-five real invocations of `HLSDownloader.download_with_ffmpeg`, each with
its own freshly written response file, produced this child output, verbatim,
25 times out of 25:

```
[out#0 @ ...] Unable to choose an output format for '@C:\Users\NMATVE~1\AppData\Local\Temp\vk_ffmpeg_i_r7iyso.args'; use a standard extension for the filename or specify the format manually.
Error opening output file @C:\Users\NMATVE~1\AppData\Local\Temp\vk_ffmpeg_i_r7iyso.args.
Error opening output files: Invalid argument
```

Three control invocations calibrate the wording: with a hand-written response
file **present** and with the same path **absent**, the real muxer behaves
identically and does not read the file in either case. Distribution over the
twenty-five runs: `{"not-expanded": 25}`.

**Failure scenario.** `vkdownloader download <url> --method ffmpeg`. The muxer
exits non-zero in about 30 ms without ever opening the response file, so the
input URL is never fetched. `download_with_ffmpeg` logs `ffmpeg_download_failed`
and returns `None`; `perform_download` (`downloader.py:550-568`) then logs one
INFO record, `ffmpeg_failed_fallback_to_segment_download`, and silently switches
to the segment downloader. The operator's selected transport never runs, and the
only evidence is a single INFO line.

**Consequence beyond the failure.** The concealment mechanism the code justifies
does not exist on this tool, so two things are true at once: the transport does
not work, *and* the rationale recorded at `downloader.py:96-99` for the
response-file design is not achieved by the mechanism it names.

---

## TRN-002 — HIGH — The response file is destroyed before the child opens it, and a failed destroy skips the child-signalling guarantee

**Type** `[BEST-PRACTICE]` (maintainability of a correct pattern) —
`[SPEC-DEVIATION]` on the guarantee at `downloader.py:400-409`
**Subject** `downloader.py:302-309` (spawn inside the `async with` block),
`:124` (the destroy step in the context manager's exit),
`:311` / `:400-409` (the `try`/`finally` that guarantees `cancel_subprocess`).

**What was observed — the ordering.** The child is spawned *inside*
`async with _temp_argfile(...)`, and the `async with` block is left on the very
next statement (`downloader.py:302-309`). Leaving the block runs
`Path(path).unlink(missing_ok=True)` at `downloader.py:124`. The
`try`/`finally` that guarantees the child is terminated
(`downloader.py:400-409`) is not entered until `downloader.py:311`. Between the
`create_subprocess_exec` call returning and the child opening the file, the
parent therefore destroys the file, and a failure to destroy it escapes *above*
the guarantee that would have signalled the child.

This ordering could not be observed end to end on this platform, because the
muxer never reaches the open (TRN-001). It is stated as structure, with the
distribution recorded as distribution: 25 of 25 runs the child never opened the
file, for the independent reason above. Structural facts are reported as
structural; the run count is not offered as evidence of the ordering.

**What was observed — the failed destroy.** The product's own destroy step was
driven against a path whose removal fails, with no replacement of any product
code: a watcher process opened each `vk_ffmpeg_*.args` file as soon as it
appeared and held the handle (on Windows an open handle without
`FILE_SHARE_DELETE` makes `DeleteFileW` fail). Result:

```
destroy_step_exception: PermissionError: [WinError 32] The process cannot access the file
                         because it is being used by another process:
                         'C:\\Users\\NMATVE~1\\AppData\\Local\\Temp\\vk_ffmpeg_30j44y7u.args'
child_pid: 24208
child_alive_after_escape: true
survivors: [24208]
parent_returned: None
```

The exception escapes `_temp_argfile`'s exit, so `download_with_ffmpeg` never
reaches `downloader.py:311`; the `finally` at `:400-409` is skipped; no
`cancel_subprocess` is ever called; and the spawned child is still running when
the call returns. This is the only row of the suite with a live child, and it
produced a survivor.

**Failure scenario.** On any machine whose muxer does expand `@file`: if the
deletion wins the race, the child sees a missing response file and reports
"no such file"; if the child has the file open when the parent deletes, the
parent's `unlink` raises, the failure replaces the in-flight download, and the
muxer is left running with no one to reap it.

---

## TRN-003 — HIGH — No process boundary around any invocation; a process the child creates for itself outlives the command

**Type** `[BEST-PRACTICE]`
**Subject** every spawn site: `ytdlp_downloader.py:631-635`,
`downloader.py:305-309`, `ffmpeg_utils.py:297`, `ffmpeg_utils.py:344`,
`browser.py:38` (the Playwright driver), `browser.py:40-43` (the browser).

**What was observed.** An AST survey of the whole source tree finds five
process-creating call sites and no boundary around any of them. Searching the
whole tree for `start_new_session`, `setsid`, `process_group`,
`CREATE_NEW_PROCESS_GROUP`, `CREATE_BREAKAWAY_FROM_JOB`, `creationflags`,
`startupinfo`, `JobObject`, `AssignProcessToJobObject` and `taskkill` returns
**no hit in any file**. The only thing addressed by the termination ladder is
the direct child's own pid (`ffmpeg_utils.py:198-207`).

A stub child that records its own pid, starts a process of its own choosing,
records that pid too, and sleeps was driven once per exit path through
`_download_with_ytdlp`. After the parent's method returned, every recorded pid
was probed against the process table:

| Exit path | Direct child | Grandchild alive after return |
| --- | --- | --- |
| success (exit 0) | reaped | **yes** |
| non-zero exit (3) | reaped | **yes** |
| cancellation (stop set, child killed) | killed | **yes** |

Survivor count: 1 per path, in every run. On the cancellation path the direct
child was signalled and the process it had started for itself was not — the
ladder addresses one pid of the two the run created, and no boundary exists that
could reach the other.

The Playwright driver was observed from the operating system while the real
driver was started: a direct child of the application process,
`node.exe C:\py_exp\mko_vkideo\.venv\Lib\site-packages\playwright\driver\node.exe
...playwright\driver\package\cli.js run-driver` (pid 3904, parent = the
application). It is inside no boundary, and only
`playwright.stop()` (`browser.py:87`) ever addresses it.

**Failure scenario.** `Ctrl+C` during a download, or a stop set by the batch
coordinator. `cancel_subprocess` terminates the yt-dlp child; the muxer that
yt-dlp started to merge the streams keeps running, holding the output file
open. Nothing in the application can address it: the ladder knows one pid, and
there is no process group, session or job object to search. The batch
coordinator's concurrency accounting is meanwhile free to start the next video.

**Why not CRITICAL.** The CRITICAL condition — an external process outliving
the command *holding a credential* — was evaluated against the observed route
and is not met: the process that holds the credential material is the direct
child (yt-dlp is the one given `--cookies`), and that one is killed. The
surviving descendant is recorded and addressed by nobody. HIGH is the composed
severity.

---

## TRN-004 — HIGH — A reader failure becomes the verdict, and the reaper can then never return

**Type** `[BEST-PRACTICE]`
**Subject** `ffmpeg_utils.py:29-63` (`iter_process_lines`; `readline()` at
`:60`, no `limit=` anywhere — the token does not appear in any spawn call in the
tree), `ytdlp_downloader.py:671-682`, `downloader.py:328-371`.

**What was observed.** The reader's size bound is the `asyncio.StreamReader`
default, read off the object the product reads: **65 536 bytes**, never set by
the application. A child that writes one line of 1 MiB and then stops:

```
parent_outcome: DID-NOT-RETURN-WITHIN-WALL-CLOCK      (15 s wall clock, 20.0 s elapsed)
parent_log_has_verdict: false                          (only "starting_ytdlp_download")
reader_declared_bound_bytes: 65536
reader_lines_yielded: 0
reader_error: ValueError: Separator is not found, and chunk exceed the limit
```

The child's own bytes were not consumed, no progress was reported, and **no
verdict of any kind was produced** — not a failure, not a cancellation, not a
completion.

**Failure scenario.** The reader raises, so `output_chunks` stops growing, so
the child eventually blocks writing to a pipe nobody drains, so `process.wait()`
— which on this platform is not signalled until the output pipe reaches end of
stream (measured: 0.038 s with nothing holding the pipe, 5.1 s when a process
the child left behind holds it) — never returns. The unbounded
`await process.wait()` at `ytdlp_downloader.py:681-682` therefore never
returns either. The call hangs indefinitely and the caller cannot tell a slow
download from a wedged one. The same shape exists on the muxer side at
`downloader.py:370-371`.

---

## TRN-005 — HIGH — The muxer's reader stops at its own end-of-stream marker; the re-wait behind it never returns

**Type** `[BEST-PRACTICE]`
**Subject** `ffmpeg_utils.py:174-175` (`break` on `progress=end`),
`downloader.py:354-371` (the re-wait the code's own comment anticipates),
`ytdlp_downloader.py:86-108` (the helper that cancels the wait task).

**What was observed.** `read_progress` yields one object and then **breaks out
of its loop** when it sees `progress=end`, so the reader task completes while
the child is still running; `_await_first_and_cancel_others` cancels the wait
task; and the code then performs a second, unbounded `await process.wait()`.
A real child process writing that stream, through the product's own reader and
its own completion helper:

```
completion_helper_returned_after_s: 0.033
child_still_running_when_helper_returned: true
unbounded_rewait_outcome: DID-NOT-RETURN-WITHIN-15s
```

With ordinary post-marker output — the marker, then 32 MiB:

```
bytes_collected_before_the_marker: 60
completion_helper_returned_after_s: 0.033
unbounded_rewait_outcome: DID-NOT-RETURN-WITHIN-10s
child_still_alive_at_the_end: true
```

The child blocks on a full pipe that the product has stopped draining, and the
re-wait has no bound to release it.

**Failure scenario.** Any muxer message after its last progress block — an
error, a warning, a trailer — larger than a pipe buffer deadlocks the download.
The caller is never told; `download_with_ffmpeg` never returns.

**The same reader also truncates deterministically.** The child wrote 4 109
bytes of tail plus a further `frame=2` line after the marker; the product's own
`stderr_collector` received **60 bytes**, ending exactly at `progress=end`
(`bytes_collected: 60`, `tail_present_in_collected_buffer: false`,
`lines_after_the_marker_present: false`). The point at which the parent stops
reading is fixed by the stream, so the truncation is certain rather than racy:
`ffmpeg_download_failed` (`downloader.py:388-395`) reports a prefix of what the
muxer actually said. Recorded here as part of the same defect — the reader's
end condition is the wrong one.

---

## TRN-006 — HIGH — A non-numeric value on the muxer's progress stream kills the reader, and the exception is swallowed

**Type** `[BEST-PRACTICE]`
**Subject** `ffmpeg_utils.py:111-119` (`_PROGRESS_KEY_HANDLERS`: `int(v)` /
`float(v)`), `ffmpeg_utils.py:160-177` (the loop that calls them),
`ytdlp_downloader.py:86-108` (`_await_first_and_cancel_others`).

**What was observed.** One progress line, `frame=abc`, from a real child
process into the product's own reader:

```
muxer_reader_state_after_2s: done
muxer_reader_error: ValueError: invalid literal for int() with base 10: 'abc'
muxer_reader_yielded: []
muxer_child_still_alive: true
child_rewait_outcome: DID-NOT-RETURN-WITHIN-5s
```

The reader task dies. `_await_first_and_cancel_others` returns the failed task
in `done` and re-raises nothing; no caller inspects it, so the failure produces
no log record and no exception. The result is the same wedged state as TRN-005,
reached from a different cause.

For contrast, the downloader's progress parser on the same surface is
regex-guarded and returns `None` for both a non-numeric percentage and the
protocol's own `N/A` placeholder:

```
ytdlp_non_numeric_pct: null        ("[download]  abc% of 10.00MiB at 1.00MiB/s ETA 00:09")
ytdlp_placeholder_size: null       ("[download]   1.0% of N/A at 1.00MiB/s ETA 00:09")
```

**Failure scenario.** The muxer emits one `key=value` line whose value is not a
bare number — the value kinds the protocol itself permits, and anything a
future or alternate build adds. The reader dies silently, the child is never
drained, and `download_with_ffmpeg` never returns.

---

## TRN-007 — MEDIUM — The re-wait after output consumption carries no bound of its own

**Type** `[BEST-PRACTICE]`
**Subject** `ytdlp_downloader.py:681-682`, `downloader.py:370-371`; contrast
`ffmpeg_utils.py:238`.

**What was observed.** A child that emits its output and then never exits:

```
parent_outcome: DID-NOT-RETURN-WITHIN-15s
child_alive_after: [<pid>]      (killed by the harness afterwards)
parent_log: only "starting_ytdlp_download" and one debug progress record
```

The same operation for the merge transport is bounded: `ffmpeg_utils.py:238`
wraps `process.communicate()` in `asyncio.wait_for(..., timeout=timeout)` with
`download_timeout`. The download paths carry no equivalent. Each call is
individually unbounded; the observed wall clock is 15 s against a wait designed
to have no limit.

**Failure scenario.** Any child that produces output and does not exit — a
stalled connection held open by a server, a merged process waiting on a lock —
holds the download open for as long as it likes, and nothing in the call can
end it. This row is the structure that turns TRN-004, TRN-005 and TRN-006 from
"slow" into "permanent": once the reader has stopped, the only thing that could
release the child is this wait, and it has no bound.

**Not re-filed from NET-007.** NET-007 records the deliberate absence of a
whole-operation download budget (`ytdlp_downloader.py:580-582`). This finding is
the narrower case: the wait that follows output consumption, with the child
already finished, carries no bound of its own.

---

## TRN-008 — MEDIUM — The discovery probe's answer is discarded; a missing dependency changes no branch and surfaces three different ways

**Type** `[BEST-PRACTICE]`
**Subject** `ffmpeg_utils.py:66-89` (the probe and its cache), `downloader.py:466-468`
(the only caller; the return value is discarded), `ytdlp_downloader.py:547-551`
(the resume path's `except (ExtractionError, OSError)`), documented in the
merge docstring at `ffmpeg_utils.py:474-478`.

**Probe's answer, and whether it re-probes.** One fresh process, a binary ahead
on the search path, then the machine changed under it:

```
{"first": true, "second": true, "machine_changed": true,
 "which_after_change": null, "third": true, "muxer_dirs_removed": ["C:\\ffmpeg"]}
```

Two calls both answer from the real lookup path; the third still answers `True`
after the only muxer on the machine was removed from `PATH` and
`shutil.which("ffmpeg")` returns `null`. A fresh process whose `PATH` holds no
muxer answers `{"which": null, "probe": false}` with one `ffmpeg_not_found`
warning. The answer is cached for the process and never re-derived.

**Whether the caller's branch changes.** With the probe forced to return
`False`, the muxer path runs identically and still spawns:

```
{"probe_returned": false, "outcome": "returned None"}
```

`downloader.py:468` calls the probe and throws the answer away. There is one
caller in the tree; no branch anywhere depends on the value.

**What the absence actually does, captured verbatim.** The probe's answer was
asserted `False` **before** each run, never after.

* Muxer transport, no muxer on the search path — the process exit status and
  the tail of the traceback:
  `process_exit_status: 1`, ending
  `FileNotFoundError: [WinError 2] The system cannot find the file specified`
  raised from `downloader.py:305`.
* Merge transport, same conditions — `ESCAPED=FileNotFoundError: [WinError 2]
  The system cannot find the file specified`, `process_exit_status: 1`.
* Downloader transport, module not importable — the child exits 1 and the
  parent records it and returns `None`:
  `download_failed ... error="ModuleNotFoundError: No module named 'yt_dlp'"`.

One absence, three surfacings: a raw traceback with exit 1, the same raw
traceback, and a structured failure record. At the CLI a traceback is caught by
`cli.py:221-224` and reduced to "An error occurred during download". Worse, on
the resume path the merge's `FileNotFoundError` is an `OSError` and is caught by
`except (ExtractionError, OSError)` at `ytdlp_downloader.py:547-551` — the
swallow the merge docstring at `ffmpeg_utils.py:474-478` describes in its own
words ("which would swallow a FileNotFoundError here, relabel it
`failed_to_refresh_token` and return None, losing the message") — so the
missing muxer is reported to the user as `failed_to_refresh_token`.

**Failure scenario.** ffmpeg is not installed. Every download that needs it
either fails with an opaque traceback or is reported as a token problem. The
only actionable text anywhere is the one `ffmpeg_not_found` warning the probe
emits — and per ENT-001 that warning is frequently written to the console
instead of the log file the operator is asked to read. A machine that loses
ffmpeg mid-session keeps the cached `True` and produces none of it.

---

## TRN-009 — MEDIUM — The redaction cannot match a filesystem path, and the terminal echo applies none

**Type** `[SPEC-DEVIATION]`
**Subject** `url_sanitizer.py:13-24`; the sites `ytdlp_downloader.py:691-695`
and `downloader.py:385-390` (both comment that the transform redacts "signed CDN
URLs **or cookie file paths**"), `ytdlp_downloader.py:198-228` (the echo path,
no transform), `ffmpeg_utils.py:311` and `ffmpeg_utils.py:363` (no transform).

**The transform, against a declared corpus.**

| Input | Changed | Result |
| --- | --- | --- |
| absolute URL with a token | yes | `https://cdn.vkvideo.ru/***REDACTED***` |
| filesystem path | **no** | `C:\Users\operator\AppData\Local\Temp\vk_cookies_ab12cd34.cookies.txt` unchanged |
| argument fragment `--cookies <path>` | **no** | unchanged |
| plain text | no | unchanged |
| argument fragment containing a URL | yes (URL part only) | `…Referer: https://cdn.vkvideo.ru/***REDACTED***` |
| error text with a URL in brackets | yes (URL part only) | `[download]  Failed: https://cdn.vkvideo.ru/***REDACTED***` |

The transform is a single regex over `https?://…` (`url_sanitizer.py:8`).
It cannot match a filesystem path, and both call sites' comments say it does.
On the muxer path the real child output proves the gap end to end: the temp
response-file path `C:\Users\NMATVE~1\AppData\Local\Temp\vk_ffmpeg_i_r7iyso.args`
reaches `ffmpeg_download_failed` verbatim, through the transforming site.

**The same bytes on two surfaces.** One stub child, driven end to end through
`_download_with_ytdlp` with the echo path on and a cookie file present:

*Terminal* (`_echo_ytdlp_line` → `sys.stderr`, no transform):
```
STUB-ARGV … --cookies C:\Users\NMATVE~1\AppData\Local\Temp\vk_cookies_undexud6.cookies.txt https://vkvideo.ru/video-1_2?sign=SYNTHETICTOKEN123&exp=9999999999
```

*Log record* (`download_failed`, `sanitize_text_for_log`):
```
error='STUB-ARGV … --cookies C:\\Users\\NMATVE~1\\AppData\\Local\\Temp\\vk_cookies_undexud6.cookies.txt https://vkvideo.ru/***REDACTED*** …'
```

The URLs are redacted in the log; the cookie file path survives in both. The
terminal write is a second surface for the same bytes with a different rule
applied to it.

**Every site where child output becomes a log record, a terminal write or a
stored buffer:**

| Site | Transform |
| --- | --- |
| `ytdlp_downloader.py:227` (terminal, echo on) | none |
| `ytdlp_downloader.py:224` (terminal, progress rewrite) | none |
| `ytdlp_downloader.py:694-696` (log record) | `sanitize_text_for_log` |
| `downloader.py:388-390` (log record) | `sanitize_text_for_log` |
| `ffmpeg_utils.py:311` (`batch_merge_failed`) | none (`error[:200]`) |
| `ffmpeg_utils.py:363` (`final_merge_failed`) | none (`stderr.decode()[:200]`) |
| `ytdlp_downloader.py:655`, `:669`; `ffmpeg_utils.py:164`; `downloader.py:352` (stored buffers) | none; consumed by the sites above |

**Failure scenario.** yt-dlp echoes its own invocation, or the muxer echoes the
path it was handed. The signed URLs are stripped on the log path and not on the
terminal path; the cookie file path is stripped on neither, despite the two
comments saying so. Whether a path is a secret is phase 06's judgement; the
mechanism — a transform that cannot match the shape this site carries, applied
at some sinks and not at others — is this phase's.

**Cross-reference, not re-filed.** Phase 06's validator recorded that SEC-005's
surface table omits `ffmpeg_utils.py:310-311` and `:363` — the two sites listed
two rows above this note, which put raw child stderr in the log with no
transform. This phase reached them
independently, from the muxer transport's own evidence, and adds them to the
table rather than restating SEC-005: the exposure judgement and the ownership of
the transform's corpus stay with 06; the enumeration and the transform's
mechanism stay here. SEC-001's permission and lifetime findings for the cookie
artefact are likewise not restated — only the fact that its path reaches the
log unredacted, which is this note's subject.

---

## TRN-010 — MEDIUM — The two transports carry different vectors, and only one has any concealment mechanism

**Type** `[BEST-PRACTICE]`
**Subject** `ytdlp_downloader.py:260-299` + `:301-317` + `:623` (the downloader
vector), `downloader.py:92-124` + `:302-309` (the muxer vector), the spawn
calls at `ytdlp_downloader.py:631-635`, `downloader.py:305-309`,
`ffmpeg_utils.py:297`, `ffmpeg_utils.py:344`.

**Both vectors, read off the objects that produce them.** The builder called
directly with a synthetic media URL and a synthetic credential path:

```
[python.exe, -u, -m, yt_dlp, --encoding, utf-8, -o, <out>, -f, best[height<=720],
 --newline, --hls-prefer-native, --no-warnings, --socket-timeout, 300, -R, 3,
 --fragment-retries, 3, -N, 4, --throttled-rate, 100000, --user-agent, <ua>,
 --referer, https://vkvideo.ru/, --cookies, C:\...\vk_cookies_f1qhfhyn.cookies.txt,
 https://vkvideo.ru/video-1_2?sign=SYNTHETICTOKEN123&exp=9999999999]
```

`media_url_is_in_vector: true`, `cookie_file_path_is_in_vector: true`. The URL
is appended by the caller at `ytdlp_downloader.py:623`, not by the builder.

The muxer vector, captured while the child received it: `["ffmpeg", "@<argfile>"]`
— neither form appears. The response file's real contents, snapshotted while
the file existed:

```
-y
-progress
pipe:2
-nostats
-headers 'User-Agent: …\n\nReferer: https://vkvideo.ru/\n\n'
-i 'https://vkvideo.ru/video-1_2?sign=SYNTHETICTOKEN123&exp=9999999999&cookies=file:C:\Users\NMATVE~1\AppData\Local\Temp\vk_cookies_cl_r82ea.cookies.txt'
-c
copy '<output>'
```

`media_url_in_response_file: true`, `credential_path_in_response_file: false`
for the standalone call; with a cookie file the credential path is inside the
file too. So one transport conceals and the other does not — the two halves of
the same decision, applied to one transport only.

A second structural observation from the same snapshot: the multi-line
`-headers` value is written as one argument, but the response file is
line-oriented, so the value would be split across three lines by any reader of
that format. Moot while TRN-001 stands; recorded because it survives the fix.

**The child's inheritance.** The child was asked what it received and diffed
against the parent, key by key:

```
parent_key_count: 115, child_key_count: 116
keys_only_in_child: ["VKD_PROBE_MARKER"]      (set by the harness as a marker)
keys_only_in_parent: []
keys_with_different_values: []
inherited_probe_marker: "set-by-parent"
child_cwd == parent_cwd
```

The full environment is inherited unchanged and the working directory is
inherited; no spawn call in the tree passes `env=` or `cwd=`. Nothing narrows
what the child can see.

**Failure scenario.** On a shared or locked-down host, every value the
application holds for the child — proxy configuration, tokens in the
environment, the working directory's meaning — is handed over wholesale, while
the mechanism the code relies on to hide the download arguments exists on only
one of the two transports.

**Cross-reference, not re-filed.** SEC-001 (phase 06) reaches the same
asymmetry from the credential side: the cookie-file path is argv element 28 of
30 on the downloader transport while its ffmpeg sibling uses a response file.
That finding owns the artefact's permissions and lifetime; this one owns only
the divergence between the two vectors, and its fix is the same shape — give
the downloader transport the mechanism the muxer transport claims to have. Note
that SEC-001's asymmetry argument weakens once TRN-001 is fixed, because the
concealment the muxer transport claims turns out not to work: whichever
transport is changed, the other has to follow.

---

## TRN-011 — MEDIUM — Child output is accumulated without a bound

**Type** `[BEST-PRACTICE]`
**Subject** `ytdlp_downloader.py:637` (`output_chunks: list[bytes]`), `:655`,
`:669`, `:684` (`b"".join(output_chunks)`).

**What was observed.** A child writing 50 MiB on one stream, with `echo=False`
so that nothing is displayed at all:

```
child_bytes_written: 52428800
peak_working_set_before_bytes: 60948480
peak_working_set_after_bytes:  172707840
peak_growth_bytes:           111759360        (106.6 MiB for 50 MiB of child output)
outcome: returned <output path>
```

The bound is the child's own output size, and the amplification is the
list-of-chunks plus the join, measured at roughly 2×. Nothing in the call
bounds it; the list grows for the whole life of the download, and on failure
the joined buffer is decoded and then transformed, adding two more copies.

**Failure scenario.** A chatty child (verbose errors, a long warning block) in a
batch run multiplies the peak by the concurrency: `max_concurrent_downloads`
defaults to 4 and is accepted up to 16, so 16 concurrent downloads of a
50 MiB-output child cost the process on the order of 1.7 GiB of working set
for output nobody asked to see — the echo path discarded every one of those
lines.

---

## TRN-012 — MEDIUM — The termination ladder reports "not clean" for a process that is already gone

**Type** `[BEST-PRACTICE]`
**Subject** `ffmpeg_utils.py:179-207` (`cancel_subprocess`); the call sites
that treat `False` as "still running": `ytdlp_downloader.py:640-645`,
`ytdlp_downloader.py:717-723`, `downloader.py:320-326`, `downloader.py:341-347`,
`downloader.py:375-381`, `downloader.py:403-409`.

**What was observed.** The ladder driven through each branch with a real
handle, then twice more against the same handle, then against a dead one:

| Case | Return | Raised |
| --- | --- | --- |
| 1st call, child alive then exits | `True` | — |
| 2nd call, same handle, already exited | **`False`** | — |
| 3rd call, same handle, already exited | `False` | — |
| call against a long-lived child (`timeout=1.0`) | `True` | — |

`False` is returned by the `except ProcessLookupError` arm at
`ffmpeg_utils.py:206-207`, which fires precisely when the handle has already
been reaped — that is, when the process is **already gone and the outcome is
clean**. Every call site in the tree reads `False` as "not clean" and logs
`*_cancel_not_clean` with the pid. A process that was never started cannot be
constructed through the public API; that row is recorded as a gap.

**Where the composition actually happens.** `downloader.py:375-381` calls
`cancel_subprocess` unconditionally in the stop branch, after
`_on_shutdown` (`downloader.py:320-326`) has already cancelled the same handle
through the reader. The second call returns `False` and the warning is logged
for a process that the first call already terminated.

**Verification status: partial.** The second-call return value and the two call
sites were both established, but the composition could not be driven end to end
on this platform: the real muxer exits in about 30 ms (TRN-001), so the stop
branch is not reached with a live child. Recorded as structure with the measured
component, not as an observed log line.

---

## TRN-013 — LOW — One batch bound is a literal where configured values sit beside it

**Type** `[BEST-PRACTICE]`
**Subject** `ffmpeg_utils.py:480` (`batch_size = 100`), against
`ffmpeg_utils.py:452` (`download_timeout: float = 300.0`),
`config.py` (`download_timeout`, `max_concurrent_downloads`, `max_retries`).

**What was observed.** The quantity that decides how much the muxer is asked to
do in one call is read off the object, not assumed:

```
batch_size_literal: 100
signature: (segments_dir, output_file, count, download_timeout: float = 300.0) -> Path | None
configured_bounds_beside_it: {"download_timeout": 300, "max_concurrent_downloads": 4, "max_retries": 3}
```

The merge is issued in batches of 100 segments, and the number is not
configurable while the timeout, concurrency and retry counts beside it are.

**Failure scenario.** A user on a slow link or with a memory-constrained host
cannot raise the merge batch smaller, and an operator debugging a merge that
fails on a large set has one fewer knob than the two parameters next to it
imply.

---

## BRW-001 — HIGH — The launch failure's cause is discarded, and the failure-handling statement itself raises

**Type** `[SPEC-DEVIATION]`
**Subject** `browser.py:44-47` (`except Exception: logger.error(...); ...;
raise ExtractionError(...) from None`).

**What the failing launch says.** The real launch was performed and its message
captured verbatim:

```
BrowserType.launch: Executable doesn't exist at
  C:\Users\NMatveichev\AppData\Local\ms-playwright\chromium_headless_shell-1228\chrome-headless-shell-win64\chrome-headless-shell.exe
╔══════════════════════════════════════╗
║ Looks like Playwright was just installed or updated.  ║
║ Please run the following command to download new browsers: ║
║     playwright install   ║
╚══════════════════════════════════════╝
```

**What the application surfaced, driving the product's own `__aenter__`:**

```
surfaced_to_caller: "UnicodeEncodeError: 'charmap' codec can't encode characters
                     in position 55-76: character maps to <undefined>"
```

The caller receives neither the missing executable nor the remedy nor even the
application's own `ExtractionError`. Two mechanisms combine:

1. `raise ... from None` (`browser.py:47`) sets `__cause__` and
   `__context__` to `None` — the actionable Playwright message is discarded
   by design, and the `ExtractionError` text names neither the binary nor how
   to get it.
2. The `logger.error("browser_launch_failed", exc_info=True)` on the line
   before it (`browser.py:45`) itself raises, because the traceback it is asked
   to render contains box-drawing characters and the console stream is cp1251.
   The `ExtractionError` is therefore never constructed at all.

**Failure scenario.** A user installs the package, runs
`vkdownloader download <url> --cookie-source browser`, and gets an
`UnicodeEncodeError`. The one piece of information that would have fixed the
problem — "run `playwright install`" — exists only in the traceback that the
statement meant to log and then failed to write.

**Cross-reference, not re-filed.** The encoding defect itself is ENT-002
(phase 01): logging is not configured on this path, so the record goes to the
console and the configured log file is never created. What is new here, and
this phase's row, is that the browser launch-failure handler is one of the
places where it converts a diagnosable failure into an unrecognisable one, and
that the deliberate `from None` would have lost the cause even if the logging
had succeeded.

---

## BRW-002 — MEDIUM — The context created on every acquire is bound to no release

**Type** `[BEST-PRACTICE]`
**Subject** `browser.py:94-116` (`create_stealth_page`); the release path
`browser.py:53-92`.

**What was observed.** The acquire path driven with stand-in objects (the real
browser binaries are not installed on this machine — see §Skips):

```
contexts_created: 2                     (for 2 calls to create_stealth_page)
pages_created: 2
contexts_closed: [false, false]
manager_stores_context: false
manager_attribute_names: ["_launch_args", "_stealth_path", "browser", "playwright", "settings"]
pages_are_distinct: true
```

`browser.new_context(...)` is called on every acquire
(`browser.py:103-108`), the returned context is a local (`browser.py:103`),
and no step in the class binds it to anything: it is not stored on the manager,
not returned, and not closed. The only release in the class is
`self.browser.close()` (`browser.py:77`), which closes the browser and with it
every context it owns. `create_stealth_page` is called once per extraction, so
one context and one page accumulate per video for the life of the manager.

**Identity parameters passed to the context**, recorded rather than judged:
`viewport={"width": 1920, "height": 1080}`, `user_agent=<settings.user_agent>`,
`locale=<settings.locale>`, `timezone_id=<settings.timezone>`. All four derive
from `Settings`; none is fixed in code. The launch argument is a single token,
`--disable-blink-features=AutomationControlled` (`browser.py:42`), whose only
purpose is to suppress an automation signal — whether the browser honours it is
a property of the browser and is out of scope by design.

**Failure scenario.** A batch run of 200 videos holds 200 contexts and 200
pages alive inside one browser for the whole run, none of them visible to the
manager. Per-video teardown is not possible, because nothing in the acquire
path hands back what it created.

**Scope note.** The acquire side only. Whether release is reached at all on any
path is CON-004 (phase 04) and is not re-argued here.

---

## BRW-003 — MEDIUM — The injected asset's absence is silent at every log level

**Type** `[BEST-PRACTICE]`
**Subject** `browser.py:112-114` (`if self._stealth_path.exists(): await
page.add_init_script(...); logger.debug("stealth_script_applied")`).

**What was observed.** The asset exists in the repository
(`src/vkdownloader/stealth.min.js`, 2 608 bytes) and is declared as a wheel
artifact (`pyproject.toml:39-40`). The manager was then pointed at a location
that holds none — the state the branch is written for — and the acquire path
driven with stand-in objects, with logging at DEBUG into a file:

```
asset_path_used: "no-such-directory\\stealth.min.js"
page_returned: true
log_records_written_during_the_call:
  {"event": "creating_stealth_page", "level": "debug", "timestamp": "…"}
injection_happened: false
```

One record — the normal entry — and nothing about the missing asset at any
level. The call still returns a usable page. With the asset present, the same
drive produces `add_init_script("…\\stealth.min.js")` and the
`stealth_script_applied` record.

**Failure scenario.** The asset is absent in the environment the application
runs in — a wheel built without the data file, a partial deployment, a renamed
file. Extraction proceeds with the browser's ordinary fingerprint, is more
likely to be detected, and the only clue is an extraction failure some way
downstream with nothing connecting it to this branch. The log says a stealth
page was created; it does not say the script was not applied.

---

## Documented skips

| Row | Reason |
| --- | --- |
| Signal-handler registration path (`asyncio/unix_events.py` `add_signal_handler`) | On Windows `loop.add_signal_handler` raises `NotImplementedError`; the `signal.signal` fallback at `signal_handlers.py:40-54` is what runs. Unreachable, not a defect. The real defect there — nothing restores the handler — is CON-001 (phase 04). |
| The grace branch of the termination ladder (`except TimeoutError: process.kill()` at `ffmpeg_utils.py:202-205`) | The standard library maps the graceful request and the forceful one to the same unconditional termination call on this platform, so no child can be made to ignore the first request and the branch cannot be entered. `timeout=5.0` (`ffmpeg_utils.py:182`) is the only grace any child receives. |
| A real browser launch, a real context, a real init script | The Playwright browser binaries are not installed on this machine (`chromium_headless_shell-1228` missing, confirmed by the verbatim launch error in BRW-001). Stand-in objects were used for the acquire side, as the suite permits. |
| The Playwright driver's working directory and environment size | The installed Playwright version does not expose the driver's process object through the public or the private attributes the harness tried (`connection_type: null`, `transport_type: null`). The command line was read from the operating system instead, and is quoted in TRN-003. |
| R2's stub-based observation of the response file at the moment the child opens it | A stub cannot shadow the real muxer on this platform: CreateProcess resolves a bare name on `PATH` with the `.exe` extension only, so a `ffmpeg.CMD` stub is found by the discovery probe and ignored by the invocation (confirmed by a pre-flight run in which shutil.which returned the stub path while the child that executed was the real muxer). The real muxer was used as the observer instead — it is the actual consumer of the file, so what it reports is stronger evidence than a stub's word. The consequence for the row is stated in TRN-001. |

---

## R9 — baselines for this phase's surface

**Tree state measured.** `git status --short -- src tests pyproject.toml` is
empty; HEAD is `ea44b3d fix(config): make env and CLI sources both reachable and
drop the unvalidated settings copy`. This is the state *after* that commit
settled — during the phase it was still an uncommitted working-tree change, and
the `ruff format --check src` exit 1 that phase 03 and the phase-06 validator
observed no longer reproduces (`30 files already formatted`, EXIT=0). Every
number below was re-measured against this tree, and every `file:line` this
report cites was re-checked against it as well: 106 anchors, **106 exact, 0
drifted**. Two anchors moved during the phase and both are corrected in place —
`downloader.py:567` → `:568` (the end of the muxer fallback block) and the
resume path's swallowing clause, which is `ytdlp_downloader.py:547-551` (the
merge docstring at `ffmpeg_utils.py:474-478` only describes it).

Commands, run from the repository root, over
`src/vkdownloader/services/{ytdlp_downloader,ffmpeg_utils,downloader}.py`,
`src/vkdownloader/infrastructure/browser.py`,
`src/vkdownloader/utils/url_sanitizer.py`:

```
uv run pytest tests -q
  495 passed, 4 skipped in 25.63s
  EXIT=0

uv run ruff check <the five paths>
  All checks passed!
  EXIT=0

uv run ruff format --check <the five paths>
  5 files already formatted
  EXIT=0

uv run mypy <the five paths>
  Success: no issues found in 5 source files
  EXIT=0
```

The suite count is this phase's own (495), later than the 486 reported by phases
03 and 06.

Match counts in the test tree (excluding `.kilo/worktrees/`), per symbol:

| Symbol | Matches |
| --- | --- |
| `create_subprocess_exec` | 8 |
| `cancel_subprocess` / `cancel_ffmpeg_process` | 2 |
| `check_ffmpeg_available` | 3 |
| `BrowserManager` | 2 |
| `sanitize_text_for_log` | 7 |
| `_temp_argfile` | 2 |
| `iter_process_lines` | 2 |
| `_build_ytdlp_cli_command` | 3 |
| `_download_with_ytdlp` | 2 |
| `_await_first_and_cancel_others` | **0** |
| `_echo_ytdlp_line` | **0** |

The suite's own spawn stand-in reads the named response file synchronously
inside the patched `create_subprocess_exec` call
(`tests/test_hls_downloader.py:720-726` and `:783-788`). That is the state in
which TRN-002's ordering is invisible by construction: the file is read before
the call returns, and the destroy step has not run yet.

---

## Checked and found clean

Recorded so the next reader does not repeat the work. Each was driven, not read.

* **The escalation ladder's first call** returns `True` for a live child and for
  one that exits inside the grace, and the `ProcessLookupError` arm is the only
  source of `False` (TRN-012 records what that arm is mistaken for).
* **The downloader's progress parser** is regex-guarded: a non-numeric
  percentage, the `N/A` placeholder, and a non-`[download]` line all return
  `None` and produce no progress and no exception. The muxer's is not (TRN-006).
* **Every flag the child vector passes exists in the installed tool.**
  `--version` reports `2026.07.04`; each of the fifteen flags was passed alone
  (exit status 2, a usage message, for the ones that take a value) and then with
  a value, and each was accepted — none produced "No such option". The three
  absent from the short `--help` text (`--hls-prefer-native`, `--referer`,
  `--user-agent`) are accepted by the installed parser.
* **The two surfaces of the downloader agree on every shared knob.**
  `socket_timeout`, `retries`, `fragment_retries` and `throttled_rate` take the
  same `Settings` value on both; `nocheckcertificate` / `--no-check-certificates`
  and the concurrency and output-format options differ only where the two
  surfaces differ in purpose (enumeration versus download).
* **Format selectors**, read off the builder for every `QualityEnum` value:
  `240→best[height<=240]`, `360→…<=360`, `480→…<=480`, `720→…<=720`,
  `1080→…<=1080`, `1440→…<=1440`, `2160→…<=2160`, `best→best`,
  `worst→best`. The `worst` entry is NET-003 (phase 03) and is not re-filed here.
* **Declared version floors** — `yt-dlp>=2024.0.0` (`pyproject.toml:27`),
  `playwright>=1.45.0` (`pyproject.toml:20`) — are two and a half years and one
  major line below what is installed. The child names `sys.executable -m
  yt_dlp`, so the version in the active environment is what runs; no floor is
  enforced at runtime and none is checked in a test.
* **Termination escalation order** — `cancel_subprocess` addresses the direct
  child and nothing else; the grace values in use are 5 s
  (`ffmpeg_utils.py:182`) for a child, 300 s (`download_timeout`, default) for
  the merge operation (`ffmpeg_utils.py:238`), and 10 s
  (`_BROWSER_CLOSE_TIMEOUT`, `browser.py:16`) for both the browser close and the
  driver stop. Only the first is short relative to the work being bounded.
* **The cookie file's removal on every path** — `ytdlp_downloader.py:725-728`
  and `downloader.py:410-413` — is phase 06's row and is not filed here.
* **The child-wait path and the displaced SIGINT handler** are CON-001 (phase
  04) and are not re-filed; the reader results above are the *other* paths
  through the same machinery.

---

## Harness notes

All scratch code lived under `.temp/` (gitignored) and has been removed,
including the anchor-verification harness. Nothing in the repository was
modified; the injected asset was not moved or renamed — the manager was pointed
at a location holding none, which is the state the silent branch is written for.
Third-party origins were never contacted: the muxer was pointed at
`http://127.0.0.1:9` (connection refused) or at a local listener, and the
downloader was replaced by a stub module placed on the *child's* module search
path, leaving the parent's own import of the real package untouched. Captured
child and driver output was written to files, never printed to the console.
