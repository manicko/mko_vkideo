# Phase 02 Audit Findings — Configuration

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/02-audit-config.md`
**Status:** complete
**Validated:** no

**Scope note.** Findings use concrete `file:line` references for traceability, but every
check was reasoned against the phase's role vocabulary (settings model · environment-file
reader used before construction · consuming configuration parser · pre-construction
unknown-variable scan · validation-error renderer · command declaration layer ·
post-construction settings copy · committed example configuration file · settings guide).
Architecture-level conclusions are stated independently of the current file layout.

**Cross-cutting exclusions applied** (§7). Not filed here: credential-material lifetime and
redaction (`06`); permission mode / atomicity / cleanup of the log file the settings create,
including the `0o600` access mode (R-S1 documented skip, `07`/`06`); the runtime effect of a
concurrency bound (`04`); composition of the timeout budget and the hardcoded constants a
consumer substitutes beside a timeout setting (`03`); the command-line option contract and
the drift between the two commands' option sets (`08`); secret scanning, ignore-file coverage
and whether a real environment file is tracked (`11`); structural documentation claims
(`09`); dangling source references to finding IDs `CFG-001`/`CFG-002` that no catalogue
contains (`99`).

**Documented skips.**

| ID | Skip | Justification |
|---|---|---|
| R-S1 | Effective access mode of the log file the settings create | The declared development platform does not enforce a POSIX access mode, so no observation distinguishes a correct mode from a wrong one. Belongs to `07`/`06`. Recorded as a skip, not a clean result. |
| R-S2 | Effect of a substituted or admitted range value against a live third-party origin | Requires the live origin, which this phase must not require. R4's stubbed-transport value assembly is the substitute. Every finding depending on it carries an explicit `UNVERIFIED` marker. |

**Baselines (R10, R11) — the state the rest was observed against, not findings.**

```
$ uv run ruff check src/vkdownloader/config.py src/vkdownloader/cli.py
All checks passed!                                    EXIT=0
$ uv run ruff format --check src/vkdownloader/config.py src/vkdownloader/cli.py
2 files already formatted                             EXIT=0
$ uv run mypy src/vkdownloader/config.py src/vkdownloader/cli.py
Success: no issues found in 2 source files            EXIT=0
$ uv run pytest tests/test_config.py -q
29 passed, 2 skipped in 0.85s                        EXIT=0
```

---

## Findings

### CFG-001: Two documented settings have a source that can never reach them — the entry layer's default option values unconditionally replace the user's

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py`, `.env.example`, `docs/11-guides/configuration.md` |
| **Classification** | mandatory |

**Description:** The settings model documents four configuration sources resolved in priority
order (constructor keyword arguments → `VKDOWNLOADER_*` process environment variables → `.env`
file in the current working directory → field defaults), at
`src/vkdownloader/config.py:20-24`. R5 confirms that order is truthful in isolation
(init kwargs beat `os.environ`; `os.environ` beats `.env`; `.env` beats defaults).

The defect is that both entry points never let the second and third sources compete for two
settings. `src/vkdownloader/cli.py:127` and `src/vkdownloader/cli.py:239` both construct the
model as:

```python
settings = Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)
```

`cookie_source` and `ssl_verify` are declared as non-optional command-line options whose
Typer defaults are `CookieSource.NONE` and `True` (`cli.py:71-81`, `cli.py:209-219`), never
`None`. So a keyword argument is *always* passed, and by the documented precedence it *always*
wins. `VKDOWNLOADER_SSL_VERIFY` and `VKDOWNLOADER_COOKIE_SOURCE` — in `.env` or in the process
environment — can never be observed at the field. `.env.example:22` and `.env.example:32`
document both variables, and `docs/11-guides/configuration.md:31` and `:36` document them as
ordinary settings.

**Evidence — R1.** Declared-setting inventory (16 fields). `ssl_verify` and `cookie_source` do
have production read sites (`src/vkdownloader/services/segment_downloader.py:536`,
`src/vkdownloader/services/downloader.py:571`, `src/vkdownloader/services/ytdlp_downloader.py:298,611,753`,
`src/vkdownloader/services/extractor.py:167,197`), so a consumer trace alone would read as
healthy. The phase's rule applies: *reachability of each source is the test, and R5 is where it
is obtained.*

**Evidence — R5, per-field diff against a `.env` setting all 16 fields.** A file setting every
field to a value distinguishable from its default:

| Run | Setup | Result |
|---|---|---|
| (a) | `.env` in the working directory | all 16 fields match the file |
| (b) | empty working directory, no file | all 16 fall back to defaults |
| (c) | same values in `os.environ`, file absent | all 16 match |
| (d) | **`.env` present, `Settings(cookie_source="none", ssl_verify=True)`** | `cookie_source` holds `CookieSource.NONE` where the file says `browser`; `ssl_verify` holds `True` where the file says `false` |

**Evidence — R5, through the process's own command-line entry point, with a controlled
positive control.** Fixture `.env` in a temporary working directory:

```
# positive control — the file IS read for non-shadowed fields
$ VKDOWNLOADER_MAX_RETRIES=not-an-int
$ uv run vkdownloader download not-a-valid-url        (stderr)
Configuration error: one or more settings have invalid values.
  - max_retries: Input should be a valid integer, unable to parse string as an integer
EXIT=1

# subject — the two shadowed fields
$ VKDOWNLOADER_SSL_VERIFY=not-a-bool
$ VKDOWNLOADER_COOKIE_SOURCE=file
$ uv run vkdownloader download not-a-valid-url        (stderr)
Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}
EXIT=1
```

No configuration error is raised. The two invalid values are not rejected because they are
never parsed — proving the `.env` never reaches those two fields, while the positive control
proves the same file *is* reaching the model for every other field. Reproduced identically on
the second entry point (`uv run vkdownloader batch urls.txt`): the same two invalid values
produced no configuration error and the process ran on to a real network attempt.

**Exact consequence.** A user behind a CDN or corporate proxy with a broken certificate chain
writes `VKDOWNLOADER_SSL_VERIFY=false` into `.env`, as `.env.example:22` and
`docs/11-guides/configuration.md:31` instruct. The model holds `True`; the TLS handshake fails
and the download dies with a certificate error, with no indication in any output that the
setting was read and discarded. A user who needs an authenticated video writes
`VKDOWNLOADER_COOKIE_SOURCE=browser`; the model holds `NONE`, browser cookie resolution is
skipped at `src/vkdownloader/services/extractor.py:167`, and the run ends with
"No streams found; the video may be private or unavailable" — a message that points at the
video's visibility rather than at the ignored setting. Nothing is printed, logged, or warned:
the discarded value is indistinguishable from never having been written. The discarding itself
is observed above; the effect on a real transfer is **UNVERIFIED** (R-S2).

**Phase-seam note (§7).** The finding survives replacing the entry point with a direct
`Settings(cookie_source=..., ssl_verify=...)` call — run (d) *is* that call, made with the file
present — so it is a defect of the construction pattern, not of the option surface. `08` may
cross-reference; per §7 it must not file it.

**Recommendation:** Stop making the option defaults outrank the configured sources. Default the
two options to `None` at the command-declaration layer and pass them through only when the
user actually supplied one, so an unsupplied option no longer occupies the highest-priority
source:

```python
ssl_verify: bool | None = typer.Option(None, "--ssl-verify/--no-ssl-verify", ...)
...
overrides: dict[str, object] = {}
if ssl_verify is not None:
    overrides["ssl_verify"] = ssl_verify
if cookie_source is not None:
    overrides["cookie_source"] = cookie_source
settings = Settings(**overrides)
```

Apply the same shape to both entry points. If the option defaults must stay as they are for
help-text purposes, the equivalent fix is to construct the model first and apply
`model_construct`-free, *re-validated* overrides only for options the user actually typed.
Whichever shape is chosen, the settings model cannot distinguish "not supplied" from
"supplied with its default value" today, which is the root cause.

---

### CFG-002: The post-construction `max_retries` override bypasses the declared range and type, and the admitted values reach the consumer

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/config.py`, `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |

**Description:** `max_retries` is declared `int`, `ge=1`, `le=10`
(`src/vkdownloader/config.py:55-60`). R3 confirms the bound is enforced exactly as declared on
the construction path: floor-1 `0` → `greater_than_equal` rejection, `1` → accept, `10` →
accept, ceiling+1 `11` → `less_than_equal` rejection, default `3` inside the range. All seven
bounded fields behaved the same way, and no declared default falls outside its own range.

The declared bound is then discarded one function later.
`src/vkdownloader/services/downloader.py:652-653`:

```python
if max_retries_override is not None:
    settings = settings.model_copy(update={"max_retries": max_retries_override})
```

Pydantic's `model_copy(update=...)` copies the field table verbatim and performs **no**
validation — it is the documented fast path for skipping re-validation. The copy becomes the
live settings object for the rest of the run and is passed straight into the extractor
(`downloader.py:667`), the segment policy
(`src/vkdownloader/services/segment_downloader.py:805,832`) and the yt-dlp command builder
(`src/vkdownloader/services/ytdlp_downloader.py:277,279`).

**Evidence — R6, override read-back matrix.** Production's baseline `max_retries` is `3`:

| Value passed to `model_copy(update=...)` | Live object holds | Type | Inside declared 1-10? |
|---|---|---|---|
| `0` | `0` | `int` | no |
| `-5` | `-5` | `int` | no |
| `11` | `11` | `int` | no |
| `100000` | `100000` | `int` | no |
| `'5'` | `'5'` | **`str`** | type violation |
| `3.7` | `3.7` | **`float`** | type violation |
| `None` | `None` | **`NoneType`** | type violation |

Every one is accepted with no exception raised.

**Evidence — R6, the values actually observed at the consumer's read site.** A recording stub
substituted at the extractor's construction — the first consumer of the copied object, reached
from `download_video` after the copy at `downloader.py:667`:

```
download_video(max_retries_override=0)   -> consumer received max_retries=0
download_video(max_retries_override=11)  -> consumer received max_retries=11
download_video(max_retries_override=-3)  -> consumer received max_retries=-3
```

**Evidence — R6, what the consumer does with them.** The retry budget is read at
`src/vkdownloader/services/ytdlp_downloader.py:367` as
`while retry_count <= settings.max_retries:` with `retry_count` starting at `0`. Evaluated with
a stubbed transport, no origin contacted:

| Admitted value | Consumer behaviour |
|---|---|
| `0` | loop entered once, 1 attempt |
| `-3` | **loop body never executes — 0 download attempts** |
| `11` | 12 attempts |
| `'5'` | `TypeError: '<=' not supported between instances of 'int' and 'str'` |
| `3.7` | 4 attempts |
| `None` | `TypeError: '<=' not supported between instances of 'int' and 'NoneType'` |

**Exact consequence.** A user passes `--max-retries -3`, or any non-positive value.
`max_retries` becomes `-3`, the `while` condition is false at `retry_count == 0`, the loop body
at `ytdlp_downloader.py:368-434` never runs, and control falls straight through to
`ytdlp_downloader.py:436-447`, which logs `max_retries_exceeded` and returns `None`. The
application reports a failed download having never issued a single request — and the log line
reads `retries=-3`, blaming the origin for a transfer that was never attempted. A value of the
wrong type (`'5'`, `None`) is worse: it is not a validation failure but an unhandled
`TypeError` on the first comparison, which `src/vkdownloader/cli.py:180-183` catches only as a
bare "An error occurred during download".

**Phase-seam note (§7).** The override arrives as a programmatic argument, so the finding
survives replacing the command-line entry point with a direct
`download_video(..., max_retries_override=-3)` call — which is exactly how the R6 probe invoked
it. `CFG-`, not `08`. The declared option contract (`08`) may cross-reference.

**R11 baseline.** `tests/test_config.py` passes in full (29 passed, 2 skipped) and contains no
test that applies the post-construction override, so the bound bypass is exercised by no test
in the configuration suite.

**Recommendation:** Re-validate the override instead of copying it unchecked, so the bound
continues to live in exactly one place:

```python
if max_retries_override is not None:
    settings = Settings.model_validate(
        {**settings.model_dump(), "max_retries": max_retries_override}
    )
```

This reuses the field's own `ge`/`le` and its declared type, so a future change to the range
needs no second edit. A `ValidationError` then surfaces through the existing handler at
`cli.py:139-141` with the redacted rendering already in place, instead of escaping as a
`TypeError` or as a silent no-op download.

---

### CFG-003: The "did you mean" renderer compares a prefixed, lower-cased key against bare field names, so 11 of 19 realistic misspellings get a wrong suggestion

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** The validation-error renderer builds its candidate set from the model's
*field names* and matches the error's `loc` against it
(`src/vkdownloader/config.py:220,229-235`):

```python
valid_field_names = sorted(Settings.model_fields.keys())      # -> "max_retries", "log_level", ...
...
if error_type == "extra_forbidden" and loc:
    close = difflib.get_close_matches(loc, valid_field_names, n=1, cutoff=0.3)
```

Those two are in different namespaces whenever the offending key came from the environment
file. With `case_sensitive=False`, pydantic-settings reports the `extra_forbidden` `loc` as the
**lower-cased, prefix-stripped-then-re-added** key: `vkdownloader_maxretries`, not
`max_retries` and not `VKDOWNLOADER_MAXRETRIES`. Fuzzy-matching that 25-character string against
12-character field names at `cutoff=0.3` produces a confident wrong answer rather than no
answer. The code's own comment at `config.py:228` names the exact case that fails —
`VKDOWNLOADER_MAXRETRIES -> MAX_RETRIES` — and that case is the one that fails.

**Evidence — R2, rendered message for an unrecognised key in the environment file.**

```
Configuration error: one or more settings have invalid values.
Check your .env file or VKDOWNLOADER_* environment variables:
  - vkdownloader_maxretries: Extra inputs are not permitted
    Did you mean: VKDOWNLOADER_DOWNLOAD_TIMEOUT? (check for typos)
    Received: <redacted>
Fix the offending value(s) and try again.
```

Two defects on four lines: the suggestion names a setting unrelated to the typo, and the `loc`
echoes `vkdownloader_maxretries` rather than the `VKDOWNLOADER_MAXRETRIES` the user actually
typed.

**Evidence — R8, 19 plausible misspellings through the real environment-file path.**

| Offending key in `.env` | Suggested | Correct? |
|---|---|---|
| `VKDOWNLOADER_MAXRETRIES` | `VKDOWNLOADER_DOWNLOAD_TIMEOUT` | **wrong** |
| `VKDOWNLOADER_MAX_RETRY` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_MAX_RETREIS` | `VKDOWNLOADER_MAX_RETRIES` | correct |
| `VKDOWNLOADER_DOWNLAOD_TIMEOUT` | `VKDOWNLOADER_DOWNLOAD_TIMEOUT` | correct |
| `VKDOWNLOADER_SSL_VERFY` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_LOG_LVL` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_COOKIE_SORCE` | `VKDOWNLOADER_COOKIE_SOURCE` | correct |
| `VKDOWNLOADER_HEADLES` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_THROTTLEDRATE` | `VKDOWNLOADER_THROTTLED_RATE` | correct |
| `VKDOWNLOADER_HTTP_CHUNKSIZE` | `VKDOWNLOADER_HTTP_CHUNK_SIZE` | correct |
| `VKDOWNLOADER_DOWNLOAD_DIRR` | `VKDOWNLOADER_DOWNLOAD_DIR` | correct |
| `VKDOWNLOADER_USERAGENT` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_TIMEZONEE` | `VKDOWNLOADER_DOWNLOAD_TIMEOUT` | **wrong** |
| `VKDOWNLOADER_LOCALE_` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_MAX_CONCURENT_DOWNLOADS` | `VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS` | correct |
| `VKDOWNLOADER_LOGIN` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_XYZ` | `VKDOWNLOADER_DOWNLOAD_DIR` | **wrong** |
| `VKDOWNLOADER_MAX_CONCURENT` | `VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS` | correct |

**11 of 19 wrong.** The two most frequent wrong answers, `VKDOWNLOADER_DOWNLOAD_DIR` (7 of 19)
and `VKDOWNLOADER_DOWNLOAD_TIMEOUT` (3 of 19), are simply the longest field names — exactly
what a `cutoff=0.3` ratio rewards when the two strings share little. A further 4 wrong answers
are for keys with no plausible intent at all (`VKDOWNLOADER_LOGIN`, `VKDOWNLOADER_`,
`VKDOWNLOADER_XYZ`), where the honest answer is "no close match, here are the valid names".

**Exact consequence.** A user who mistypes `VKDOWNLOADER_MAXRETRIES` is told to use
`VKDOWNLOADER_DOWNLOAD_TIMEOUT`. They set it, restart, and get a fresh `extra_forbidden` for a
setting they never meant to touch; the cycle points at timeout configuration instead of at the
one-character omission in their own file. `VKDOWNLOADER_SSL_VERFY` is redirected to
`VKDOWNLOADER_DOWNLOAD_DIR`, which is worse still because it names a path setting — the user
edits a directory and the error is unchanged. A user who writes `VKDOWNLOADER_` or
`VKDOWNLOADER_XYZ` is given a confident wrong pointer where the full valid-name list (already
implemented at `config.py:235`) was the correct output.

**R11 baseline.** `tests/test_config.py:304-312` asserts only
`"Did you mean" in formatted or "Valid fields" in formatted`. That assertion cannot fail when
the suggested name is wrong, so the defect is not caught by the existing suite.

**Recommendation:** Match in one namespace. Normalise the `loc` to the environment-variable
name before matching, and match against the full variable names the process accepts:

```python
if error_type == "extra_forbidden" and loc:
    bare = loc.split("_", 2)[-1] if loc.lower().startswith(_ENV_VAR_PREFIX.lower()) else loc
    close = difflib.get_close_matches(
        _ENV_VAR_PREFIX + bare.upper(), _build_valid_env_vars(), n=1, cutoff=0.6
    )
```

Two changes matter: strip the prefix the model added so the same namespace is used on both
sides, and raise `cutoff` from `0.3` to roughly `0.6` so an unrelated long name can no longer
out-score a genuine near-match. Keep the existing "print the full valid-name list" branch for
the no-match case — it already does the right thing. Separately, render the `loc` in the case
the user typed it, so the error names `VKDOWNLOADER_MAXRETRIES` rather than
`vkdownloader_maxretries`.

---

### CFG-004: The pre-construction typo guard misses three assignment forms the consuming parser accepts

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** Two parsers read the same environment file. The pre-construction
unknown-variable scan (`src/vkdownloader/config.py:247-275`) exists to warn about a typo
*before* construction crashes — the model docstring at `config.py:26-32` and
`docs/11-guides/configuration.md:176-179` both state that this is its purpose. The consuming
parser is `pydantic-settings`, which is more permissive about assignment syntax than the scan
is.

The scan's own docstring at `config.py:250` claims it "Uses the same simple `KEY=VALUE`
semantics as pydantic-settings". It does not. Three divergences were observed.

**Evidence — R7, 13 assignment forms, one fixture file each.** Scanner key/value vs the value
the model actually consumed, with the construction outcome:

| Form in `.env` | Scanner reports | Model consumes | Construction |
|---|---|---|---|
| `VKDOWNLOADER_MAX_RETRIES=9` | key ok, value `9` | `9` | ACCEPTED |
| `export VKDOWNLOADER_MAX_RETRIES=9` | key **`export VKDOWNLOADER_MAX_RETRIES`** | `9` | ACCEPTED |
| `VKDOWNLOADER_MAX_RETRIES=9 # bumped to 9` | key ok, value **`9 # bumped to 9`** | **`9`** | ACCEPTED |
| `VKDOWNLOADER_MAX_RETRIES="9"` / `'9'` | key ok, value `9` | `9` | ACCEPTED |
| `VKDOWNLOADER_MAX_RETRIES=$UNSET_VARIABLE` | key ok, value `$UNSET_VARIABLE` | not expanded | REJECTED `int_parsing` |
| `VKDOWNLOADER_MAX_RETRIES=${UNSET_VARIABLE}` | key ok, value `${UNSET_VARIABLE}` | not expanded | REJECTED `int_parsing` |
| `   VKDOWNLOADER_MAX_RETRIES   =   9   ` | key ok, value `9` | `9` | ACCEPTED |
| `VKDOWNLOADER_TIMEZONE=America/New York` | key ok, value `America/New York` | `America/New York` | ACCEPTED |
| `VKDOWNLOADER_MAX_RETRIES` (no `=`) | nothing | default | ACCEPTED |
| `vkdownloader_max_retries=9` | key ok (lower case) | `9` | ACCEPTED |
| `VKDOWNLOADER_MAX_RETRIES=` | key ok, value `''` | rejected | REJECTED `int_parsing` |

**Evidence — R7b, six misspelled keys — the pre-flight guard's actual target.** The guard fires
only when the scanner's key both starts with `VKDOWNLOADER_` (case-sensitive test at
`config.py:309`) and is not a declared field:

| Misspelled line in `.env` | Scanner key | Pre-flight warning? | Model outcome |
|---|---|---|---|
| `VKDOWNLOADER_MAXRETRIES=9` | `VKDOWNLOADER_MAXRETRIES` | **YES** | REJECTED |
| `VKDOWNLOADER_MAXRETRIES=9` (leading spaces) | `VKDOWNLOADER_MAXRETRIES` | **YES** | REJECTED |
| `VKDOWNLOADER_MAXRETRIES=9  # oops` | `VKDOWNLOADER_MAXRETRIES` | **YES** | REJECTED |
| `export VKDOWNLOADER_MAXRETRIES=9` | `export VKDOWNLOADER_MAXRETRIES` | **no** | REJECTED |
| `vkdownloader_maxretries=9` | `vkdownloader_maxretries` | **no** | REJECTED |
| `"VKDOWNLOADER_MAXRETRIES"=9` | `"VKDOWNLOADER_MAXRETRIES"` | **no** | REJECTED |

**Exact consequence.** Three assignment forms that the consuming parser accepts, and that a
user arriving from a shell would naturally write, defeat the guard completely. A user who
exports their variables — `export VKDOWNLOADER_MAXRETRIES=9` in `.env`, a habit shell
familiarity encourages and a form `pydantic-settings` accepts — gets **no warning at all**,
and the process then dies with a bare `Extra inputs are not permitted` that carries no
suggestion, because the suggestion machinery in CFG-003 keys off the `loc` and cannot recover
the user's intent from it. The same holds for an all-lowercase key and for a quoted key. In
all three cases the guard's entire reason for existing — the early, actionable warning the
docs promise at `config.py:26-32` and `docs/11-guides/configuration.md:176-179` — is absent,
and the user gets the crash the guard was written to prevent.

The inline-comment row is a separate divergence: the scan reports
`VKDOWNLOADER_MAX_RETRIES=9 # bumped to 9` as the value `9 # bumped to 9` while the consuming
parser reads `9`. Nothing consumes the scanned value today, so this is latent rather than
active — but it means the scan cannot be reused as a value source without silently changing
behaviour, and it directly falsifies the docstring claim at `config.py:250`.

**R11 baseline.** `tests/test_config.py:267-298` covers the `.env` typo guard with the plain
form only (`VKDOWNLOADER_MAXRETRIES=9`). No test exercises the `export`, lower-case, or
quoted-key forms, nor the inline-comment value divergence.

**Recommendation:** Do not hand-roll a second parser. The pre-construction scan should read the
file the same way the consuming parser does. `python-dotenv` is already installed as a
transitive dependency of `pydantic-settings`, so `dotenv_values()` gives the same keys, the
same quote stripping and the same inline-comment handling, removing all three divergences in
one change:

```python
from dotenv import dotenv_values

def _scan_env_file(env_path: Path = Path(".env")) -> dict[str, str]:
    if not env_path.exists():
        return {}
    return {k: v for k, v in dotenv_values(env_path).items() if v is not None}
```

If a hand-rolled reader must be kept, the minimum is: strip a leading `export` keyword, strip
surrounding quotes from the *key* as well as from the value, compare the prefix
case-insensitively at `config.py:309`, and drop a trailing inline comment. Whichever route is
taken, update the docstring at `config.py:250` so it no longer claims a parity the code does
not have.

---

### CFG-005: The committed example configuration file offers a value the model rejects, and contradicts the installation guide

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.env.example`, `docs/01-tools/installation.md`, `docs/11-guides/configuration.md`, `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** The committed template is validated here as an artifact, like any other. Every
commented assignment was uncommented in isolation into a fixture file and constructed. 15 of
16 are accepted. One is not.

**Evidence — R9, per-line accept/reject for `.env.example`.**

| Line | Assignment | Outcome |
|---|---|---|
| 12-17 | `HEADLESS`, `USER_AGENT`, `TIMEZONE`, `LOCALE`, both interaction waits | ACCEPTED |
| 20-22 | `MAX_RETRIES`, `DOWNLOAD_TIMEOUT`, `SSL_VERIFY` | ACCEPTED |
| 25, 26 | `DOWNLOAD_DIR=~/Downloads/vkdownloader`, `MAX_CONCURRENT_DOWNLOADS` | ACCEPTED |
| **27** | **`VKDOWNLOADER_THROTTLED_RATE=10000`** | **REJECTED — `greater_than_equal`, "Input should be greater than or equal to 50000"** |
| 28 | `HTTP_CHUNK_SIZE=10485760` | ACCEPTED |
| 32 | `COOKIE_SOURCE=none` | ACCEPTED |
| 35, 36 | `LOG_LEVEL`, `LOG_FILE` | ACCEPTED |

The field declares `ge=50000` at `src/vkdownloader/config.py:102`; R3 confirms the floor is
enforced (`49999` → `greater_than_equal` rejection, `50000` → accept). The template's value is
five times below the floor.

**Evidence — R9, the two-way name diff.** Clean: no declared setting is absent from the
artifacts, and no name appears in the artifacts that is not declared. The defect is in a
*value*, not a name.

**Evidence — R9, the settings documents contradict the template and each other.** The same
setting is documented twice with different values:

| Source | Value offered for `VKDOWNLOADER_THROTTLED_RATE` | Legal? |
|---|---|---|
| `.env.example:27` | `10000` | **no** |
| `docs/01-tools/installation.md:131` | `100000` | yes |
| `docs/11-guides/configuration.md:34` | `100000` (stated as the default) | yes — but no range is given |

The installation guide's full 16-line block was validated line by line and every line is
accepted. So the two shipped documents disagree, and only one of them works.

A related documentation gap: the settings guide's reference table gives the declared range for
four of the six bounded fields — `browser_pre_interaction_wait` (1-30),
`browser_post_interaction_wait` (1-30), `max_retries` (1-10), `download_timeout` (30-3600),
`max_concurrent_downloads` (1-16) — but gives **no range at all** for `throttled_rate`
(50000-1000000) or `http_chunk_size` (0-104857600). A user therefore has no way to learn that
`10000` is out of range except by crashing into it.

**Exact consequence.** A user follows the template as instructed at `.env.example:3-4` — copy
it to `.env` and adjust values as needed — and tunes the one setting whose name reads as a
performance knob. The process refuses to start:

```
Configuration error: one or more settings have invalid values.
Check your .env file or VKDOWNLOADER_* environment variables:
  - throttled_rate: Input should be greater than or equal to 50000
    Received: <redacted>
Fix the offending value(s) and try again.
```

The failure occurs before any download is attempted, and the value the template itself
supplied is the cause. Since the template is shipped in the sdist
(`pyproject.toml:65`) and is the documented entry point for configuration, this is a defect
reachable by the first action the documentation asks a user to take.

**Recommendation:** Correct the template value at `.env.example:27` to a legal one —
`VKDOWNLOADER_THROTTLED_RATE=100000`, matching the installation guide and the declared default.
Add the two missing ranges to the reference table in `docs/11-guides/configuration.md:34-35`.
To stop this class of defect recurring, add a test that walks `.env.example` line by line,
uncomments each assignment, and constructs the model — the artifact is committed and shipped,
so it belongs under test the same way any other committed input does. Such a test would have
caught this at commit time with no manual audit.

---

### CFG-006: Configuration diagnostics are emitted on stdout, in a third log format, before the logging system they belong to is configured

| Field | Value |
|-------|-------|
| **ID** | CFG-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** Both entry points call the unknown-variable scan *before* the logging setup
that the scan's own output depends on: `src/vkdownloader/cli.py:125` calls
`warn_unknown_env_vars()`, and only at `cli.py:128` does `setup_logging(settings)` run. The
same ordering appears at `cli.py:237` and `cli.py:240`. The scan emits through
`logger.warning` at `src/vkdownloader/config.py:313-319`, which at that point is structlog's
default configuration, not the one `setup_logging` installs at `config.py:368-382`.

This is the one emission-ordering facet §7 assigns to this phase: *the emission of
configuration diagnostics before the logging system is configured, and the consequence of the
resulting inconsistent output.*

**Evidence — R8, streams captured separately at the process's own entry point.** A fixture
`.env` containing one unrecognised key, run as `uv run vkdownloader download not-a-valid-url`
with `1> out.txt 2> err.txt`:

```
########## STDOUT (out.txt) ##########
2026-09-29 11:30:35 [warning  ] unknown_env_var_ignored        hint='Variable is not a
recognized setting and will be ignored. Check for typos.'
valid_vars=['VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT', 'VKDOWNLOADER_BROWSER_PRE_INTERACTION_WAIT',
'VKDOWNLOADER_COOKIE_SOURCE', 'VKDOWNLOADER_DOWNLOAD_DIR', 'VKDOWNLOADER_DOWNLOAD_TIMEOUT',
'VKDOWNLOADER_HEADLESS', 'VKDOWNLOADER_HTTP_CHUNK_SIZE', 'VKDOWNLOADER_LOCALE',
'VKDOWNLOADER_LOG_FILE', 'VKDOWNLOADER_LOG_LEVEL', 'VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS',
'VKDOWNLOADER_MAX_RETRIES', 'VKDOWNLOADER_SSL_VERIFY', 'VKDOWNLOADER_THROTTLED_RATE',
'VKDOWNLOADER_TIMEZONE', 'VKDOWNLOADER_USER_AGENT'] var=VKDOWNLOADER_MAXRETRIES

########## STDERR (err.txt) ##########
Configuration error: one or more settings have invalid values.
Check your .env file or VKDOWNLOADER_* environment variables:
  - vkdownloader_maxretries: Extra inputs are not permitted
    Did you mean: VKDOWNLOADER_DOWNLOAD_TIMEOUT? (check for typos)
    Received: <redacted>
Fix the offending value(s) and try again.
```

Three inconsistencies in one run, all about the same misconfiguration:

1. **Wrong stream.** The *warning* is on **stdout**; the *error* it predicts, for the same key,
   is on **stderr**. stdout is where results go — a caller that redirects or parses stdout
   receives a 1,400-character warning as if it were data, and a caller scanning stderr for
   problems finds nothing until the process has already decided to abort.
2. **Third format.** The warning renders as
   `<timestamp> [warning ] <event> key=value ...` — structlog's pre-configuration default. It
   matches neither of the two formats `setup_logging` installs: the colourised
   `ConsoleRenderer` used when no log file is configured, or the `JSONRenderer` written to
   `VKDOWNLOADER_LOG_FILE`. The same application emits three different line shapes for the
   same class of event.
3. **Lost from the log artifact.** With `VKDOWNLOADER_LOG_FILE` configured, the JSON log
   contains the post-setup events and the pre-construction warning appears in no log file at
   all. Confirmed: a run with `VKDOWNLOADER_LOG_LEVEL=DEBUG` and `VKDOWNLOADER_LOG_FILE` set
   produced a JSON log whose first records were `{"event": "env_file_resolved", ...}` with no
   preceding configuration warning, because the run aborted at construction before any handler
   existed.

**Exact consequence.** A user configures a log file and greps it for configuration problems.
The one diagnostic that fires *before* the log exists is absent from the log, so the log and
the terminal disagree about what happened. A user scripting the tool redirects stdout to a
pipe and gets a multi-line structlog dump mixed into their data stream. A user reading only
stderr — where every other error in the process goes — never sees the warning that would have
told them which key was wrong, and gets only the post-mortem.

**R11 baseline.** No test in `tests/test_config.py` covers the emission stream or the format
of the pre-construction warning; the guard's tests assert only the returned key list.

**Recommendation:** Keep the scan, but make it a rendered diagnostic rather than a log record
before logging exists. Return the findings from the scan (it already returns `list[str]`) and
have the entry point render them to **stderr** through the same `typer.echo(..., err=True)`
machinery that emits the validation failure at `cli.py:140` and `cli.py:279`:

```python
unknown = warn_unknown_env_vars()
if unknown:
    typer.echo(
        "Configuration warning: unrecognised VKDOWNLOADER_* variables: "
        + ", ".join(unknown),
        err=True,
    )
```

That puts the warning on the same stream as the failure it anticipates, removes the third
format from the output, and costs nothing in behaviour. If the warning should also reach the
log artifact, emit it a second time *after* `setup_logging` rather than relying on a
pre-configuration emitter. As a separate, smaller change, stop passing the full 16-entry
`valid_vars` list on every line — the valid-name list is already printed on the no-match branch
at `config.py:235`, and repeating it inline is what makes the line 1,400 characters wide.

---

### CFG-007: The model accepts an empty value for settings that have no meaningful empty form

| Field | Value |
|-------|-------|
| **ID** | CFG-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** Two path-typed settings already receive explicit empty-string handling.
`normalize_download_dir` at `src/vkdownloader/config.py:130-147` maps `""` to the field default,
and `empty_string_to_none` at `config.py:149-162` maps `""` to `None`. The docstring at
`config.py:140-142` states the intent explicitly: *"ensures consistent empty-string behavior
across all path-typed fields."*

That consistency was applied only to the two path fields. The remaining free-text settings have
no `min_length` and no empty-value validator, and R2 observed one of them accepting an empty
string silently.

**Evidence — R2, construction with an empty value for settings that have no empty form.**

| Input | Outcome |
|---|---|
| `VKDOWNLOADER_USER_AGENT=` | **ACCEPTED — `user_agent` is `''`** |
| `VKDOWNLOADER_MAX_RETRIES=` | REJECTED `int_parsing` — "Input should be a valid integer, unable to parse string as an integer" |
| `VKDOWNLOADER_LOG_LEVEL=` | REJECTED `value_error` — "Value error, '' is not a valid LogLevel" |

The two numerics and the enum reject an empty value with a clear message. The one string that
gets through is the one with four production read sites, every one of which forwards the empty
value verbatim into a protocol or a driver call:

| Read site | What the empty value becomes |
|---|---|
| `src/vkdownloader/services/segment_downloader.py:901` | `"User-Agent": ""` in the per-request header dict |
| `src/vkdownloader/services/downloader.py:278` | `f"User-Agent: {self.settings.user_agent}\r\nReferer: ..."` — an empty header line in the ffmpeg header block |
| `src/vkdownloader/services/ytdlp_downloader.py:607` | `--user-agent ""` appended to the yt-dlp command line |
| `src/vkdownloader/infrastructure/browser.py:105` | `user_agent=""` passed to the browser context constructor |

`timezone` and `locale` (`config.py:47-54`) are unbounded strings in the same class and reach
`browser.py:106-107` as `locale=""` and `timezone_id=""`.

**Exact consequence.** A user writes `VKDOWNLOADER_USER_AGENT=` in `.env` — a common way to
mean "unset this" after copying a template — and gets no error, no warning, and no diagnostic.
The application then sends an empty `User-Agent` on every request, passes an empty user agent
to the browser context, and invokes the downloader with `--user-agent ""`. The CDN sees an
empty agent string and the request is refused or fingerprinted; the user is left with a
transfer failure and no configuration message pointing at the line they just wrote. The
transfer-level effect is **UNVERIFIED** (R-S2) — it requires a live origin.

**Why advisory rather than mandatory.** The three neighbouring settings already reject an
empty value with a clear message, so the inconsistency is real and the fix is small; but
reaching the bad state requires the user to write an explicit empty assignment, and the
resulting failure is a failed transfer rather than data loss or a security boundary. This is
recorded as a hardening and consistency item, not a correctness emergency.

**R11 baseline.** `tests/test_config.py:232-261` covers the empty-string path for
`download_dir` and `log_file` only; no test covers an empty value for `user_agent`,
`timezone`, or `locale`.

**Recommendation:** Give the free-text settings the same treatment the path settings already
get, using the existing `mode="before"` validator pattern so the failure is a validation
failure with the redacted rendering already in place:

```python
@field_validator("user_agent", "timezone", "locale", mode="before")
@classmethod
def reject_empty_string(cls, v: object) -> object:
    if isinstance(v, str) and not v.strip():
        raise ValueError("must not be empty; remove the setting to use the default")
    return v
```

An explicit message beats a fall-through to the default here, because an empty user agent is
not a request for the default — it is a request for no user agent, and silently substituting
the default would hide a real mistake. The same validator removes the need for
`env_ignore_empty` to be configured, which is currently off, so an empty assignment is
currently indistinguishable from a deliberate one at the source.

---

### CFG-008: The resolved environment file is reported only at DEBUG, so working-directory dependence is invisible at the default log level

| Field | Value |
|-------|-------|
| **ID** | CFG-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

**Description:** The environment file is resolved relative to the process's current working
directory, declared as `env_file = ".env"` at `src/vkdownloader/config.py:191` and stated
prose-only in the model's docstring at `config.py:34-35`. R5 confirms the dependence: the
identical model, constructed from two different working directories, produced two different
configurations — all 16 fields took the file's values in run (a) and all 16 fell back to
defaults in run (b).

The process does contain the reporting function for this, but every line it emits is at DEBUG:

```python
def _log_env_file_path() -> None:            # src/vkdownloader/cli.py:40
    env_file = Path(".env")
    if env_file.exists():
        logger.debug("env_file_resolved", path=str(env_file.resolve()))
    else:
        logger.debug(".env file not found; using environment variables or defaults only")
```

Both branches are `logger.debug` — the "not found" branch, the one that actually explains a
surprise, is the quieter of the two. Called at `cli.py:130` and `cli.py:242`, i.e. *after*
`setup_logging`, so the level configured by `log_level` applies: at the declared default
`LogLevel.INFO` (`config.py:121-124`) neither line is emitted.

**Evidence — R8, entry-point runs at the default log level, streams captured separately.**

```
=== .env present in the working directory ===
stdout: (empty)              stderr: Invalid URL format. ...
stdout: NO mention of .env   stderr: NO mention of .env

=== .env absent entirely ===
stdout: (empty)
stdout: NO mention of .env   stderr: NO mention of .env
```

The two runs are byte-identical from the user's point of view. The diagnostic exists and works
— it was observed firing:

```
{"path": "C:\\...\\cli_fill\\.env", "event": "env_file_resolved", "level": "debug", "timestamp": "..."}
```

at `VKDOWNLOADER_LOG_LEVEL=DEBUG`, and the level setting itself is confirmed to reach its
consumer (a CRITICAL-level run suppressed both the debug and the info records, a DEBUG-level
run emitted them).

The user-facing guide does not close the gap. `docs/11-guides/configuration.md:19` says only
"Create a `.env` file to customize defaults" and `docs/01-tools/installation.md:114` says only
"Create a `.env` file for custom settings" — neither states that the file must sit in the
directory the command is run from.

**Exact consequence.** A user installs the tool, writes `.env` next to the project as the
documentation's phrasing implies, and runs `vkdownloader` from anywhere else — a different
terminal, a scheduled task, a shortcut, a CI step. Every setting silently reverts to its
default: the browser reappears, retries drop to 3, the log file stops being written. Nothing
in the output distinguishes this from a correctly loaded configuration, and the only way to
find out is to first raise the log level, which the user has no reason to suspect is the
cause. Under §9 this is a resolution that depends on the working directory with no diagnostic.

**Recommendation:** Report the resolution at INFO rather than DEBUG — the not-found branch as a
single-line notice, the found branch as a single line naming the path. The information is
already correct and already formatted; only the level is wrong:

```python
def _log_env_file_path() -> None:
    env_file = Path(".env")
    if env_file.exists():
        logger.info("env_file_resolved", path=str(env_file.resolve()))
    else:
        logger.info("env_file_not_found_using_environment_or_defaults")
```

One INFO line per run is a negligible cost and makes the "why did my setting not apply"
question answerable without guesswork. Alongside it, state the location in
`docs/11-guides/configuration.md` next to the "Create a `.env` file" instruction, so the
dependence is documented where a user reads it rather than only in a source docstring. A
longer-term alternative, if the project wants the file to be findable regardless of where the
command runs, is to resolve it against the project root as well as the working directory and
report which one won — that changes the resolution rule rather than the reporting, and should
be decided deliberately rather than as a logging tweak.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 2 |

| ID | Severity | Type | One-line |
|---|---|---|---|
| CFG-001 | CRITICAL | SPEC-DEVIATION | `.env`/environment values for `ssl_verify` and `cookie_source` are unconditionally replaced by the entry layer's default option values |
| CFG-002 | HIGH | SPEC-DEVIATION | The post-construction `max_retries` override skips the declared range and type, and the admitted values reach the consumer |
| CFG-003 | MEDIUM | SPEC-DEVIATION | The "did you mean" renderer matches across two namespaces; 11 of 19 misspellings get a wrong suggestion |
| CFG-004 | MEDIUM | SPEC-DEVIATION | The pre-construction typo guard misses the `export`, lower-case and quoted-key assignment forms |
| CFG-005 | MEDIUM | DOC-UPDATE | `.env.example:27` offers `VKDOWNLOADER_THROTTLED_RATE=10000`, below the declared floor, and contradicts the installation guide |
| CFG-006 | MEDIUM | SPEC-DEVIATION | The configuration warning is emitted on stdout in a third log format and never reaches the log artifact |
| CFG-007 | LOW | BEST-PRACTICE | Empty values are rejected for numeric and enum settings but accepted for `user_agent`, `timezone` and `locale` |
| CFG-008 | LOW | BEST-PRACTICE | The resolved environment file is reported only at DEBUG, so working-directory dependence is invisible at the default level |

## Mandatory Fixes

| ID | Severity | What must change |
|---|---|---|
| CFG-001 | CRITICAL | Stop passing `cookie_source` and `ssl_verify` as unconditional constructor keywords from either entry point, so an option the user did not type stops occupying the highest-priority configuration source. `src/vkdownloader/cli.py:127`, `:239`. |
| CFG-002 | HIGH | Re-validate the post-construction override instead of `model_copy(update=...)`, so the declared `ge`/`le` and type still apply. `src/vkdownloader/services/downloader.py:652-653`. |
| CFG-003 | MEDIUM | Match the offending key against the environment-variable namespace, not the field namespace, and raise `cutoff` so an unrelated long name cannot out-score a genuine near-match. `src/vkdownloader/config.py:220,229-235`. |
| CFG-004 | MEDIUM | Make the pre-construction scan read the file the way the consuming parser does, so `export`, lower-case, quoted-key and inline-comment forms stop defeating the guard. `src/vkdownloader/config.py:247-275,309`. |
| CFG-005 | MEDIUM | Correct the illegal value in the committed template and add the two missing declared ranges to the settings guide. `.env.example:27`; `docs/11-guides/configuration.md:34-35`. |
| CFG-006 | MEDIUM | Emit the pre-construction configuration warning on stderr through the same machinery as the validation failure, instead of through a log record emitted before logging exists. `src/vkdownloader/cli.py:125,237`; `src/vkdownloader/config.py:313-319`. |

## Advisory Recommendations

| ID | Severity | What to change |
|---|---|---|
| CFG-007 | LOW | Reject an empty value for the free-text settings, matching the empty-string handling the two path fields already have. `src/vkdownloader/config.py:43-54`. |
| CFG-008 | LOW | Report the resolved environment file — and the not-found case — at INFO, and state the working-directory location in the settings guide. `src/vkdownloader/cli.py:40-46`; `docs/11-guides/configuration.md:19`. |

## Doc Updates Needed

| ID | Type | Document | Claim to correct |
|---|---|---|---|
| CFG-005 | DOC-UPDATE | `.env.example:27` | `VKDOWNLOADER_THROTTLED_RATE=10000` is below the declared floor of 50000 (`src/vkdownloader/config.py:102`) and crashes the process at startup. |
| CFG-005 | DOC-UPDATE | `.env.example:27` vs `docs/01-tools/installation.md:131` | Two shipped documents give different values for the same setting; only the installation guide's `100000` is legal. |
| CFG-005 | DOC-UPDATE | `docs/11-guides/configuration.md:34-35` | The reference table omits the declared ranges for `throttled_rate` (50000-1000000) and `http_chunk_size` (0-104857600), while giving ranges for the other four bounded settings. |
| CFG-001 | SPEC-DEVIATION | `docs/11-guides/configuration.md:31,36,176-179` | The guide presents `VKDOWNLOADER_SSL_VERIFY` and `VKDOWNLOADER_COOKIE_SOURCE` as settings sourced from the environment file; the entry layer makes that source unreachable for them. Either the guide must state the command-line option is the only working source, or CFG-001 must be fixed. |
| CFG-004 | SPEC-DEVIATION | `src/vkdownloader/config.py:250` | The docstring claims the pre-flight reader "uses the same simple `KEY=VALUE` semantics as pydantic-settings"; it does not, on three assignment forms. |
| CFG-008 | BEST-PRACTICE | `docs/11-guides/configuration.md:19`, `docs/01-tools/installation.md:114` | Neither states that the environment file is resolved from the process's current working directory. |

---

## Verification Ledger

Every finding above cites at least one R-row. R-S1 and R-S2 are documented skips, recorded in
the header and never counted as clean results.

| ID | Method | What it established | Findings it supports |
|---|---|---|---|
| R1 | Introspect the model in one `uv run python -` session; per-field read-site counts split by production vs test source, excluding every worktree directory | 16 declared fields with type, default, range, enum membership; declared metadata (prefix `VKDOWNLOADER_`, `extra='forbid'`, `hide_input_in_errors=True`); no field has an empty production read list | CFG-001 (a consumer trace alone would read as healthy) |
| R2 | Unknown key in the environment file; the same key in the process environment only; programmatic non-text values for an enum field and a range field; empty values | File key → `extra_forbidden`; process-environment key → silently ignored (matches the documented claim at `config.py:30-32`); all non-text and out-of-range inputs leave through `ValidationError`; no rejected value appears in any rendered message | CFG-003, CFG-007 |
| R3 | Accept/reject at floor−1, floor, default, ceiling, ceiling+1 for all 7 bounded fields; defaults asserted inside their own ranges | Every declared range enforced exactly as declared on the construction path; all 7 defaults inside their ranges | CFG-002 (the bound that is later bypassed), CFG-005 |
| R4 | Every bounded field's read sites and substituted literals recorded; values assembled at floor and ceiling with a stubbed transport | `-R 1`…`-R 10`, `--socket-timeout 30`…`3600`, `-N 1`…`-N 16`, `--throttled-rate 50000`…`1000000`, `--http-chunk-size` omitted at 0 and `104857600` at the ceiling; both interaction waits reach `asyncio.sleep` unchanged. No end of any range the consumer cannot express — no finding filed | — |
| R5 | All 16 fields set to distinguishable values; constructed from the file's directory, from an empty directory, and from the process environment with the file absent; per-field diff; repeated through the process's own command-line entry point on both commands, with a positive control | Every documented source reaches every field *except* `ssl_verify` and `cookie_source`, which are shadowed by constructor keywords; the documented four-level resolution order is otherwise truthful | CFG-001 |
| R6 | Post-construction override applied the way production applies it, at floor−1, ceiling+1 and wrong types; read back from the live object; a recording stub at the consumer's read site; consumer-side evaluation of the retry comparison | Seven admitted values, all reaching the consumer unchanged; a non-positive value yields 0 download attempts, a wrong type yields an unhandled `TypeError` | CFG-002 |
| R7 | 13 assignment forms, one fixture file each; scanner key/value vs consumed key/value, plus the construction outcome | Reader and consumer diverge on `export` (key), inline comment (value); the guard is defeated on 3 of 6 misspelled forms | CFG-004 |
| R8 | 19 misspellings through the real environment-file path; stdout and stderr captured separately at the entry point; the log artifact inspected | 11 of 19 wrong suggestions; the warning lands on stdout in a third format and never reaches the log artifact; `.env` resolution is never reported at the default level | CFG-003, CFG-006, CFG-008 |
| R9 | Every assignment in `.env.example` and in each settings document uncommented in isolation and constructed; two-way name diff; named values checked against the declared type | 1 of 16 template lines rejected; name sets identical in both directions; `throttled_rate` illegal in the template and legal in the installation guide; no real credential in the artifact | CFG-005 |
| R10 | `ruff check`, `ruff format --check`, `mypy` over the settings module and its declared consumers | All three exit 0 with no findings — the baseline these results were observed against, not filed as a finding | — |
| R11 | `pytest tests/test_config.py`, then the test names mapped against blocks (a)–(g) | 29 passed, 2 skipped. No test covers: the entry layer's shadowing construction pattern, the post-construction override, the `export`/lower-case/quoted-key guard forms, a wrong "did you mean" suggestion, the emission stream or format of the pre-construction warning, an empty value for `user_agent`/`timezone`/`locale`, or the line-by-line validity of `.env.example` | Corroboration for CFG-001, CFG-002, CFG-003, CFG-004, CFG-006, CFG-007 |
