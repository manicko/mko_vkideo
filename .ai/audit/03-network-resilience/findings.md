# Phase 03 Audit Findings — Network Resilience

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/03-audit-network-resilience.md`
**Status:** complete
**Validated:** no

---

## Findings

### NET-001: A successful batch merge destroys its own inputs, and the failure path destroys the only remaining copy — silently

| Field | Value |
|-------|-------|
| **ID** | NET-001 |
| **Severity** | CRITICAL |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** The only merge path in the process is `_merge_segments_batched`
(`ffmpeg_utils.py:451-515`): ⌈N/100⌉ batch stages, then one final stage. Each
batch stage **unlinks its own input segments immediately after it succeeds**
(`ffmpeg_utils.py:314-317`), before any later stage has run. If a later batch
stage or the final stage then fails, the `finally` at `ffmpeg_utils.py:511-515`
unlinks every batch temp file that *had* been produced. At that point both
copies of the already-merged bytes are gone. The residue reporter
`_log_preserve_segments` (`segment_downloader.py:930-939`) is guarded on
`segment_count > 0`, so in the case where the loss is total it emits nothing.

**Evidence:** Method **R3** — the process-launch boundary replaced by a local
stub that reads its argv and its concat list file byte-for-byte, writes the
concatenated bytes, and exits with a chosen status. No real binary, no socket.

Case A — 250 segments, all three batch stages succeed, final merge forced to fail:
```
  stub invocations:
    -y -f concat -safe 0 -i ...\batch_list_0.txt   -c copy ...\batch_00000.ts
    -y -f concat -safe 0 -i ...\batch_list_100.txt -c copy ...\batch_00100.ts
    -y -f concat -safe 0 -i ...\batch_list_200.txt -c copy ...\batch_00200.ts
    FINAL-MERGE -> out.mp4 (forced failure)
  _merge_segments_batched -> None
  inventory AT STAGE EXIT:            (empty)
  original segments surviving: 0 of 250
  final output present: False size=0
  residue report: <NOTHING EMITTED>
```
Case D (150 segments, two batch stages, final forced to fail) is identical:
`0 of 150` survive, nothing emitted.

Case B/C — a **middle** batch (index 100) fails:
```
  original segments surviving: 150 of 250
  gapped original indices: count=100  first=00000.ts last=00099.ts
  inventory AT STAGE EXIT:
    .out_segments/batch_00100.ts        15000     <- partial, half of the batch
    .out_segments/batch_list_100.txt    8000
  residue report: preserving_segments_for_resume count=151
```
`count=151` counts `*.ts` in the directory, which includes the **failed** batch
temp file — the report describes 151 resumable segments when 150 exist.

**Consequence:** A single failure of the last stage of a 250-segment download
destroys every byte the download had produced, and the process records nothing
whatsoever — no output file, no exception, no residue line.
`download_hls_with_resume` returns `None`, `perform_download` returns `None`,
and the operator is told the download failed with no indication that the whole
transfer must be repeated. In the middle-batch case the surviving set is gapped
(`00000.ts`–`00099.ts` missing) and the announced count does not describe the
set on disk.

**Recommendation:** Make the batch stage non-destructive until the whole merge
has succeeded — delete the input segments only in `_perform_final_merge`'s
success path (after `ffmpeg_utils.py:356-361`), not per batch at
`ffmpeg_utils.py:314-317`. Remove the `finally` unlink at `ffmpeg_utils.py:511-515`
or restrict it to a temp file that is provably not the last surviving copy, and
have `_log_preserve_segments` report unconditionally (count 0 included) so the
"nothing was kept" case is stated rather than inferred. Both changes are inside
this phase's carve-out (a stage destroying the bytes a later stage needs); the
retention/residue side of the leftover `batch_*.ts` and `batch_list_*.txt` files
belongs to `07`.

---

### NET-002: The manifest-fetch layer has no retry policy — a 429 or 5xx on the playlist abandons the transfer on the first response, and the status is never recorded

| Field | Value |
|-------|-------|
| **ID** | NET-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `_fetch_playlist_with_retry` (`segment_downloader.py:484-523`)
has a retry *loop* but no retry *policy*. It retries only a transport-level
failure (line 504-505, `continue` with no delay) and a 403/410 that a forced
re-extraction can answer. Every other status returns `None` on the first
response, at `segment_downloader.py:512-513`:
`if status not in (403, 410) or not extractor: return None`. No log line carries
the status: `_fetch_single_playlist` returns `("", status)` and the caller drops
it on the floor.

**Evidence:** Method **R1**, three matrices printed separately against the
scripted origin, `max_retries=3`. Matrix 1 (manifest fetch):

```
MATRIX 1 - MANIFEST FETCH LAYER (_fetch_playlist_with_retry), max_retries=3
  variant: extractor=None
  status  requests  delay-to-next   returned     pause.pause/waits
  200     1         []              playlist    pause=0 wait=0
  400     1         []              None         pause=0 wait=0
  401     1         []              None         pause=0 wait=0
  403     1         []              None         pause=0 wait=0
  404     1         []              None         pause=0 wait=0
  408     1         []              None         pause=0 wait=0
  410     1         []              None         pause=0 wait=0
  425     1         []              None         pause=0 wait=0
  429     1         []              None         pause=0 wait=0
  500     1         []              None         pause=0 wait=0
  501     1         []              None         pause=0 wait=0
  502     1         []              None         pause=0 wait=0
  503     1         []              None         pause=0 wait=0
  504     1         []              None         pause=0 wait=0
  507     1         []              None         pause=0 wait=0
  EXC     3         [0.0, 0.0]      None
```
With an extractor present only 403 and 410 change (3 requests, spacing
`[0.0, 0.0]`). The same statuses on the two media-part layers, one matrix each:

```
MATRIX 2 - MEDIA-PART PARALLEL STRATEGY (_download_segment_parallel)
  429   3  [10.0, 10.0]  False  pause=[(video_url, 10.0)] x3
  500   3  [10.0, 10.0]  False  pause=[(video_url, 10.0)] x3
  503   3  [10.0, 10.0]  False  pause=[(video_url, 10.0)] x3
  408   1  []             False  pause=[]                  (fail fast)
  501   1  []             False  pause=[]
  507   1  []             False  pause=[]

MATRIX 3 - MEDIA-PART SEQUENTIAL STRATEGY (_download_segment_sequential)
  429   3  [0.437, 1.688]  False
  500   3  [0.047, 0.078]  False
  503   3  [0.047, 0.078]  False
  408   1  []               False
```
Every non-200 status is logged by the media-part layers
(`segment_download_failed status=503`); the manifest layer logs nothing at all
for a status response.

**Consequence:** The playlist is a single small GET. When the origin rate-limits
it — the condition the whole `RETRYABLE_STATUS_CODES` /
`throttled_rate` / per-origin-pause machinery exists to survive — the entire
download is abandoned on the first response, with **no** retry, **no** delay,
**no** pause, and **no** operator-visible diagnosis of the status that stopped
it. The two media-part strategies 60 lines below treat the identical status as
the canonical retryable. The transport-level failure path is also unthrottled:
three retries with measured spacing `[0.0, 0.0]`.

**Recommendation:** Give the manifest layer the same policy table the media-part
layers use — map 429/500/502/503/504 (and 408/425) through
`_compute_backoff_delay` + `_wait_with_shutdown`, notify the shared pause
coordinator the way `segment_downloader.py:189-196` does for parts, and log the
status on every non-200 outcome. Pass the coordinator into
`_fetch_playlist_with_retry` so the pause reaches it. Keep 403/410 on the
refresh path. Add a delay to the `continue` at `segment_downloader.py:504-505`.

---

### NET-003: `--quality worst` downloads the best stream, and the selected stream address is never given to the child at all

| Field | Value |
|-------|-------|
| **ID** | NET-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |

**Description:** The ladder selects a stream in
`QualitySelector.select(video.streams, quality)` and passes its URL as
`m3u8_url` to `download_with_ytdlp_with_resume_fallback`
(`downloader.py:691-704` → `downloader.py:508-521`). That URL never reaches the
child: `_download_with_ytdlp` (`ytdlp_downloader.py:564-574`) has no `m3u8_url`
parameter, and `ytdlp_downloader.py:623` appends the **page** URL as the child's
positional argument. The child is instead told to re-derive the stream itself,
from a format selector built at `ytdlp_downloader.py:255-258`:
```python
format_selector = (
    f"best[height<={quality_str}]" if quality_str and quality_str.isdigit() else "best"
)
```
`quality_str` is `quality.replace("p","")` (`ytdlp_downloader.py:606`), so
`QualityEnum.WORST` → `"worst"` → not a digit → `-f best`.

**Evidence:** Method **R3** (argv captured from the local stub) and **R7(a)**
(option object captured from the in-process library).

```
LADDER: what the child is told to download, per selected QualityEnum
  QualityEnum 240    -> yt-dlp -f 'best[height<=240]'
  QualityEnum 720    -> yt-dlp -f 'best[height<=720]'
  QualityEnum 1080   -> yt-dlp -f 'best[height<=1080]'
  QualityEnum 2160   -> yt-dlp -f 'best[height<=2160]'
  QualityEnum best   -> yt-dlp -f 'best'
  QualityEnum worst  -> yt-dlp -f 'best'          <== inverted
```
```
child argv url arg: https://vkvideo.ru/video-12345_67890
  (the selected m3u8_url is not in the argv at all)
  full argv: python -u -m yt_dlp --encoding utf-8 -o video.mp4
             -f 'best[height<=1080]' --newline --hls-prefer-native --no-warnings
             --socket-timeout 30 -R 3 --fragment-retries 3 -N 4
             --throttled-rate 100000 --user-agent AUDIT-UA/1.0
             --referer https://vkvideo.ru/
             https://vkvideo.ru/video-12345_67890
```

**Consequence:** `vkdownloader --quality worst` selects the **minimum**-height
stream (`quality.py:80`, `min(streams, key=lambda s: (s.height is None, s.height or 0))`),
discards it, and downloads the **highest** the origin offers. No log line records
that the delivered quality differs from the selected one — the only quality
record in the path is the `quality=` field echoed into
`starting_ytdlp_download` (`ytdlp_downloader.py:599-604`), which records the
*request*, not the delivery. For numeric qualities the app's exact selection is
likewise re-derived by the child's own ranking against a `<=` filter, so
`--quality 1080` can deliver 720 when no 1080 progressive format exists, with no
record of the substitution. Both the `yt-dlp` and `auto` methods take this path
(`downloader.py:504-521` and `:569-591`); only `ffmpeg` uses the selected
address.

**Recommendation:** Pass the selected `m3u8_url` into `_download_with_ytdlp` and
give it to the child as the positional argument (or as an input template), so
the address chosen by `QualitySelector` is the one downloaded. If the child must
re-select, derive the selector from the *selected* stream's height rather than
from the request string, and special-case `worst` — a `-f` expression that means
"best" when the caller asked for the worst is a silent inversion. Either way,
log the selected address and the delivered format.

---

### NET-004: A refreshed signed address is used for the manifest only — every media part is still requested from the stale host, with the fresh cookie

| Field | Value |
|-------|-------|
| **ID** | NET-004 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `_fetch_playlist_with_retry` obtains a replacement address on
403/410 and re-requests the manifest from it
(`segment_downloader.py:515-519`). The replacement never leaves that local
variable: `_run_download_session` builds the download policy with the **original**
argument at `segment_downloader.py:835` (`m3u8_url=m3u8_url`), and
`_download_segment_concurrent` resolves every relative segment path against
`policy.m3u8_url` (`segment_downloader.py:683-687`). The shared `headers` dict
*is* rewritten in place (`_handle_token_refresh`, `segment_downloader.py:479`,
`headers["Cookie"] = new_cookies`), so the fresh credential follows the fresh
address for the manifest and is then sent to the **old** host for every part.

**Evidence:** Method **R5** — scripted origin refuses the first request with 403
and serves a manifest on a different host; the extraction surface replaced by a
stub returning a chosen stream. Repeated for four different caller selections.

```
R5 - manifest refused once, replacement on a DIFFERENT host
  browser re-extractions performed: 1
  every request the session made, in order:
    t=0.000 status=403  url=https://cdn-OLD.example/seg/p.m3u8?sig=OLDTOKEN
                 Cookie='sid=STALECOOKIE'
    t=0.000 status=200  url=https://cdn-FRESH.example/seg/p.m3u8?sig=NEWTOKEN
                 Cookie='sid=FRESHCOOKIE'
    t=0.000 status=200  url=https://cdn-OLD.example/seg/seg/000.ts
                 Cookie='sid=FRESHCOOKIE'
    t=0.000 status=200  url=https://cdn-OLD.example/seg/seg/001.ts
                 Cookie='sid=FRESHCOOKIE'
  manifest address before refresh : https://cdn-OLD.example/seg/p.m3u8?sig=OLDTOKEN
  manifest address after  refresh : https://cdn-FRESH.example/seg/p.m3u8?sig=NEWTOKEN
  base each media part resolved against: https://cdn-OLD.example/seg/seg/000.ts
  part host == refreshed manifest host: False
  fresh credential sent to the stale part host: True
```
The same table for `selected='best'`, `'720'` and `'240'` produced identical
address and credential rows — the outcome does not depend on the selection.

**Consequence:** The recovery path exists, is taken, and does not work. Every
media part is requested with the **expired** signature from the old CDN host
while carrying the **new** session cookie. On a real VK manifest that yields 403
per part, which `_download_segment_parallel` treats as non-retryable
(`segment_downloader.py:247-257`, fail fast), so every part fails, `_tally_and_merge`
returns `None`, and the whole download fails — having already spent a browser
extraction to obtain an address it never used for the bytes. The new cookie is
also disclosed to the old host on every part request.

**Recommendation:** Have `_fetch_playlist_with_retry` return the address it
actually succeeded with (its local `current_url`) alongside the playlist text,
and pass that into `DownloadPolicy.m3u8_url` at
`segment_downloader.py:835`, so parts resolve against the base the refreshed
manifest was served from. Write the refreshed cookie only after the base is
switched, so the new credential is not sent to the old host.

---

### NET-005: The manifest-refresh path substitutes the first stream for the selected quality, with no record of the substitution

| Field | Value |
|-------|-------|
| **ID** | NET-005 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `_refresh_token_and_retry` (`segment_downloader.py:426-446`)
returns `str(streams[0].url)` — the first stream the forced re-extraction
produced — with no quality consideration at all:
```python
streams, new_cookies, _raw_cookies = await extractor.extract_streams_with_cookies(
    video_url, force_browser=True
)
if not streams:
    return None
return str(streams[0].url), new_cookies or ""
```
The two sibling refresh helpers do branch on the caller's selection —
`_attempt_segment_resume` (`ytdlp_downloader.py:503-521`) and `_resolve_cookies`
(`ytdlp_downloader.py:756-774`) both test `quality_enum == QualityEnum.BEST` and
log the outcome. The manifest-refresh helper does neither.

**Evidence:** Method **R5**, per-selection table. The stub's replacement stream
carried a distinct label in each run so that any use of it would be visible:
```
selected='1080'  replacement stream label='best'   -> streams[0] used, label never read
selected='best'  replacement stream label='best'   -> streams[0] used
selected='720'   replacement stream label='720p'   -> streams[0] used, label never read
selected='240'   replacement stream label='240p'   -> streams[0] used, label never read
```
The only log record produced on this path is
`token_expired_fetching_new` (`segment_downloader.py:515`) — a boolean event
with no address, no label and no selected value. In production the forced
extraction always produces `quality="best", height=None` for whatever the page
captured first (`extractor.py:297-305`), so the substitution is not merely
unguarded, it is a substitution of "best" for whatever was asked for.

**Consequence:** A `--quality 240` or `--quality 720` download that hits a token
expiry on the playlist is silently switched to the browser's first captured
address at whatever quality that address carries. Nothing in the log, the
returned path or the exit status records the change, so the operator cannot tell
that the video they asked for at 240p was delivered at a different quality.
Contrast the same repository's two other refresh helpers, which log
`fresh_token_obtained_for_resume quality=... selected_quality=...`.

**Recommendation:** Reuse the existing selection logic: parse the caller's
quality, run `QualitySelector` over the refreshed streams when it is `BEST`, and
apply the same explicit "preselected URL retained" branch the other two helpers
use when it is numeric. Log the selected and the delivered label in the same
record, so the substitution is stated when it happens. This is the *selection*
question; the rendering of a non-selectable label in an error's alternatives is
`08`'s (see NET-008).

---

### NET-006: Two of the four terms of the composed HTTP timeout are dead at the configured floor — and one is dead at every value in range

| Field | Value |
|-------|-------|
| **ID** | NET-006 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** Every aiohttp request builds the same four-term deadline from
one configured value, in three places:
`downloader_throttle.py:200-205` (media-part sequential),
`segment_downloader.py:224-229` (media-part parallel),
`segment_downloader.py:495-500` (manifest fetch):
```python
client_timeout = aiohttp.ClientTimeout(
    total=download_timeout,
    connect=min(30, download_timeout // 4),
    sock_connect=30,
    sock_read=60,
)
```
`total` is the whole-operation budget for the request; `connect` already bounds
pool acquisition and, for a new connection, supersedes `sock_connect`. A term
larger than, or equal-and-shadowed by, its container can never fire.

**Evidence:** Method **R7(b)** — the composed deadline evaluated at the smallest,
default and largest value the configuration permits
(`download_timeout: int = Field(default=300, ge=30, le=3600)`, `config.py:61-66`):
```
R7b - deadline composition at floor / default / ceiling
  floor    download_timeout=30    total=30  connect=min(30, d//4)=7   sock_connect=30  sock_read=60
           dead/exceeded terms: ['sock_read(60) > total(30)',
                                  'sock_connect(30) >= connect(7) - never binds']
  default  download_timeout=300   total=300 connect=min(30, d//4)=30  sock_connect=30  sock_read=60
           dead/exceeded terms: ['sock_connect(30) >= connect(30) - never binds']
  ceiling  download_timeout=3600  total=3600 connect=min(30, d//4)=30 sock_connect=30  sock_read=60
           dead/exceeded terms: ['sock_connect(30) >= connect(30) - never binds']
```
At the floor, `sock_read` (60) **exceeds** the term that contains it (`total`
= 30) and `sock_connect` (30) equals it. At the default and the ceiling,
`sock_connect` is still shadowed by `connect` and can never fire. Only `total`
and `connect` are live; `sock_connect` and `sock_read` are literals that no
setting reaches.

**Consequence:** A user who sets `VKDOWNLOADER_DOWNLOAD_TIMEOUT=30` to shorten
stalls gets a socket-read budget they cannot use — the 30 s whole-request budget
always fires first, so a segment that trickles one byte every 45 s is killed at
30 s despite the code asking for 60. And at every value in range the operator who
raises the setting to 3600 s gets `sock_read` still pinned at 60 s: a long,
silently-truncating download on a slow CDN is killed at 60 s of read inactivity
while the setting reads 3600. The two literals duplicate the bounded `connect`
term's purpose and are outside the setting's control entirely.

**Recommendation:** Derive every term from the same setting. `sock_connect` adds
nothing once `connect` is set and should be removed. `sock_read` should be
`min(60, download_timeout)` at the floor, or simply the setting value when the
intent is a per-read ceiling. If a hard 60 s read ceiling is deliberate, it
needs its own bounded setting rather than a literal inside a budget another
setting is supposed to control. Collapse the three identical copies into one
helper so the floor, default and ceiling can be checked in one place.

---

### NET-007: One configured HTTP request timeout is reused unchanged as the local concat's budget, while the two stages that actually transfer bytes have no budget at all

| Field | Value |
|-------|-------|
| **ID** | NET-007 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |

**Description:** `download_timeout` is declared as
`"HTTP client timeout in seconds for individual segment requests and playlist
fetches"` (`config.py:61-66`). At `segment_downloader.py:615` that same value is
handed to `_merge_segments_batched` as the budget for the ffmpeg **merge**
subprocesses (`ffmpeg_utils.py:304` and `:351`,
`asyncio.wait_for(process.communicate(), timeout=download_timeout)`) — a purely
local `concat` of files already on disk, with no network involved. It is applied
per subprocess, so a video with ceil(N/100) batches can occupy
`ceil(N/100) * download_timeout + download_timeout` seconds. In the opposite
direction, the two stages that do transfer bytes impose **no** budget at all:
`download_with_ffmpeg` (`downloader.py:305-372`) and `_download_with_ytdlp`
(`ytdlp_downloader.py:630-682`) both await a bare `process.wait()` with no
`wait_for`; only the shutdown event can end them.

**Evidence:** Method **R7(c)** — every stage that consumes the value, and the
budget it applies there:
```
R7c - every stage that consumes download_timeout, and the budget it applies
  stage                       file:line                                          mechanism                     budget applies to
  T2 in-process yt-dlp        extractor.py:201                                   socket_timeout                 per-socket
  T2 in-process yt-dlp        extractor.py:244                                   asyncio.wait_for              WHOLE OPERATION
  T1 manifest fetch           segment_downloader.py:496-500                      ClientTimeout.total           per-request
  T1 media part (parallel)    segment_downloader.py:224-229                      ClientTimeout.total           per-request
  T1 media part (sequential)  downloader_throttle.py:200-205                     ClientTimeout.total           per-request
  T3 yt-dlp child             ytdlp_downloader.py:274-275                        --socket-timeout              per-socket
  T5 ffmpeg BATCH MERGE       segment_downloader.py:615 -> ffmpeg_utils.py:304   asyncio.wait_for(communicate) per ffmpeg subprocess
  T5 ffmpeg FINAL MERGE       segment_downloader.py:615 -> ffmpeg_utils.py:351   asyncio.wait_for(communicate) per ffmpeg subprocess
  T4 ffmpeg direct transfer   -                                                  -                              NO BUDGET (process.wait() unbounded)
  T3 yt-dlp direct transfer   -                                                  -                              NO BUDGET (process.wait() unbounded)

  worst-case total merge time for a 250-segment video at the default 300s:
    3 batch stages x 300s + 1 final stage x 300s = 1200s (20 min)
    for a LOCAL concat of files already on disk
```
Two further terms are literals that duplicate the bounded setting's purpose:
`DownloadPolicy.download_timeout: int = 300` (`segment_downloader.py:66`) and
the five function defaults `download_timeout: int = 300`
(`segment_downloader.py:146, 217, 282, 314, 370`); `downloader_throttle.py:180`
is the one that is correctly derived from the model at import time
(`downloader_throttle.py:19`).

**Consequence:** An operator who raises `VKDOWNLOADER_DOWNLOAD_TIMEOUT` to let a
slow CDN finish has silently raised the ffmpeg merge budget by the same factor:
a stalled local concat can now burn 20 minutes per video with no progress
output, and a value set for a *request* governs a *disk operation*.
Symmetrically, a stalled ffmpeg or yt-dlp transfer of a live stream runs
unbounded — the process cannot end it but by Ctrl-C, and the partial it leaves
is what NET-015's predicate then mistakes for a resumable artefact.

**Recommendation:** Give the merge stages their own budget (derived from the
number of stages and the measured segment size, or a separate bounded setting)
rather than reusing the per-request value unchanged, and pass the merge's budget
once rather than per subprocess. Add an explicit `asyncio.wait_for` around the
two transfer stages' `process.wait()` so a stalled transfer is bounded by the
same setting the per-request budget uses. Replace the six literal `= 300`
defaults with the value derived from the settings model, as
`downloader_throttle.py:19` already does.

---

### NET-008: The intercepted address is an unconstrained "first captured wins", and the quality label attached to it is not a member of the declared enumeration

| Field | Value |
|-------|-------|
| **ID** | NET-008 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/infrastructure/network_monitor.py`, `src/vkdownloader/services/quality.py` |
| **Classification** | mandatory |

**Description:** The browser capture surface appends every qualifying address in
arrival order and deduplicates by exact string only
(`network_monitor.py:62-66`, `:132-136`) — no host constraint, no quality
constraint, no preference for a media playlist over a manifest. The extraction
surface then takes element zero unconditionally
(`extractor.py:297-305`):
```python
if monitor.m3u8_urls:
    stream = Stream(url=monitor.m3u8_urls[0], format=StreamFormat.HLS,
                    quality="best", width=None, height=None)
```
The label it attaches, `"best"`, and the label enumeration produces for a record
with no height, `"unknown"` (`extractor.py:63`,
`quality=f"{height}p" if height else "unknown"`), are **not members** of
`QualityEnum` (`models/enums.py:6-17`), so neither can be re-requested.

**Evidence:** Method **R4(b)** (two qualifying addresses fed in a fixed order)
and **R8** (label membership and re-request).
```
R4b - which captured address wins when several qualify
  fed in order: ['https://ads.tracker.example/video-9_9/stream.m3u8?ad=1',
                 'https://cdn.vkvideo.ru/video-1_2/720p/stream.m3u8?sig=G']
  m3u8_urls after capture: ['https://ads.tracker.example/video-9_9/stream.m3u8?ad=1',
                            'https://cdn.vkvideo.ru/video-1_2/720p/stream.m3u8?sig=G']
  address the extraction surface settles on (m3u8_urls[0]):
      https://ads.tracker.example/video-9_9/stream.m3u8?ad=1
```
```
R8 - label membership
  members of the declared enumeration QualityEnum:
      ['240','360','480','720','1080','1440','2160','best','worst']
  'unknown' is a member of that enumeration: False
  re-request of a stream whose label is 'unknown':
    label 'unknown' requested as 'unknown'  -> ValueError: 'unknown' is not a valid QualityEnum
    label 'unknown' requested as 'unknownp' -> ValueError: 'unknownp' is not a valid QualityEnum
  list_available_qualities -> ['1080p','720p','480p','360p','unknown']
  QualityNotAvailableError: Quality '240' not available.
    Available: ['1080p','720p','480p','unknown','unknown','360p']
```
The alternatives list repeats `'unknown'` twice for two distinct records with
the same label, and `downloader.py:685` logs
`available_qualities=available[:8]` containing it.

**Consequence:** Any third-party host whose URL ends in `.m3u8` and is fetched
before VK's own playlist becomes the delivered address — and it is then handed to
ffmpeg and to the segment downloader together with the session cookie
(`downloader.py:270-297`, `segment_downloader.py:900-905`). Separately, the
enumeration offers `"unknown"` to the operator as an available quality, in the
log line and in every "quality not available" error, but passing it back raises
`QualityParseError` — a label the caller can see and cannot act on.

**Recommendation:** Constrain the selection: filter captured addresses by host
against the expected CDN suffix, prefer a media playlist over a manifest (the
media playlist is the one whose segments the ladder can download, and its address
is normally the *second* capture), and record the host and label chosen in the
log. Add `"unknown"` as a `QualityEnum` member, or map it in `_find_quality_match`,
so the label enumeration produces is a label the enumeration accepts, and
deduplicate the alternatives list. This is the *selection* defect; the rendering
of a non-selectable label in the operator's output is `08`'s and is named here
rather than filed twice.

---

### NET-009: The shared per-origin pause is consulted at a strict subset of the sites that could consult it, and is keyed narrower than the resource it protects

| Field | Value |
|-------|-------|
| **ID** | NET-009 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** `URLBackoffCoordinator` is the process's only per-origin pause.
It is **set** in exactly one place, `_notify_backoff_for_retryable_status`
(`segment_downloader.py:189-196`, `pause(video_url, 10.0)`), reachable only from
the parallel media-part attempt (`segment_downloader.py:248`). It is
**consulted** in exactly two places: `_check_backoff_before_attempt`
(`segment_downloader.py:260-270`, called only from `_download_segment_parallel`
at `:336`) and the yt-dlp retry loop (`ytdlp_downloader.py:400-401`).

Three sites that can be throttled and cannot consult it:
- the **manifest fetch** layer, which has no coordinator parameter at all
  (`segment_downloader.py:484-492`);
- the **sequential** media-part strategy — `_download_segment_sequential`
  (`segment_downloader.py:139-181`) has no `backoff_coordinator` parameter, and
  `_download_segment:389-398` routes to it whenever
  `max_concurrent_downloads == 1`;
- the **in-process yt-dlp extraction** (`extractor.py:184-258`), which makes
  its own origin requests on a worker thread and has no pause at all.

The key is the VK **page** URL, not the origin: `pause(video_url, 10.0)` where
`video_url` is the page the user supplied, while the pressure is on the CDN host
that serves every item. `10.0` is a hard-coded literal, not derived from any
setting, and it is set for *every* retryable status, so a 503 gets the same
10 s pause as a 429.

**Evidence:** Method **R1** — three matrices, plus a call-site search
**index-scoped on `src/`, excluding `.kilo/worktrees/`**.

Call sites of the pause helper (the full list):
```
  SET:    services/segment_downloader.py:196   pause(video_url, 10.0)
  CONSULT services/segment_downloader.py:267   wait_if_paused(video_url)
  CONSULT services/ytdlp_downloader.py:401     wait_if_paused(video_url)
```
Sites that wait without consulting it (every rate-limiting wait in the process):
```
  services/downloader_throttle.py:361   asyncio.sleep(delay) in _wait_with_shutdown(None branch)
  services/downloader_throttle.py:365   _wait_with_shutdown body - the sequential media-part backoff
  services/extractor.py:242             asyncio.wait_for(run_in_executor(yt-dlp), download_timeout)
  services/segment_downloader.py:719    the anti-detection inter-segment delay
```
Observed per layer (R1 matrices):
```
  Matrix 1 (manifest):    429 -> pause=0 wait=0 ; 503 -> pause=0 wait=0
                          every status: pause=0 wait=0
  Matrix 2 (parallel):    429 -> pause=[('https://vkvideo.ru/video-12345_67890', 10.0)] x3
                          503 -> pause=[('https://vkvideo.ru/video-12345_67890', 10.0)] x3
  Matrix 3 (sequential):  429 -> n/a (no coordinator parameter)
                          503 -> n/a (no coordinator parameter)
```
Every recorded pause is keyed on the same page URL; the resource under pressure
(shared CDN host) does not appear in any key.

**Consequence:** With `VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS=1` — the documented
anti-detection mode — the pause is silently lost for every media part, so a 429
storm from the CDN is met with unthrottled retries from that video. In a batch,
two videos served by the same CDN each hold their own key, so neither is slowed
by the other's 429: the pause does not bound the pressure it exists to bound. The
in-process extraction, which is the surface that makes the *first* origin
contact of every download, is outside the pause's reach entirely.

**Recommendation:** Give the manifest layer and the sequential strategy the same
coordinator parameter the parallel strategy has, and pass it through
`DownloadPolicy` and `_download_segment_sequential` so both media-part strategies
share one pause. Consult the pause before the in-process extraction's first
request. Key the pause on the CDN host (or on the manifest host once it is
known) rather than the page URL, so all items served by one origin share a key,
and derive the 10 s duration from a bounded setting rather than a literal.

---

### NET-010: A connection-level failure on a retrying path is retried with zero measured delay, and the two media-part strategies disagree on whether to retry it at all

| Field | Value |
|-------|-------|
| **ID** | NET-010 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory |

**Description:** Three retrying paths treat a connection-level failure
differently, and none of them delays:
- the **manifest layer** catches `aiohttp.ClientError` in `_fetch_single_playlist`
  (`segment_downloader.py:461-463`), returns `None`, and the caller `continue`s
  (`segment_downloader.py:504-505`) — no delay, no pause;
- the **parallel media-part** strategy catches it in `_try_single_download_attempt`
  (`segment_downloader.py:301-303`), returns `None`, and the outer loop
  (`segment_downloader.py:333-357`) re-enters immediately — no delay, and no
  pause is set, because `_notify_backoff_for_retryable_status` is only reached
  from the *response* path at `:248`;
- the **sequential media-part** strategy catches it in `_retry_429_with_backoff`
  (`downloader_throttle.py:260-267`) and `return None` — **terminal on the first
  attempt**, no retry at all.

A 200 with an empty body has the same shape as a failure on the parallel
strategy: `_run_parallel_download_with_backoff:232-235` returns `None` and the
loop re-enters with no delay.

**Evidence:** Method **R1** — one transport-level-failure run per layer, each
measuring request count and wall-clock spacing between requests.
```
  Matrix 1 (manifest,    extractor=None):
    EXC  requests=3  delay-to-next=[0.0, 0.0]  returned=None
    EXC note: connection-level failure is retried with ZERO delay between attempts.
  Matrix 1 (manifest,    with extractor):
    EXC  requests=3  delay-to-next=[0.0, 0.0]  returned=None

  Matrix 2 (parallel media part):
    200 (empty body) requests=3  delay-to-next=[0.0, 0.0]  returned=False  pause=[] wait=3
    EXC              requests=3  delay-to-next=[0.0, 0.0]  returned=False  pause=[] wait=3
    EXC note: connection-level failure IS retried, and with ZERO delay (no pause set).
    429+Retry-After:2  requests=3  delay-to-next=[10.0, 10.0]  pause=[(video_url, 10.0)] x3

  Matrix 3 (sequential media part):
    EXC  requests=1  delay-to-next=[]  returned=False
    EXC note: connection-level failure is NOT retried at all (terminal on attempt 1).
    429+Retry-After:2  requests=3  delay-to-next=[2.0, 2.0]
    429+RA2 note: 3 requests + 3 waits, i.e. a wait AFTER the final attempt.
```
The 429 rows also expose a second asymmetry: the parallel strategy guards the
delay with `attempt < max_retries - 1`
(`_should_continue_on_retry`, `segment_downloader.py:199-205`) and so does not
sleep after its last attempt; the sequential strategy has no such guard
(`downloader_throttle.py:234-247`), so with `max_retries=3` and
`Retry-After: 2` it sleeps 2 s a third time and then gives up.

**Consequence:** A CDN that resets the connection produces three requests inside
the same millisecond, three times over, from every layer that retries — which is
the opposite of the etiquette the retry machinery exists to express. The same
failure on the sequential strategy gives up after one request, so
`VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS=1` turns a transient reset into a failed
download. On the response path the sequential strategy additionally burns one
full `Retry-After` interval as dead time after the final attempt.

**Recommendation:** Route the transport-level failure through the same policy as
a response on every layer: compute a delay from the attempt index, apply it via
`_wait_with_shutdown`, and notify the shared pause the way
`_notify_backoff_for_retryable_status` does, so the failure is bounded like a
429 instead of being retried instantly. Apply `_should_continue_on_retry` (or
its equivalent) in `_retry_429_with_backoff` so the final attempt does not sleep,
and make the sequential strategy retry transport failures to the same
`max_retries` budget as the parallel one.

---

### NET-011: The response-size guard measures after reading — on the declared-length-absent path the whole body is materialised before the cap is applied

| Field | Value |
|-------|-------|
| **ID** | NET-011 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | mandatory |

**Description:** `_intercept_response` guards the JSON-parsing branch with a
1,000,000-byte cap (`network_monitor.py:23`, `:73-105`). The `Content-Length`
pre-read is correct and the boundary is exact. The body cap is not a memory
bound: when the declared length is absent **or unparseable**, the code calls
`await response.body()` at `network_monitor.py:90` — which materialises the whole
body in the browser process — and only compares `len(body)` to the cap at
`:99-105`. The comment at `:87-88` states the opposite ("Enforce a byte cap even
when Content-Length is absent").

**Evidence:** Method **R4(c)** — the interceptor driven with a counting body in
five configurations, recording the bytes read before any size decision and the
decision taken, on the parsing branch:
```
  MAX_JSON_BODY_BYTES = 1000000
  case                                  bytes read    decision
  no declared length, body 10x the cap  10000000      skipped AFTER reading the whole body
  declared length above the cap         0             skipped on DECLARED length (body never read)
  declared length exactly the cap       0             skipped on DECLARED length (body never read)
  declared length one below the cap     999999        parsed
  declared length garbage ("not-a-number") 2000000    skipped AFTER reading the whole body
```
The two `0` rows confirm the guard is exact *at* the cap (not one byte below)
and that the declared-length path does bound memory. The first and last rows
confirm it does not on the other two paths.

**Consequence:** A chunked response, or one whose `Content-Length` is malformed,
of arbitrary size is fully buffered before the cap is consulted; the cap bounds
parsing work, not memory. A malformed `Content-Length` defeats the pre-read
guard entirely and routes straight to the unbounded path. The m3u8-address
branch (`:60-66`) never reads a body, so it is not affected; the gap is on the
branch that parses.

**Recommendation:** Treat an absent or unparseable `Content-Length` as
over-budget for the purposes of *starting* the read, or bound the read itself
rather than its result. With the Playwright `Response` API — which exposes
`body()` as an all-or-nothing call and no streaming reader — a true memory bound
is not expressible on this branch, so the honest fix is to cap on the
declared length when present and **skip** the branch when it is absent or
unparseable, rather than reading first and measuring after. Correct the comment
at `:87-88` to match whichever behaviour is adopted.

---

### NET-012: Acceptance admits a foreign origin that merely contains the pattern, and a negative identifier component; the derived identifier then reaches consumers that assume the canonical form

| Field | Value |
|-------|-------|
| **ID** | NET-012 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** The acceptance predicate is an unanchored `search` over the
whole reference (`extractor.py:25`, `:28-37`):
```python
VIDEO_ID_PATTERN = re.compile(r"video-(-?\d+)_(\d+)")
return bool(VIDEO_ID_PATTERN.search(url))
```
`?` on the first group accepts a leading `-` in the owner component. The
predicate is not confined to the single-download path: `cli.py:249` gates the
**entire** user-supplied batch list with it. The derived identifier
(`extractor.py:100-107`, `owner_id, video_id = match.group(1), match.group(2)`)
is then carried into `video_id_full` at `extractor.py:126-127` and `:161-162`
and into the log fields there — while four *other* consumers derive their
identifier from the **raw string** by splitting on `_`:
`downloader.py:530`, `ytdlp_downloader.py:608`, `segment_downloader.py:602` and
`:706`.

**Evidence:** Method **R9** — a fixed input table, accept/reject and the derived
identifier for each, then the consumer list.
```
  input                                                                 accept   derived id
  https://vkvideo.ru/video-123_456                                    True     video-123_456
  https://vk.com/video-123_456                                        True     video-123_456
  https://vkvideo.ru/video-123_456/extra                              True     video-123_456
  https://evil.example/watch?next=https%3A%2F%2Fvkvideo.ru%2Fvideo-123_456  True  video-123_456
  https://evil.example/video-123_456                                  True     video-123_456
  video-123_456                                                       True     video-123_456
  https://vkvideo.ru/video--123_456                                   True     video--123_456
  https://vkvideo.ru/video--1_456                                     True     video--1_456
  https://vkvideo.ru/video_123_456                                    False    -
  https://vkvideo.ru/videos-123_456                                   False    -
  https://vkvideo.ru/video-1O3_456                                    False    -
  https://vkvideo.ru/videos123_456                                    False    -
  https://vkvideo.ru/video-1_2?ref=https://vkvideo.ru/video-9_9        True     video-1_2
  (empty)                                                             False    -
```
Near misses are correctly rejected; the four accepted non-canonical rows are
not. `video--123_456` yields `owner_id = -123`, which is carried into
`video_id_full = "-123_456"` and into the `extracting_streams` log field
(`extractor.py:129`).

Consumers of the derived identifier, all of which assume the canonical form:
```
  src/vkdownloader/services/extractor.py:126-127   video_id_full = f"{owner_id}_{video_id}"
  src/vkdownloader/services/extractor.py:161-162   (same)
  src/vkdownloader/services/downloader.py:530      video_id = url.split("_")[-1]
  src/vkdownloader/services/ytdlp_downloader.py:608 video_id = url.split("_")[-1]
  src/vkdownloader/services/segment_downloader.py:602  video_id = video_url.split("_")[-1]
  src/vkdownloader/services/segment_downloader.py:706  video_id = video_url.split("_")[-1]
```
For the accepted foreign-origin input those four yield a fragment such as
`456` (or `456%26x%3D1` when the pattern is inside a query value); for the
trailing-path input they yield `456/extra`.

**Consequence:** A batch list containing `https://evil.example/watch?next=...`
or any foreign origin whose path embeds the pattern is accepted, counted as
valid, and then handed unchanged to `page.goto(url)` (`extractor.py:273`) and to
the third-party downloader as a page URL — the gate the list relies on is a
substring test, not an origin test. A negative owner id is accepted and carried
into the identifier and the logs. The identifier is then re-derived by four
consumers from the raw string, so the value that identifies a video in the
progress display is not the value the parser produced.

**Recommendation:** Anchor acceptance to the origin and to the path, e.g. match
the whole path component against `^video(-?\d+)_(\d+)$` after `urlparse`, and
require the host to be in the expected set. Reject a negative owner component at
acceptance rather than carrying it forward. Derive the per-item identifier once,
in the parser, and pass it to the four consumers instead of re-slicing the raw
URL, so an accepted non-canonical input cannot produce a different identifier in
the log than in the parser.

---

### NET-013: Request-fidelity and verification policies reach a strict subset of the transports; the two surfaces of the same third-party downloader present different identities

| Field | Value |
|-------|-------|
| **ID** | NET-013 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | recommended |

**Description:** Counted as a transport inventory, the process reaches the origin
in six distinct ways: **T1** `aiohttp.ClientSession` (manifest + every media
part), **T2** the third-party downloader as an in-process library on a worker
thread, **T3** the same downloader as a child process, **T4** `ffmpeg` as a child
process transferring a live stream, **T5** `ffmpeg` as a child process doing a
local concat (no network; retained in the inventory for completeness), **T6**
Chromium via Playwright. Four of the six carry the configured user agent, three
carry the referer, two honour `throttled_rate`, and the two surfaces of the same
downloader (T2, T3) carry a *different* option set.

**Evidence:** Method **R6(a)-(d)** — a policy reach table built from
index-scoped call sites (`src/`, worktree directories excluded), the flag/warning
counts, and a runtime capture of what each surface is actually handed.

```
R6a - transport inventory
  T1  aiohttp.ClientSession (manifest fetch + every media part)   services/segment_downloader.py:797
  T2  third-party downloader as an in-process library (thread)   services/extractor.py:211,243
  T3  third-party downloader as a child process                  services/ytdlp_downloader.py:631
  T4  ffmpeg as a child process (direct HLS transfer)           services/downloader.py:305
  T5  ffmpeg as a child process (concat merge, N+1 invocations)  services/ffmpeg_utils.py:297,344
  T6  Chromium via Playwright (page load + interception)         infrastructure/browser.py:40

R6b - policy -> read-site count against the transport count
  policy                            read sites  transports reached
  ssl_verify                        4           4/6   missing: T5, T6
  user_agent                        4           4/6   missing: T2, T5
  Referer (hard-coded https://vkvideo.ru/)  3       3/6   missing: T2, T5, T6
  throttled_rate                    2           2/6   missing: T1, T4, T5, T6
  download_timeout                  3           3/6   missing: T4, T5, T6
  max_concurrent_downloads          3           3/6   missing: T2, T4, T5, T6
  http_chunk_size                   1           1/6   missing: T1, T2, T4, T5, T6
```
Verification disablement, as **two separate numbers**:
```
R6c - flag sites and warning sites
  T2  services/extractor.py:197                 nocheckcertificate = not settings.ssl_verify   warns? NO
  T3  services/ytdlp_downloader.py:298          --no-check-certificates                          warns? yes
  T1  services/segment_downloader.py:536-543    ssl.CERT_NONE, check_hostname=False              warns? yes
  T4  services/downloader.py:298-300            ffmpeg -tls_verify 0                             warns? NO
  flag sites = 4;  warning sites = 2
  distance T2 -> nearest warning: none in this module (nearest is a different surface, 779 lines away)
  distance T4 -> nearest warning: none in this module (nearest is a different transport)
  T6 (Chromium) has no flag site; browser.py:40-43 never passes ignore_https_errors=
```
Per-transport request fidelity, captured at runtime:
```
R6d - in-process library option object, in full:
  quiet, no_warnings, extract_flat, nocheckcertificate, socket_timeout, retries,
  fragment_retries, throttled_rate
  -> no 'user_agent', no 'http_headers' key at all
R6d - T1 aiohttp request headers:  User-Agent = 'AUDIT-UA/1.0'
                                    Referer  = 'https://vkvideo.ru/'
R6d - T3 child argv (relevant tail): --user-agent AUDIT-UA/1.0 --referer https://vkvideo.ru/
R6d - T4 ffmpeg argfile:            -headers 'User-Agent: AUDIT-UA/1.0 Referer: https://vkvideo.ru/'
R6d - T6 context kwargs:            user_agent='AUDIT-UA/1.0', locale='ru-RU', timezone_id='Europe/Moscow'
R6d - T5 merge argv:                ffmpeg -y -f concat -safe 0 -i list.txt -c copy o.mp4   (no network)
```

**Consequence:** The two surfaces of the same third-party downloader present
**different identities** to the origin: the extraction surface (T2) sends the
library's own default user agent and no referer, while the download surface (T3)
sends the configured agent and referer. The extraction surface is the one that
makes the *first* origin contact of every download, including every forced
re-extraction, so a user who sets a custom user agent to look like a browser is
unidentified at exactly the moment the origin is most likely to inspect. With
`ssl_verify=false`, two of the four flag sites (T2, T4) disable verification
without any warning in their own module, and the browser's TLS posture is
undeclared because `ignore_https_errors` is never passed. `throttled_rate` — the
setting whose declared purpose is rate limiting — governs the two surfaces that
are not the ones carrying most of the traffic.

**Recommendation:** Put the configured user agent and referer into the in-process
option object (`http_headers` / `user_agent`) so T2 and T3 present the same
identity, and add a warning beside the two un-warned `ssl_verify` flag sites so
all four sites announce when verification is off. Pass `ignore_https_errors`
explicitly to the browser context so T6's TLS posture is declared rather than
inherited. Treat "reaches a strict subset" as a documented decision: if
`throttled_rate` deliberately does not govern the aiohttp surface (the segment
path has its own pacing at `segment_downloader.py:719`, itself disabled in batch
mode), say so in the setting's description rather than leaving the count at 2/6.

---

### NET-014: The effective simultaneous request rate against one origin is the square of the per-item bound, and nothing else caps it

| Field | Value |
|-------|-------|
| **ID** | NET-014 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `max_concurrent_downloads` is declared as "Maximum number of
videos downloading concurrently in a batch" (`config.py:89-96`, `ge=1 le=16`).
It is applied at **two** levels, and there is no third bound to contain the
product:
- whole-item gate — `shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)`
  (`batch_downloader.py:328`);
- per-item fan-out — the same value is passed to the child as `-N`
  (`ytdlp_downloader.py:280-281`) *and* used as the per-item segment semaphore
  (`segment_downloader.py:822`, `asyncio.Semaphore(max_concurrent_downloads)`).

The only other ceiling in the chain is `TCPConnector(limit=10)`
(`segment_downloader.py:537`, `:543`), a hard-coded literal unrelated to the
setting. `throttled_rate` does not govern the aiohttp surface at all (NET-013).

**Evidence:** Method **R6(e)** — the three bounds read from the configuration
model, then the product:
```
  max_concurrent_downloads     default=4     ge=1  le=16
  download_timeout             default=300   ge=30 le=3600
  throttled_rate               default=100000 ge=50000 le=1000000
  max_retries                  default=3     ge=1  le=10

  whole-item bound (batch video semaphore)   = max_concurrent_downloads = 16
  per-child bound passed to the child (-N)   = max_concurrent_downloads = 16
  segment-layer semaphore per item           = max_concurrent_downloads = 16
  aiohttp TCPConnector limit (hard-coded)    = 10   (segment_downloader.py:537,543)
  PRODUCT against one origin at the ceiling  = 16 x 16 = 256
  same product at the default                 = 4 x 4 = 16
  note: the two factors are the SAME setting, so the per-item bound is applied
  twice - once as a whole-item gate and once as the per-item fan-out - and its
  effect against the origin is squared rather than bounded.
```

**Consequence:** At the declared ceiling a batch can have 16 videos in flight,
each opening 16 concurrent requests to the CDN: 256 simultaneous requests from
one process to one origin, at 16x the intended per-video rate, from a setting
the operator raised in order to download *videos* in parallel.
`TCPConnector(limit=10)` does not bound that product: `_create_connector`
has exactly one call site, inside `_run_download_session`, which runs once per
video, and each call is paired with its own `ClientSession`. There is no
process-wide pool and no process-wide ceiling of 10. The aggregate connection
ceiling is 10 x `max_concurrent_downloads` — 4 x 10 = 40 at the default and
16 x 10 = 160 at the declared ceiling, exactly as phase `04` states in
`CON-009`; and nothing bounds the aggregate request count, so the origin is
the only place it is discovered. Seam: the `limit=10` literal is phase `04`'s
by phase assignment, and `CON-009` records that carve-out.

**Recommendation:** Decide which of the two levels the setting governs and stop
using it for both. If it is the whole-item gate, give the child and the segment
layer their own separately bounded settings; if it is the per-item fan-out, gate
the batch on a different value. Whatever the choice, bound the per-video
concurrent-request count with a setting rather than the `limit=10` literal, so the
product is expressible and checkable. Seam: the hard-coded connector ceiling
itself is `04`'s by phase assignment; only the product and the duplication are
filed here.

---

### NET-015: The ladder's handoffs are asymmetric, and the fallback predicate inspects one of the two names a partial can take

| Field | Value |
|-------|-------|
| **ID** | NET-015 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |

**Description:** Two handoffs hand a failed method's output path to the segment
stage. One removes the predecessor's partial first —
`ytdlp_downloader.py:531` (`output_file.unlink()`, with the comment "Remove
partial file to start clean segment download"). The other does not —
`downloader.py:550-567`: `download_with_ffmpeg` returning `None` leads straight
into `download_hls_with_resume` with the same `output_file`, which the ffmpeg
stage has already truncated and partially written.

The predicate that decides whether the fallback runs at all inspects **one** name
(`ytdlp_downloader.py:415-417`):
```python
if not validated_output.exists() or validated_output.stat().st_size == 0:
    return None
```
`_attempt_segment_resume` is therefore reached only when a non-empty file exists
at `output_file`. The residue line at `ytdlp_downloader.py:443-446` cleans the
same single name.

**Evidence:** Method **R3** — the process-launch boundary replaced by a local
stub that leaves a partial under each of the three possible names in turn, and
the segment stage replaced by a recorder.
```
LADDER: yt-dlp child fails, leaving 'output' (quality=1080)
  [info] download_interrupted_switching_to_segments path=...video.mp4 retry=1 size=4096
  [info] browser_streams_selected_with_preselected_url_for_resume m3u8_url=https://cdn-OLD.example/... quality=1080
  forced browser extractions: 1
  segment stage invocations: [{'m3u8_url': 'https://cdn-OLD.example/p.m3u8?sig=STALE',
                               'cookies': 'sid=FRESH', 'quality': '1080',
                               'output_file': '...video.mp4'}]

LADDER: yt-dlp child fails, leaving 'part' (quality=1080)
  [error] download_failed error='Unknown yt-dlp error' returncode=1
  forced browser extractions: 0
  returned: None
  files on disk: [('video.mp4.part', 4096)]
  segment stage invocations: <NEVER REACHED>

LADDER: yt-dlp child fails, leaving 'nothing'
  forced browser extractions: 0
  returned: None
  segment stage invocations: <NEVER REACHED>

LADDER: ffmpeg stage fails after writing a partial to the FINAL output path
  before handoff: [('video.mp4', 3584)]
  after handoff, the next stage received output_file: ...video.mp4
  the failed stage's partial still present at that path: True size=3584
```
The first case also shows the address the next stage receives: the **stale**
pre-selected `m3u8_url` paired with the **fresh** cookie (address freshness is
filed separately as NET-004/NET-005 territory; here the relevant fact is that the
partial was removed and the fallback ran).

**Consequence:** The advertised retry-with-resume fallback is skipped whenever
the child leaves its residue under the `.part` name — the predicate does not
look there, so the ladder returns `None` after the retry budget and never
attempts the segment stage. After an ffmpeg failure a corrupt, non-zero-length
file stays at the operator's chosen output path, indistinguishable from a
completed download; and on a later run of the same URL, `ytdlp_downloader.py:416`
reads that corrupt file as "a partial exists" and skips the yt-dlp path
altogether.

**UNVERIFIED sub-claim:** *which* of the two names the child leaves on failure is
internal behaviour of the third-party tool and is not observable from this
process; it is recorded as a skip, not asserted. What is established here is the
code-level fact that the predicate and the cleanup cover exactly one of the two
names, so the fallback is reached or not depending on a detail this repository
does not control and does not check.

**Recommendation:** Probe both `output_file` and `output_file.part` in the
predicate at `ytdlp_downloader.py:415-417` and clean both at `:443-446`, so the
fallback does not depend on the child's internal naming. Make the two handoffs
agree: remove the failed stage's partial before handing its path on, in
`downloader.py:550-567` as `ytdlp_downloader.py:531` already does, so a corrupt
artefact never occupies the destination the merge stage is about to write.

---

### NET-016: The intercepted-address normaliser promotes a relative path to a host, carries a plaintext address forward in plaintext, and contains an unreachable branch

| Field | Value |
|-------|-------|
| **ID** | NET-016 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | mandatory |

**Description:** `_normalize_url` (`network_monitor.py:41-51`) is a single
fall-through chain. Its bare-promotion branch (`:51`) prefixes `https://` to
anything not already absolute and not rooted — including a relative path such as
`a/stream.m3u8`, which becomes the host `a`. An absolute `http://` address is
returned unchanged (`:44-45`), so a plaintext address is carried forward in
plaintext, while every other form is silently promoted to `https`. The branch
`:49-50` (`if url.startswith("//")`) is unreachable: `:47` already consumed
every string starting with `/`.

**Evidence:** Method **R4(a)** — fifteen address forms through the normaliser,
then the branch reach counts.
```
  form                        input                                       normalised                                  scheme
  absolute https              https://cdn.example/a/stream.m3u8           https://cdn.example/a/stream.m3u8           https
  absolute http               http://cdn.example/a/stream.m3u8            http://cdn.example/a/stream.m3u8            http
  absolute http + query       http://cdn.example/a/stream.m3u8?sig=X     http://cdn.example/a/stream.m3u8?sig=X     http
  scheme-relative             //cdn.example/a/stream.m3u8                 https://cdn.example/a/stream.m3u8           https
  root-relative               /a/stream.m3u8                              https://a/stream.m3u8                       https
  bare host + path            cdn.example/a/stream.m3u8                   https://cdn.example/a/stream.m3u8           https
  bare relative path          a/stream.m3u8                               https://a/stream.m3u8                       https
  bare filename               stream.m3u8                                 https://stream.m3u8                         https
  leading whitespace          '  https://cdn.example/a/stream.m3u8  '    https://cdn.example/a/stream.m3u8           https

  branch reachability:
    line 44-45 'startswith http(s)://'       reached by 5/15 inputs
    line 47-48 inner ternary 'startswith //' reached by 4/15 inputs
    line 49-50 'if url.startswith("//")'     reached by 0/15 inputs -> UNREACHABLE
    line 51     bare promotion                reached by 6/15 inputs
```
```
R4b2 - a JSON payload whose HLS value is a bare relative path
  json value '720/stream.m3u8' -> ['https://720/stream.m3u8']       (host "720")
```

**Consequence:** A JSON payload whose `hls` value is a relative path yields an
address on a nonexistent host (`720`), which `extractor.py:297-305` then reports
as a discovered stream and hands to the transfer stages. An `http://` address
captured from the page is carried forward unchanged, so the `Cookie` header
assembled at `segment_downloader.py:900-905` and the ffmpeg `-headers` at
`downloader.py:277-279` are sent in the clear to that host — while the same
normaliser promotes a *scheme-relative* `//host/...` to https, so whether
plaintext is carried forward depends on which form the page happened to use.

**Recommendation:** Promote only forms that actually name a host; resolve a
root-relative address against the page's own origin (available on the response)
instead of treating its first segment as a hostname, and drop candidates that do
not resolve to an absolute `https://` address. Delete the unreachable branch at
`:49-50`.

---

### NET-017: Format classification matches one literal anywhere in the address, a record with no codec key is treated as video, and the ranker cannot tell a placeholder height from an absent one

| Field | Value |
|-------|-------|
| **ID** | NET-017 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/quality.py` |
| **Classification** | mandatory |

**Description:** Three enumeration predicates read format metadata by
inspection rather than by structure:
- `extractor.py:51` excludes audio with `format.get("vcodec") == "none"` — a
  record that **omits** `vcodec` is not audio by that test and survives;
- `extractor.py:62` classifies with `".m3u8" in format_url` — a substring test
  over the whole reference, so a query value, a fragment or a directory name
  containing that literal classifies the record as HLS;
- `extractor.py:63` labels a record `"unknown"` when `height` is falsy, which
  covers `height=0` as well as `height=None`, and the ranker key
  `quality.py:77-80` then treats `height=0` as a real resolution that outranks
  an explicitly absent one.

**Evidence:** Method **R8** — a fixed eight-record format table through
`_build_streams`, then the ranker, then two targeted follow-ups.
```
  record                                        survives   format label
  video-only 1080 mp4                           yes        mp4    1080p
  video-only 720 m3u8                           yes        hls    720p
  audio-only 128k (vcodec="none")               NO         -      -
  no codec key at all                           yes        mp4    480p
  no height                                     yes        mp4    unknown
  height zero                                   yes        mp4    unknown
  no url                                        NO         -      -
  total survivors: 6 of 8
```
```
R8 follow-up 1 - classification by structure vs by substring anywhere
  true HLS playlist                            https://c/720/stream.m3u8               -> hls
  progressive mp4 whose QUERY carries .m3u8    .../video.mp4?src=https://x/a.m3u8&t=1 -> hls  MISCLASSIFIED
  directory named .m3u8                        https://c/v.m3u8/720/video.mp4         -> hls  MISCLASSIFIED

R8 follow-up 2 - set = [height=None, height=0]
  best   -> https://c/zero.mp4 height=0
  worst  -> https://c/zero.mp4 height=0
  labels: ['unknown']
```

**Consequence:** An audio-only record that omits `vcodec` is offered and
selectable as a video stream; a progressive MP4 is routed to the HLS path, and
its address is then handed to ffmpeg (`downloader.py:589-590`) and to the segment
downloader, neither of which will get a playlist. When the enumeration carries
no real resolution, `best` and `worst` select the same record — the one with the
least information.

**Recommendation:** Classify on the parsed path's suffix rather than a substring
over the whole reference, and exclude a record that is neither video-bearing nor
explicitly audio-only. Treat `height <= 0` as absent in the label and in the
ranker key, so a placeholder cannot outrank a missing value.

---

### NET-018: `_parse_retry_after` rejects three of the five date forms the specification permits, accepts a negative delay, and the ceiling is applied before the server's value

| Field | Value |
|-------|-------|
| **ID** | NET-018 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory |

**Description:** `_parse_retry_after` (`downloader_throttle.py:272-303`) accepts
only the IMF-fixdate form (`parsedate_to_datetime` re-`strftime`-ed to
`"%a, %d %b %Y %H:%M:%S GMT"`) plus a bare `float()`. Three of the five date
forms HTTP permits are not parsed, a past date is silently ignored (correct per
specification), and `float()` accepts a negative value.

The ceiling is applied in the wrong order. `_compute_backoff_delay`
(`downloader_throttle.py:306-338`) computes `min(delay, 30.0)` at line 330 and
only *then* applies `max(delay, retry_after)` at line 336 — so the local ceiling
bounds the local term, and the server's value is applied outside it, unbounded.

**Evidence:** Method **R2** — a fourteen-row header-form table, the full
compute-then-clamp path at attempt indices 0..10, two real waits raced against a
3 s observer, and one end-to-end run through the parallel media-part layer.
```
R2a - _parse_retry_after over every header form the specification permits
  form                                     header                                parsed
  integer seconds                          120                                   120.0
  non-integer seconds                      2.5                                   2.5
  exponent notation                        1e1                                  10.0
  HTTP-date IMF-fixdate (RFC 9110)         <+60s, GMT>                           59.96
  HTTP-date with +0000 offset              <+60s, +0000>                         None
  HTTP-date obsolete RFC 850               Tue, 29-Sep-26 09:10:38 GMT           None
  HTTP-date obsolete asctime()             Tue Sep 29 09:10:38 2026              None
  HTTP-date lower-case day/month           mon, 01 jan 2035 00:00:00 gmt          260549421.96
  HTTP-date in the past                    <-600s>                               None
  HTTP-date far in the future              <+86400s>                             86399.96
  garbage 1                                soon                                  None
  garbage 2                                120 seconds                           None
  whitespace padded                        "  30  "                              30.0
  negative                                 -5                                    -5.0
  absent (no header)                       <absent>                              None

R2b - full compute-then-clamp path (jittered local term shown for the first rows)
  attempt  computed only  RA=600     RA=0.001   RA absent  bind
  0        0.6343         600.0      0.6343     0.6343     -
  1        1.3288         600.0      1.3288     1.3288     -
  5        30.0           600.0      30.0       30.0       local-30s-cap
  deterministic ceiling probe: max computed over attempts 0..40 = 29.91
  (the local cap binds from attempt 5 upward for 429, from attempt 10 for 500;
   the server value is applied AFTER the cap and is never clamped)

R2c - is the waited value bounded?  A real wait, raced against a 3s observer
  _compute_backoff_delay(429, attempt=0, Retry-After=600) = 600.0
  wait still pending after 3.00s with budget 600.0s -> no 30s ceiling is applied
  lower-case date form parses to 260549421.96 s (8.26 years)
  real wait on the lower-case date form still pending after 3.00s with that budget

R2d - end-to-end through the parallel media-part layer
  Retry-After=12, max_retries=2 -> n=3 spacing=[12.0] returned=False
```

**Consequence:** A server that sends the obsolete RFC 850 or `asctime()` form —
both still permitted for recipients, and still emitted by real origins — gets
the local jitter instead of the delay it asked for. A syntactically valid date
far in the future, whether in conventional or lower case, makes the process sleep
for it: with the lower-case form the computed budget is **8.26 years**, and the
only escape is the shutdown event, i.e. Ctrl-C. `-5` is returned as a delay
value. A legitimate `Retry-After: 600` puts the process to sleep for ten minutes
on a request whose own configured budget is 30-300 s.

**Recommendation:** Parse all three HTTP-date forms (use
`email.utils.parsedate_to_datetime` and accept its result rather than
re-`strftime`-ing one form) and reject a non-positive parsed value. Clamp
*after* taking the maximum with the server's value, so the ceiling bounds the
wait the process actually performs, and decide explicitly whether the ceiling is
per-request or per-video — on a slow origin a long server delay should not
freeze one attempt for an hour, but it must be capped by something, and today it
is capped by nothing.

**Boundary note:** the *wording* of the precedence comment at
`downloader_throttle.py:334` ("Prefer Retry-After header over calculated delay")
against the `max()` at `:336` — a mismatch pinned by
`tests/test_downloader_throttle.py:605-608` — is a documentation-against-comment
question and is **not** filed here; it is named for `09`.

---

## Documented Skips

Recorded as skips, not as clean results. Nothing below is claimed either way.

### SKIP-01: Whether a child process *enforces* the certificate policy it is handed
`downloader.py:298-300` puts `-tls_verify 0` into the ffmpeg argfile;
`ytdlp_downloader.py:298` puts `--no-check-certificates` into the child argv.
Both were **delivered** in this run (R7(a)/R3) and both were observed in the
captured argv/argfile. Whether the child honours them is internal to that binary
and is not observable from this process. No finding is filed on enforcement.
Platform: Windows, declared.

### SKIP-02: Whether a child process enforces the transfer budgets it is handed
`--socket-timeout`, `-R`, `--fragment-retries`, `-N` and `--throttled-rate` were
observed in the captured argv (R7(a)); their enforcement is internal to the
child. What *is* established and filed is the argv content itself and the
*absence* of a whole-operation budget on the two transfer stages (NET-007).

### SKIP-03: Internal failure behaviour of the third-party downloader and the browser driver
Out of scope by design. The specific consequence is recorded inside NET-015: the
*residue name* the child leaves on failure (`X.mp4` vs `X.mp4.part`) was not
observed, and is marked UNVERIFIED there rather than asserted.

### SKIP-04: `TCPConnector(limit=10)` as a connection ceiling
`segment_downloader.py:537`, `:543`. `04`'s by phase assignment. Only the
**product** of the bounds is filed (NET-014), with `04` named as the owner of the
ceiling itself.

### SKIP-05: Cookie lifetime, permissions and retention
Cookie-file permission mode, cleanup, and the query-string embedding of the file
path are `06`'s by phase assignment. What is filed here is the cookie **as a
request credential** — its injection (`segment_downloader.py:900-905`,
`downloader.py:277-279`), its refresh (NET-004, NET-005) and its non-disclosure
in request-URL logging (the `sanitize_url_for_log` redaction observed in every
captured log line).

### SKIP-06: A real network, a real origin, and a real Chromium
No socket was opened and no browser was launched. Every network subject in this
report was established against a scripted in-process origin, a local stub at the
process-launch boundary, and locally constructed values. The composition,
classification and acceptance tables (R6-R9) are exact; the *runtime* rows
(R1-R5) reflect the code's control flow, not any origin's real behaviour.

---

## Baselines (R10)

The state this report was observed against, and the subjects with no test
coverage, declared before being checked.

### Static and test baselines (R10a)

| Command | Exit | Output |
|---------|------|--------|
| `uv run pytest -q -rs` | 0 | 486 passed, 4 skipped |
| `uv run ruff check src tests` | 0 | `All checks passed!` |
| `uv run ruff format --check src tests` | 0 | `52 files already formatted` |
| `uv run mypy src` | 0 | `Success: no issues found in 30 source files` |

All 4 skips are one platform gate, not four independent subjects:
```
tests/test_cookie_permissions.py:57
  SKIPPED (Owner-only confinement is not offered on Windows, so an insecure
  fallback is used) - D-11 contract requires owner-only permissions, which the
  platform does not provide.
```
The three static tools are clean, so nothing in this report is attributable to a
type error, a lint violation or a formatting violation; every finding is a
behavioural or specification gap.

### Transport-symbol coverage (R10b) — declared before being checked

Searched the test tree (`tests/`), the index, excluding worktree directories:

| Pattern | Matches in `tests/` | Consequence |
|---------|---------------------|-------------|
| `aiohttp` | **0** | The aiohttp transport layer — manifest fetch and every media part — has **no test of any kind**. |
| `ClientTimeout \| TCPConnector \| ssl. \| create_default_context \| CERT_NONE \| check_hostname` | **0** | Timeout composition and certificate configuration have **no test**. |
| `Retry-After \| retry_after \| _parse_retry_after \| _compute_backoff_delay \| RETRYABLE` | 44 | Covered. |
| `NetworkMonitor \| _normalize_url \| m3u8_urls \| is_valid_video_url \| parse_video_id \| VIDEO_ID_PATTERN` | 49 | Covered. |

Consequence for the findings above: every subject established here about the
aiohttp layers, the merge stage, the ladder handoff and the per-surface option
sets is established by the scripted origin and the local stub — **not** by the
suite. The 486 passes include zero assertions on any of those paths, so a
regression in NET-001, NET-002, NET-006, NET-007, NET-010, NET-011 or NET-014
would be invisible to the existing tests. The first cheap step towards closing
that is a test for the merge stage's segment-deletion ordering, since that is
where the only CRITICAL finding lives.

---
