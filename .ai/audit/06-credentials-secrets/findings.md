# Phase 06 Audit Findings — Credentials and Secrets

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/06-audit-credentials-secrets.md`
**Status:** complete
**Validated:** no

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

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
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

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
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

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
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

| Field | Value |
|-------|-------|
| **ID** | SEC-007 |
| **Severity** | MEDIUM |
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

## Summary

Ten findings, in the order the phase's §6 blocks are written: the on-disk
artefact (SEC-001, SEC-002, SEC-003), the channels (SEC-004), the sinks
(SEC-005, SEC-006, SEC-007, SEC-008), the written file (SEC-009), the harvest
(SEC-010). Eight are mandatory, two are advisory. Four are HIGH, five MEDIUM, one
LOW.

The single most consequential result is SEC-009: it is the one finding here that
is not about exposure at all but about the product failing to deliver a
credential it went to considerable trouble to obtain — a single character at
`cookies.py:78`, verified against the installed consumer rather than argued
from the format. SEC-001 through SEC-004 are a coherent chain on one artefact:
its requested mode is not the mode in force, it is not confined by anything else
in the tree, it survives forcible termination, and its path is in a process
argument vector. SEC-005 through SEC-007 are one class with three faces — the
product transforms a value on one surface and not on another, whether the
surface is a terminal, a path-shaped string the transform cannot match, or a
third party's exception message.










