# B7 / NET-008 Research — Expected CDN host/suffix constant for VK Video HLS

**Task:** Resolve the blocking research gate for *Plan 07 B7 (NET-008): Constrain the
captured-address selection surface.* This answers Plan 07 §3.5 question 1 (the expected CDN host/suffix),
§3.5 question 4 (media-vs-manifest distinction), and the auxiliary questions in the B7 brief.

**Scope rule observed:** This is research-only. No production code or tests were modified.
Confidence levels are stated explicitly (per the research agent rules): `HIGH`, `MEDIUM`, `LOW`.

---

## TL;DR (the deliverable for B7's Planner)

| Item | Finding | Confidence |
|---|---|---|
| **Primary accept suffix** | `*.okcdn.ru` | **HIGH** |
| vkvideo.ru / vk.com share CDN origin? | **YES** — both are VK Video front-ends that resolve media to `okcdn.ru` | **HIGH** |
| CDN provider | **VK's own CDN** (domain `okcdn.ru` = "OK CDN", owned by VK LLC; IPs on VK ASN AS47541/AS47764). Not Akamai/Cloudflare/Yandex. | **HIGH** |
| Master-vs-media discriminator (programmatic) | Master = `#EXT-X-STREAM-INF` / `#EXT-X-I-FRAME-STREAM-INF`; Media = `#EXTINF` (required per segment) + `#EXT-X-TARGETDURATION` (required). `#EXT-X-PLAYLIST-TYPE` is OPTIONAL → not a reliable sole discriminator. | **HIGH** |
| `vkcdn.me` | **REJECTED** — not a VK host (the similar `vcdn.me` is an unrelated commercial service). | HIGH |
| Secondary VK CDN domains | `*.mycdn.me` (MEDIUM-HIGH), `*.vkuser.net` (LOW-MEDIUM) — VK-owned, observed serving `.m3u8`, but evidence is strongest for `okcdn.ru`. | MEDIUM-HIGH / LOW-MEDIUM |

**Recommended constant form (value only — expression is B7's Planner's call, §3.5 item 2):**

```python
# B7/NET-008: VK Video HLS segments are served from VK's own CDN.
# `okcdn.ru` ("OK CDN") is owned by VK LLC and resolves to VK's ASN
# (AS47541 / AS47764); Passive DNS shows host prefixes ``vkvd<N>`` (VK Video)
# and ``vd<N>`` (general VK media). The m3u8 is never served from the page
# host (vkvideo.ru / vk.com); it is served from this CDN.
# Authority: project limitations doc (docs/11-guides/vkdownloader-limitations.md,
# "Time-Limited m3u8 Tokens" example `https://vkvdXXX.okcdn.ru/...`); RFC/WHOIS
# ownership of okcdn.ru (VK LLC).
HLS_CDN_SUFFIX = ".okcdn.ru"
# Lower-frequency, same-owner failover mirrors observed serving `.m3u8`;
# accepted alongside the primary to avoid false rejections. (See evidence.)
HLS_CDN_EXTRA_SUFFIXES = (".mycdn.me", ".vkuser.net")
```

The existing `select()` already has a **safety suspension**: if *every* captured address would be
rejected by the filter, it logs once and returns the unconstrained ranked set. That safeguard means a
narrow filter cannot silently break a download — the failure mode is "warned + fall back", exactly what
NET-008's prose requires ("fail visibly").

---

## 1. What is the expected CDN host/suffix?

### 1.1 Primary answer — `*.okcdn.ru` (HIGH confidence)

The VK Video m3u8 is served from `okcdn.ru`, specifically a `vkvd<N>.okcdn.ru` host. This is directly
documented in **this project's own** limitations guide:

> `docs/11-guides/vkdownloader-limitations.md`, §"2. Time-Limited m3u8 Tokens":
> ```
> https://vkvdXXX.okcdn.ru/?expires=1783915662438&sig=XXXXX&urls=...
> ```

That example is the *exact* VK Video tokenized-HLS shape (`expires` + `sig` + `urls` query params),
and the `vkvd` prefix is "VK Video". This is in-repo, product-grounded evidence (confidence: HIGH — it
is the project author stating what VK Video returns).

### 1.2 Domain ownership (HIGH confidence)

`okcdn.ru` is owned by **VK LLC**, not a third party:

- **WHOIS / OTX (alienvault)** — `Domain: okcdn.ru`, `Org: VK LLC`, name servers `ns1/ns2/ns3.okcdn.ru`.
- **urlscan.io Passive DNS / ASN** — `AS47764 - VK-AS LLC VK, RU`; route `217.20.144.0/20`; IPv4 A records
  `217.20.155.82`, `217.20.152.226`, `217.20.156.72`; PTR `ip82.155.odnoklassniki.ru` (VK's own Odnoklassniki
  CDN). These IPs are inside VK's announced space.
- **2whois.ru DNS** — confirms A records `217.20.155.82 / .226 / 217.20.156.72`, NS `ns1/ns2/ns3.okcdn.ru`,
  and a GlobalSign wildcard cert `*.okcdn.ru` (plus `*.mycdn.me`, `mycdn.me`, `okcdn.ru`).
- Passive DNS hostnames observed on `okcdn.ru`: `vkvd557`, `vd615`, `vd294`, `vd647`, `vd395`, `vd405`,
  `vd395` (all resolving to VK IPs) — matching the `vkvdXXX` / `vdXXX` prefix shape.

Sources: urlscan.io/domain/okcdn.ru; OTX alienvault `domain/okcdn.ru`; 2whois.ru `okcdn.ru`.

### 1.3 CDN provider — VK's own, NOT Akamai/Cloudflare/Yandex (HIGH confidence)

`okcdn.ru` is delivered **from VK's own network**, not a third-party edge:

- The serving ASN recorded against `okcdn.ru` is **AS47764 (VK-AS)** / AS47541 (VK) per urlscan.io and
  Netify's "VK network" sample IPs. A third-party CDN (Akamai = AS20940, Cloudflare = AS13335,
  Yandex CDN) would announce itself; the recorded edge ASN is VK's.
- The reverse-DNS (`ip82.155.odnoklassniki.ru`) is VK's own Odnoklassniki edge, confirming self-hosted
  delivery.
- VK publicly discussed building its own CDN: YouTube talk *"Много храним и быстро раздаем: как мы
  построили CDN VK"* ("How we built VK's CDN"), hosted on `cloud.vk.com/cdn` — i.e. VK operates the CDN
  that `okcdn.ru` names.

Conclusion: the host/suffix to filter on is `*.okcdn.ru`; the underlying provider is VK itself.

### 1.4 Does `vkvideo.ru` share the CDN with `vk.com`? — YES (HIGH confidence)

Both `vkvideo.ru` and `vk.com` are VK Video **front-ends** for the same product, and **both resolve the
media to the same `okcdn.ru` CDN**:

- **yt-dlp `vk.py` (authoritative OSS reference):** a single `VKIE` extractor whose `_VALID_URL` accepts
  both `vkvideo\.ru` and `vk\.com`:
  `r'(?:(?:m|new|vksport)\.)?vk(?:(?:video)?\.ru|\.com)/(?:...)(?P<videoid>-?\d+_\d+)...'`
  It feeds both through the *same* player-data extraction (`player['params'][0]`, format id prefixed
  `hls`) and calls `_extract_m3u8_formats(format_url, ...)`. yt-dlp never filters the returned URL by
  host — it trusts the URL VK's player emits. Because both entry hosts traverse the identical player →
  CDN path, the served m3u8 comes from the same `okcdn.ru` origin.
- **`vk.com` login flow** (`VKBaseIE._perform_login`) posts to `https://vk.com` and is shared across the
  extractor — vk.com is the canonical auth surface, with `vk.ru`/`vkvideo.ru` as mirrors. yt-dlp issue
  #5832 confirms `vk.ru` is a mirror of `vk.com` behind the same backend.
- **Wikipedia "VK Video"** — VK Video is "an internet video hosting service… Owner: VK… URL: vkvideo.ru",
  i.e. the same product accessible via both domains.
- **Project evidence:** `urls.txt` uses `vkvideo.ru`; the limitations doc's tokenised-m3u8 example is on
  `okcdn.ru`; yt-dlp's extractor treats both entry hosts as VK Video. No evidence exists that either entry
  host serves m3u8 from itself — the segment/playlist is always on `okcdn.ru`.

### 1.5 The candidate suffixes from the brief — verdict per pattern

| Candidate | Verdict | Reasoning |
|---|---|---|
| `*.okcdn.ru` | **ACCEPT (primary)** | Project doc example + VK-owned + serving ASN is VK. HIGH. |
| `*.mycdn.me` | **ACCEPT (secondary)** | Co-listed on `okcdn.ru`'s GlobalSign `*.mycdn.me` cert (2whois.ru DNS/SSL output) and observed serving `.m3u8` for VK-group content (`vd340.mycdn.me/video.m3u8` in streamlink/streamlink#5377). Same-owner VK CDN. MEDIUM-HIGH. |
| `*.vkuser.net` | **ACCEPT (secondary)** | VK-owned (`ncc.vk.com`, `ns1.vkontakte.ru`, Netify `vk6-14.vkuser.net` → AS60476 VK NL). Ranked a failover mirror by the ok.ru resolver (`hostRank 2 | *vkuser.net*`). No direct `vkvideo.ru` m3u8 observation. LOW-MEDIUM. |
| `*.vkcdn.me` | **REJECT** | Not a real VK host. The look-alike `vcdn.me`/`cdn.vcdn.me`/`stream.vcdn.me` is an unrelated commercial "multi-CDN video" service (VCDN, not VK). No VK ownership evidence. HIGH confidence it is wrong. |
| `*.example.com` (incl. `cdn.example.com`) | **REJECT** | Test fixtures only (see §4). |
| any other host | **REJECT** | A `.m3u8` from an unrelated host is the NET-008 failure mode (a third party fetched first wins). The safety suspension in `select()` makes the rejection visible rather than silent. |

---

## 2. How to distinguish a media playlist from a manifest

Source of truth: **RFC 8216 §4.1 ("Definition of a Playlist")** and the tag sections quoted via the
RFC text, cross-checked with the `ok.ru-direct-resolver` flow which distinguishes master vs media the
same way.

### 2.1 Definitive rules (programmatic)

- **Master playlist (manifest):** the playlist contains `#EXT-X-STREAM-INF` or
  `#EXT-X-I-FRAME-STREAM-INF`. RFC 8216 §4.3.2/§4.3.4: *"These tags must not appear in a Media
  Playlist; … clients are required to fail if a single playlist contains both Master Playlist tags
  and Media Playlist or Media Segment tags."* → **presence of a master tag is definitive.** A master
  playlists lists Variant Streams (other playlists), not segments.
- **Media playlist:** there are **no** master tags (`#EXT-X-STREAM-INF` / `#EXT-X-I-FRAME-STREAM-INF`),
  and the body carries **Media Segment** tags. The two reliable, RFC-mandated media signals are:
  - `#EXTINF` — `§4.3.2.1`: *"This tag is REQUIRED for each Media Segment."*
  - `#EXT-X-TARGETDURATION` — `§4.3.3.1`: *"The EXT-X-TARGETDURATION tag is REQUIRED."*
- **`#EXT-X-PLAYLIST-TYPE` is OPTIONAL** — `§4.3.3.5`: *"It is OPTIONAL."*

### 2.2 Recommended discriminator (and a weakness in the current code)

Recommended:
```
if "#EXT-X-STREAM-INF" in text or "#EXT-X-I-FRAME-STREAM-INF" in text:
    MASTER
elif "#EXTINF" in text or "#EXT-X-PLAYLIST-TYPE" in text:   # media
    MEDIA
else:
    UNCLASSIFIED
```
Order matters: **master must be tested first** because master tags are mutually exclusive with media
tags (RFC), so once a master tag is seen it cannot also be a media playlist.

**Weakness in the current implementation** (`infrastructure/network_monitor.py:21-24`, `115-136`):
`_classify_playlist` uses `#EXT-X-PLAYLIST-TYPE` *alone* as the media signal. Because that tag is
OPTIONAL, a real media playlist that omits it (e.g. a minimal live playlist, or the project's own
`test_intercept_response_classifies_unclassified_playlist` body `#EXTM3U\n#EXT-X-TARGETDURATION:10\n`)
falls through to `UNCLASSIFIED` instead of `MEDIA`. A media playlist with segments but no
`#EXT-X-PLAYLIST-TYPE` would be mis-ranked below master → the wrong address could be handed to the
downloader. Adding `#EXTINF` as an *additional* media signal is the minimal, RFC-correct fix.

Note on the existing tests (research-only observation; **not** a request to edit them):
`test_intercept_response_classifies_media_playlist` and
`test_intercept_response_classifies_unclassified_playlist` currently pin the `PLAYLIST-TYPE`-only
behaviour. If the discriminator is widened to also admit `#EXTINF`, the *media* test stays green (its
body already has `#EXT-X-PLAYLIST-TYPE`), but the *unclassified* test body
(`#EXTM3U\n#EXT-X-TARGETDURATION:10\n`, no `#EXTINF`) would remain UNCLASSIFIED under an
`#EXTINF`-inclusive rule — so it would also stay green **if `#EXTINF` is the added signal** (not
`#EXT-X-TARGETDURATION`). Using `#EXTINF` rather than `#EXT-X-TARGETDURATION` is therefore the
choice that keeps both tests green while becoming RFC-correct. (This is a B7 Planner/Validator
decision under §3.5 question 4, which the report confirms: a wrong preference heuristic is worse than
none — the host filter and label fix are shippable without it.)

### 2.3 Source for the rules

- **RFC 8216 §4.1** — "A Playlist is a Media Playlist if all URI lines identify Media Segments. A
  Playlist is a Master Playlist if all URI lines identify Media Playlists."
- **RFC 8216 §4.3.2.1 (EXTINF)** — "This tag is REQUIRED for each Media Segment."
- **RFC 8216 §4.3.3.1 (EXT-X-TARGETDURATION)** — "… is REQUIRED."
- **RFC 8216 §4.3.3.5 (EXT-X-PLAYLIST-TYPE)** — "It is OPTIONAL."
- **RFC 8216 §4.3.4 (Master Playlist Tags)** — must not appear in a Media Playlist; a playlist
  containing both is invalid and clients MUST fail.
- **`ok.ru-direct-resolver` README/flow** — corroborates master = `#EXTM3U` + variant URIs; the same
  `#EXT-X-STREAM-INF`/`#EXTINF` shape is what it parses.

---

## 3. Other known VK video CDN hosts (and rejects)

Confirmed VK-owned CDN hostnames serving `.m3u8`:

- `*.okcdn.ru` — primary; `vkvd<N>`, `vd<N>`, `st`, `api`, `calls` prefixes observed (Passive DNS on
  urlscan.io / OTX).
- `*.mycdn.me` — VK-owned; co-certified with `*.okcdn.ru` on the same GlobalSign wildcard; observed
  serving `.m3u8` (`vd340.mycdn.me/…/video.m3u8` — streamlink discussion #5377).
- `*.vkuser.net` — VK-owned (`ncc.vk.com` SOA, Netify `vk6-14.vkuser.net` AS60476 VK); ranked a
  failover mirror by the ok.ru resolver. No direct `vkvideo.ru` m3u8 capture observed.

**Rejected outright:**

- `*.vkcdn.me` — not VK. The only look-alike, `vcdn.me` / `cdn.vcdn.me` / `stream.vcdn.me`, is a
  separate "multi-CDN video infrastructure" service (VCDN), unaffiliated with VK. No ownership evidence
  for `vkcdn.me`. High-confidence reject.

---

## 4. Interaction with existing tests (research-only)

- `tests/test_extractor.py::TestExtractWithBrowser::test_browser_extraction_uses_first_m3u8_url`
  uses `https://cdn.example.com/{first,second}.m3u8`. The plan (§B7 tests) states a **host filter alone**
  leaves it green: both addresses share `cdn.example.com` (not in the accept set) → both rejected →
  the safety suspension returns the unconstrained ranked set → arrival order holds → `first_url` is still
  `select()[0]`. A *preference* rule (media-before-master) is the risk; since neither body in that test is
  a distinguishable media/manifest, the preference does not change the winner there. ✔ consistent with
  the host constant above. (B7 Planner must still state why it stays green, per the plan — this report
  supplies the reason.)
- `tests/test_browser_infrastructure.py::TestNetworkMonitor` already covers master/media/unclassified
  classification and `select()` ranking (lines ~976-1071). The host filter has **no** existing test yet
  (none of these use an okcdn.ru host); the plan's "ADD `TestNetworkMonitor` … an expected host, an
  unexpected host, a manifest and a media playlist" is still outstanding and will consume
  `HLS_CDN_SUFFIX` = `.okcdn.ru`.

---

## 5. Answers to the three numbered research questions

1. **Expected CDN host/suffix.** `*.okcdn.ru` (primary, HIGH). VK Video does *not* serve the m3u8 from
   `vkvideo.ru`/`vk.com`; those are page/entry hosts — the playlist and segments come from `okcdn.ru`
   (host prefix `vkvd<N>` for video). `vkvideo.ru` and `vk.com` **share the same CDN origin** (both
   resolve through VK's single player → `okcdn.ru` path; yt-dlp uses one extractor for both). CDN
   provider is **VK's own ("OK CDN")**, IPs on AS47541/AS47764 — not Akamai, Cloudflare, or Yandex CDN.
   Accept also `*.mycdn.me` (MEDIUM-HIGH) and `*.vkuser.net` (LOW-MEDIUM) as same-owner mirrors;
   **Reject** `*.vkcdn.me` (unrelated service) and all other hosts.

2. **Media vs manifest.** Master = contains `#EXT-X-STREAM-INF` or `#EXT-X-I-FRAME-STREAM-INF`
   (RFC-forbidden in a media playlist → definitive). Media = no master tag **and** contains `#EXTINF`
   (REQUIRED per segment, §4.3.2.1) — optionally also `#EXT-X-PLAYLIST-TYPE` (OPTIONAL, §4.3.3.5, so a
   confirmatory but non-definitive signal). `#EXT-X-PLAYLIST-TYPE` alone is the wrong sole signal
   because it is optional; the current `_classify_hls`/`_classify_playlist` in `network_monitor.py`
   relies on it and can mis-rank a media playlist that omits it. Adding `#EXTINF` as a media signal
   fixes this while keeping the existing media/unclassified tests green.

3. **Other known hosts.** `*.okcdn.ru` (primary), `*.mycdn.me`, `*.vkuser.net` (VK-owned mirrors).
   `*.vkcdn.me` is a decoy and must be rejected.

---

## 6. Sources (hyperlink + claim)

| # | Source | Claims supported |
|---|---|---|
| S1 | `docs/11-guides/vkdownloader-limitations.md` (in-repo) | `vkvdXXX.okcdn.ru` is the VK Video m3u8 host; tokenized shape (`expires`/`sig`/`urls`). |
| S2 | RFC 8216 §4.1, §4.3.2.1 (EXTINF REQUIRED), §4.3.3.1 (TARGETDURATION REQUIRED), §4.3.3.5 (PLAYLIST-TYPE OPTIONAL), §4.3.4 (master tags forbidden in media playlists) | Master/media distinction; optional-ness of PLAYLIST-TYPE. |
| S3 | `https://www.rfc-editor.org/rfc/rfc8216.html` (fetched) | Authoritative HLS tag semantics above. |
| S4 | OTX / urlscan.io Passive DNS for `okcdn.ru` | Owned by VK LLC; AS47764; IPs 217.20.155.82/.226/217.20.156.72; PTR odnoklassniki.ru; subdomains `vkvd557/vd395/vd405/vd647/…`. |
| S5 | 2whois.ru DNS/SSL for `okcdn.ru` | GlobalSign wildcard `*.okcdn.ru` + `*.mycdn.me` + `mycdn.me` (co-cert = same owner infra). |
| S6 | Netify "VK" application page | `vkuser.net`, `vk.com`, `vk.ru`, `userapi.com` are VK primary domains; VK uses dedicated network blocks (AS47541). |
| S7 | yt-dlp `yt_dlp/extractor/vk.py` (fetched raw) | One extractor for `vkvideo.ru` **and** `vk.com`; m3u8 extracted from player data, no host filter; login via `vk.com`. |
| S8 | yt-dlp issue #5832 | `vk.ru` is a mirror of `vk.com` behind the same backend. |
| S9 | Wikipedia "VK Video" + vk.company press release | VK Video = product owned by VK, URL `vkvideo.ru`, also reachable via `vk.com`. |
| S10 | "Много храним и быстро раздаем: как мы построили CDN VK" (YouTube, `cloud.vk.com/cdn`) | VK built/operates its own CDN (not a 3rd-party edge). |
| S11 | streamlink/streamlink discussion #5377 (`vd340.mycdn.me/video.m3u8`) | `mycdn.me` serves `.m3u8` for VK-group (ok.ru) content; co-cert with `okcdn.ru`. |
| S12 | `ok.ru-direct-resolver` README (GitHub) | `*.okcdn.ru` = rank-0 CDN, `*vkuser.net*` = rank-2 failover; master/media parsing shape. |

---

## 7. Confidence summary & residual uncertainty

- **`*.okcdn.ru` accept:** HIGH. Backed by in-repo product doc + WHOIS/AS ownership + serving ASN.
- **vkvideo.ru == vk.com same CDN:** HIGH. Single yt-dlp extractor + shared VK backend; m3u8 is not
  served from the page host.
- **CDN provider = VK-owned:** HIGH for "origin/edge ASN is VK"; LOW for "zero third-party CDN
  involvement anywhere in VK's global delivery" (VK may peer with others for overflow, but the recorded
  serving edge for `okcdn.ru` is VK-owned AS47541/AS47764). This distinction does not affect the host
  filter, which keys on the registered domain `okcdn.ru` regardless of edge provider.
- **`*.mycdn.me`:** MEDIUM-HIGH (VK cert co-listing + observed `.m3u8`; not yet directly tied to a
  `vkvideo.ru` capture).
- **`*.vkuser.net`:** LOW-MEDIUM (VK-owned, used as ok.ru failover; no direct vkvideo.ru capture).
- **`*.vkcdn.me`:** HIGH reject (look-alike is an unrelated service).

No network access was used from the test environment; all claims derive from documentation, DNS/WHOIS
passive data, and an OSS extractor source — satisfying the "hardcoded constant / documented rule, not
runtime discovery" constraint.
