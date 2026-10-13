---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 10 Audit Findings — Test Coverage

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/10-audit-test-coverage.md`
**Status:** complete
**Validated:** no

**Measurement basis.** `HEAD` = `a335b2a`. The working tree is dirty: `src/vkdownloader/cli.py` and
`src/vkdownloader/config.py` carry uncommitted edits from a concurrent agent. Every anchor in
`services/downloader.py`, `services/segment_downloader.py`, `services/cookies.py`,
`services/ffmpeg_utils.py`, `services/downloader_throttle.py`, `services/signal_handlers.py`,
`utils/security.py` and `utils/url_sanitizer.py` is **HEAD-anchored** — those files are unmodified.
Anchors in `cli.py` and `config.py` are **working-tree-anchored** and are labelled as such.

**Runtime.** Windows (`os.name == 'nt'`, `platform win32`), CPython 3.12.1, pytest 9.1.1,
pytest-asyncio 1.4.0, ffmpeg `N-117624-g9eb7e8d2a4-20241023`. All probes ran under `.temp/t10/`
(gitignored) and were deleted; the tracked tree was confirmed clean after R2 and after R12.

---

## Verification record

| Row | What was run | Result |
|---|---|---|
| R1 | `uv run pytest tests -q -p no:cacheprovider -rs` ×2 + `--collect-only -q` | 502 collected; 498 passed, 4 skipped, 0 failed, 0 warnings; 25.4 s and 28.5 s. Three runs agree. Counts the state the findings below were observed in — filed as coverage, never as evidence of isolation. |
| R2 | `uv run --with pytest-cov pytest tests --cov=vkdownloader --cov-report=term-missing` (then `json:` redirected into `.temp/t10/`) | 2234 statements, 239 missed, **89 %**. Per-module table and the complete missing-line set captured. `COVERAGE_FILE` redirected so the run left nothing in the tracked tree; `git status` confirmed clean afterwards. |
| R3 | Missing-line set ∩ statement ranges obtained by **parsing** each module with `ast` (not reading it) | Range→missing intersections produced for every body cited below. |
| R4 | Substitution-site enumeration per external boundary role | 63 distinct product-space targets / 368 sites; 5 external / 58 sites. Real crossing of any boundary is a documented skip (fixed wording below). |
| R5 | One `VKDOWNLOADER_*` variable set alone per run; whole suite re-launched from a second working directory; suite re-run with no overlay | `VKDOWNLOADER_COOKIE_SOURCE=browser`, `VKDOWNLOADER_MAX_RETRIES=99`, `VKDOWNLOADER_SSL_VERIFY=false` each moved **0** of 30 tests in `tests/test_config.py`. Second working directory (`.temp/t10/`): 498 passed / 4 skipped, identical. The `tests/conftest.py:13-42` autouse fixture neutralises both halves. |
| R6 | Each of the 19 test modules run alone; two explicit orderings of the process-global-mutating modules | Per-file results sum to exactly the whole-suite result (498 + 4). Both orderings: 250 passed / 4 skipped. Restoration probes: `test_hls_downloader.py:2655` patches `signal.signal` itself, so no real process signal state is mutated; `test_progress_display.py:283-313` asserts handlers are repointed back and `test_progress_display.py:38` provides a restoring fixture. |
| R7 | Unpatched construction search per boundary role | HTTP client: **0** references to `aiohttp` / `ClientSession` in the entire test tree. Process: 42 `patch("asyncio.create_subprocess_exec")` sites, 0 unpatched. Media tool: 6 `patch("yt_dlp.YoutubeDL")` sites, 0 unpatched. Browser driver: 2 `patch(...async_playwright)` sites, 0 unpatched. Real child processes in the whole suite: 2, both harness (`test_packaging.py:309` `uv build`; `test_config.py:427` the `.env` positive-control probe) — neither is a product subprocess. |
| R8 | Every `patch()` first argument resolved to a dotted name by AST; assigned one of four classes | 426 sites classified. Disqualifying classes: the subject (7 sites on `download_hls_with_resume`, 7 on `HLSDownloader.download_with_ffmpeg`); scheduling primitives (4 on `asyncio.wait_for`, 1 on `asyncio.get_running_loop`); production models whose validation is the point (24 on `vkdownloader.cli.Settings`). |
| R9 | Per test, `patch()` targets intersected with symbols imported from the product; compared-value provenance classified | No exact leaf-name self-substitution. Two self-confirming classes present: read-backs of a stand-in's own call record (e.g. `test_security.py:75` `call_kwargs = mock_logger.warning.call_args[1]`) and values the test configured into a stand-in (the `MagicMock` settings at 24 `cli.Settings` sites). |
| R10 | Every conditional and skip guard enumerated; real terminal-attachment state and real access-control state read by a throwaway probe test | 4 skip guards, 0 conditionals, all 4 reported as **skips** under `-rs`. Probe output: `sys.stdin.isatty()=True`, `sys.stdout.isatty()=False`, `sys.stderr.isatty()=False`; a file created and `os.chmod(p, 0o600)` measured `st_mode & 0o777 == 0o666`, `st_file_attributes == 32`. The guards are honest; the *form* is a reported skip, not a reported pass. |
| R11 | `pyproject.toml`, `pytest.ini`, `tox.ini`, `setup.cfg` inspected at the root and in the test tree; markers enumerated against `--markers` | **No pytest configuration file exists anywhere.** Markers used: `asyncio` ×174, `skipif` ×4 — both registered. Difference: empty. |
| R12 | One undecorated `async def` test in a scratch file outside the tracked tree, run with `--rootdir=<repo>` | **Failed**: `Failed: async def functions are not natively supported` … `You need to install a suitable plugin`. pytest-asyncio 1.4.0 defaults to `asyncio_mode=strict`; omitting the decorator is a hard failure, not a silent pass. File deleted; `git status` clean. |
| R13 | Both workflow definitions read | 2 workflows. `packaging-check.yml:44` runs `uv run pytest tests/test_packaging.py -v` and fires on `tests/**`. `doc-lint.yml` greps `docs/` for NUL bytes. Test-execution job: **present but scoped to 1 of 21 modules (14 of 502 tests)**. lint / format / typecheck / dependency-scan / secret-scan / lockfile-check / build-and-publish: absent — recorded as a cross-reference to `11`, not filed here. |
| R14 | Finding-shaped identifiers swept from the test tree; each resolved against the current tree and the register | 9 `D-` ids carried, **all 9 resolve** to entries in `.ai/plans/done/01-confirmed-code-defects_DONE.md`. Three carried ids use this phase's own live prefix (see TST-015). No identifier was adopted. |

### Documented skips (fixed wording)

- **R4 — crossing a real process, media-tool, browser-driver or HTTP-client boundary.** Attempted:
  run the product's own subprocess/network/browser paths unmodified. Why the evidence is unobtainable:
  the suite substitutes every one of them (R7 counts above) and a real crossing would require a live
  VK session, a CDN and a media payload that the declared prerequisites do not provide. What remains
  verifiable: the substitution counts, the coverage of the bodies behind the boundaries, and the
  consequences cited in TST-001, TST-002, TST-003 and TST-006. Owner of the unverifiable half: the
  boundary's own phase (`05` process/media-tool, `06` credentials, `03` network).
- **R10 — whether a `0o600` mode is actually in force.** Attempted: create a file, `os.chmod` it to
  `0o600`, read the real mode. Why the evidence is unobtainable: on this platform `os.chmod` toggles
  only the read-only attribute, so the probe measured `0o666` regardless of the request. What remains
  verifiable: that the four guards report a skip and never a pass, which is the form this phase files
  (TST-014). Owner of the unverifiable half: `06` for the credential file, `07` for every other
  artefact.
- **R1 — isolation.** Re-running the suite is not a test of isolation, and none of the findings below
  rests on repetition. Isolation was established by R5's variation, not by R1's agreement.

---

## Findings

### TST-001: The suite asserts that `ffmpeg @argfile` works; no assertion in it can fail if it does not

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_hls_downloader.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** `HLSDownloader.download_with_ffmpeg` builds its command as
`["ffmpeg", f"@{argfile}"]` (`downloader.py:303`). Three tests assert that this form is what the
product emits, and each is satisfied by the *string*, not by any ffmpeg executing anything:

* `tests/test_hls_downloader.py:275-288` (`test_download_with_ffmpeg_uses_argfile_syntax`) asserts
  `len(captured_args) == 2`, `captured_args[0] == "ffmpeg"`, `captured_args[1].startswith("@")`,
  and `not argfile_path.exists()` after the call. The last one is satisfied because
  `_temp_argfile`'s `finally` unlinks the file (`downloader.py:124`) whether or not anything read it.
* `tests/test_hls_downloader.py:742` asserts `captured_args[0] == "ffmpeg"` and, at `:725`, strips
  the `@` with `args[1][1:]` **in the test's own stand-in** to read the file.
* `tests/test_hls_downloader.py:787` does the same.

The stand-in is the only thing in the whole system that ever reads the argfile. Because all 42
`asyncio.create_subprocess_exec` constructions in the suite are substituted (R7), **no assertion in
the suite can fail on whether the muxer honours `@`**. The suite therefore encodes a broken
convention as a passing, documented guarantee: `tests/test_hls_downloader.py:239` names it in prose
("uses ffmpeg @argfile to hide m3u8 URL and cookies"), and `:640`, `:686` carry it as a security
oracle.

**Evidence вЂ” R3** (`--cov` missing-line set в€© statement ranges parsed with `ast`): `downloader.py:303`
is covered, so the test does reach the body; the gap is the assertion, not the execution.

**Evidence вЂ” own runtime probe** against the installed muxer, decisive control included:

```
A. ffmpeg @<argfile>          returncode: 4294967274   (no output file)
   [... ] Unable to choose an output format for '@C:\...\a.args';
          use a standard extension for the filename or specify the format manually.
          Error opening output file @C:\...\a.args.
B. same argv passed directly  returncode: 0            output produced: True, 2511 bytes
C. @<file> naming valid lavfi returncode: 4294967274   (same literal-@ token error)
```

Control B is the same argument vector without `@`; control C shows the token is consumed as a literal
filename whatever the file contains. The muxer never opens the file.

**Exact consequence:** with `downloader.py:396`, every call to `download_with_ffmpeg` reaches
`if process.returncode != 0:` and returns `None`. The HLS transport the product documents and ships
produces no artefact, and the 498-test suite reports it green. The argument vector itself belongs to
`05` and the file on disk to `07`; this finding is filed only for what the test asserts about them.

**Recommendation:** the test's claim is wrong, not the production code's intent вЂ” per the project's
production-code-is-king rule, fix the test. Add one test that crosses the process boundary for real
for this specific body (ffmpeg is already a declared dependency and is on `PATH`), and demote the
three argv-shape tests to what they actually check: that secrets are absent from `process.argv`.
Assert the ffmpeg outcome, not the argv spelling. Until the transport is exercised end to end, no
test in the suite should carry `SEC-001`/`SEC-002` as satisfied on the argfile path.

---

### TST-002: All four cookie round-trip tests hard-code the dotted domain, which is exactly why the host-only defect ships green

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_cookies.py`, `src/vkdownloader/services/cookies.py` |
| **Classification** | mandatory |

**Description:** `tests/test_cookies.py` is the only module that drives the cookie file through the
real consumer, and its docstring (`:1-15`) states the standard correctly: "Assertions are made against
the jar, never against the file's text: a file that *looks* correct is not evidence that the consumer
accepted it." Its fixture constant defeats that standard anyway. `tests/test_cookies.py:25` declares
`_DOMAIN = ".vkvideo.ru"`, and all four round-trip tests (`:54`, `:79`, `:116`, `:138`) build every
cookie through `_cookie` / `_cookie_without_expiry_key` / `_cookie_with_null_expiry`, each of which
hard-codes `_DOMAIN`. The second input shape a host produces is never constructed.

`services/cookies.py:78` writes the Netscape *include-subdomains* column as the literal `TRUE`,
independent of the domain it just read at `:67`. For a host-only domain the two columns disagree, and
the real consumer refuses the whole file.

**Evidence вЂ” R2:** `services/cookies.py` is **100 % covered, 0 statements missed**. Every line of the
defect executes on every suite run. The instrument cannot see it, because the suite never varies the
input that distinguishes the two shapes.

**Evidence вЂ” own runtime probe**, production writer в†’ real consumer, both shapes:

```
domain='.vkvideo.ru'  file line: b'.vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession_id\tabc123'
  jar.load() ok, parsed={'session_id'}, sent_to_vkvideo={'session_id'}
domain='vkvideo.ru'   file line: b'vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession_id\tabc123'
  jar.load() RAISED http.cookiejar.LoadError: invalid Netscape format cookies file ...
  http/cookiejar.py:2051  assert domain_specified == initial_dot  -> AssertionError
```

End to end through yt-dlp's own entry point (`yt_dlp.cookies.load_cookies`, which wraps `jar.load()`
in `except Exception: raise CookieLoadError`):

```
domain='.vkvideo.ru'   yt_dlp load_cookies(): OK
domain='vkvideo.ru'    yt_dlp load_cookies() RAISED yt_dlp.cookies.CookieLoadError: failed to load cookies
```

**In-tree contradiction that makes the gap unambiguous:** the suite itself constructs the host-only
shape twice and asserts only on the text вЂ” `tests/test_extractor.py:227` (`{"domain": "vkvideo.ru"}`,
inside `test_cookies_to_netscape_preserves_domain`, whose `:234` asserts only `"vkvideo.ru" in result`)
and `tests/test_hls_downloader.py:1033` (`domain="vkvideo.ru"`). Two test modules disagree about the
shape the browser reports; only one of them round-trips through the consumer, and it is the one that
picks the shape the format cannot reject.

**Exact consequence:** `extractor.py:288` obtains cookies from `page.context.cookies()`. When any
returned cookie is host-only, the file written at `ytdlp_downloader.py:304` and passed as
`--cookies` at `:305` is rejected by yt-dlp with `CookieLoadError`, so `--cookie-source browser`
supplies no cookies and the download proceeds unauthenticated. The whole file fails, not one line.
**UNVERIFIED** for the exact domain VK's session cookie carries вЂ” that half needs a live browser,
which the declared prerequisites exclude. The defect in the writer and the blind spot in the test are
both observed; the trigger is not.

**Recommendation:** production code is right, the test is wrong. Add the host-only shape to the
`_cookie()` builders in `tests/test_cookies.py` (a `domain` parameter defaulting to `_DOMAIN`, with
one case per column-agreement shape) so the file is driven through `jar.load()` on both. That single
addition is what would have caught the defect; the docstring's own standard, applied to both shapes,
suffices.

### TST-003: A forced final-merge failure destroys every segment original, and the suite's only failure-path test asserts a boolean

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_ffmpeg_utils.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | mandatory |

**Description:** `_merge_batch_segments` deletes each batch's segment originals as soon as that batch
merges (`ffmpeg_utils.py:314-316`), and `_merge_segments_batched`'s `finally` (`:511-515`) then
deletes every batch temp it created. So a final-merge failure on a video above the 100-segment batch
size leaves nothing to retry from. The suite tests both halves of that chain and never their
composition:

* Success paths over the batch boundary are covered вЂ” `test_ffmpeg_utils.py:433` (250 segments),
  `:532` (150), `test_hls_downloader.py:2622` (`test_merge_segments_batched_uses_batch_size_100`, 250).
* The only final-merge *failure* test is `test_ffmpeg_utils.py:331-351`
  (`test_final_merge_returns_false_on_failure`). It passes **one** temp file, `assert result is False`,
  and asserts nothing about what is on disk. A one-temp-file final merge is not the batched shape
  (`:506` needs `len(temp_files) >= 1`, and the multi-batch case is what leaves zero originals).
* No test drives `_merge_segments_batched` to a failing final merge at all.

**Evidence вЂ” R3** (parsed statement ranges в€© missing lines): the failure branch of `_perform_final_merge`
is only partly executed вЂ” `:352-354` (the timeout path) is missing, `:363-364` executes. The
destructive `finally` at `:511-515` is reached on every `_merge_segments_batched` test and is
therefore *covered* while nothing asserts what it destroyed.

**Evidence вЂ” own runtime probe**, 250 real segment files, batch merges succeeding and the final merge
forced to fail:

```
segments before        : 250
ffmpeg invocations     : 4 (rc values: [0, 0, 0, 1])
_merge_segments_batched: None
original .ts survivors : 0 of 250
batch temps survivors  : []
final_list.txt present : True
output file produced   : False
```

**Exact consequence:** 0 of 250 originals survive. `segment_downloader.py:617-618` calls
`_cleanup_segments` only on success, but by then the directory holds only `final_list.txt`. The
documented resume guarantee вЂ” asserted for the playlist-fetch failure
(`test_hls_downloader.py:295-321`) and the segment-download failure (`:324-354`) вЂ” is not asserted for
the third failure mode, the only one that destroys the input. A user who hits a final-merge failure
must re-download every segment from the CDN.

**Recommendation:** add one test that builds more than 100 segments, forces the final merge to fail,
and asserts the state of the directory afterwards. If the intended guarantee is "a failed final merge
keeps its inputs", the test will fail against current production code and the fix belongs in
`ffmpeg_utils.py:314-316`/`511-515`; if the guarantee is "a failed merge is unrecoverable", the
docstring for `_merge_segments_batched` must say so, because the resume tests imply the opposite.
Either way the assertion has to exist before the behaviour is claimed.

---

### TST-004: `test_validate_output_path_rejects_traversal_even_if_resolved` claims a guard the suite never executes

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_security.py`, `src/vkdownloader/utils/security.py` |
| **Classification** | advisory |

**Description:** `tests/test_security.py:154-161` is a class whose docstring is specifically about the
post-resolution half of the traversal guard: "SEC-006: The pre-resolution `..` check is a no-op for
paths that callers already resolve. The fix adds a post-resolution check too." Its last test,
`test_validate_output_path_rejects_traversal_even_if_resolved` (`:195-209`), is named and documented
as verifying that post-resolution guard. It does not:

```python
path = Path("/safe/base") / ".." / "etc"        # :204  str(path) still contains ".."
# :205  # path.resolve() will resolve this to /etc (no ".."), but str(path) has ".."
# :206  # The pre-resolution check catches it. For the post-resolution check,
# :207  # we verify that a path object with ".." in its string form is rejected:
```

The test's own comments (`:205-207`) say the **pre**-resolution guard at `security.py:47-50` fires.
Its docstring (`:196-201`) says it verifies the **post**-resolution guard. The test asserts
`pytest.raises(DownloadError, match="Path traversal detected")` вЂ” a message both guards produce
verbatim, so it cannot distinguish them.

**Evidence вЂ” R2/R3** (missing-line set в€© the parsed range of `validate_output_path`):
`utils/security.py` reports missing `60, 61, 62`. Line `59` (`if ".." in str(resolved):`) is
evaluated on every call; the body that raises вЂ” `60`, `61`, `62` вЂ” **never executes in any of the
502-test run**. The guard the class exists to protect is untested.

**Exact consequence:** a reviewer reading the class docstring and the test name concludes the
post-resolution guard is covered. It is not. If that body were deleted, the suite stays green; if it
is load-bearing for callers that pass an already-resolved path (`security.py:102` does, via
`_resolve_output_file`), nothing in the suite would notice.

**Recommendation:** the two comments at `:205-207` are the honest description of what the test does.
Either build a real post-resolution case вЂ” a path whose `str()` is clean but whose resolved form
carries `..`, which needs a symlink or a UNC edge вЂ” and rename the test to match, or split it into two
tests with the pre-resolution one named for what it actually covers. Do not leave the docstring
claiming the second.

### TST-005: Nothing outside one machine runs the suite; the one workflow that does runs 14 of 502 tests

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.github/workflows/packaging-check.yml`, `.github/workflows/doc-lint.yml`, `pyproject.toml` |
| **Classification** | advisory |

**Description:** The repository has two workflow definitions. `doc-lint.yml` greps `docs/` for NUL
bytes and touches nothing else. `packaging-check.yml` is the only job that executes tests, and its
single command is `uv run pytest tests/test_packaging.py -v` (`:44`). That is 14 of the 502 collected
tests. The other 19 modules вЂ” including every test named in TST-001 through TST-004 and TST-006 вЂ”
have no execution outside the developer's own machine.

The gate is also correctly scoped in one respect and that is worth preserving: its path filter is
derived from the sdist allow-list, so `tests/**` does fire it. It simply does not run what lives
there.

**Evidence вЂ” R13** (both workflow files read in full): workflow count 2; commands run:
`uv sync --locked`, `uv run pytest tests/test_packaging.py -v`, and a `grep -rlaP '\x00' docs/`.
Present: test execution (partial). Absent: lint, format check, type check, dependency scan, secret
scan, lockfile check, build-and-publish. No coverage measurement is declared anywhere вЂ” neither in
the workflows nor in `pyproject.toml` (R11 found no `[tool.pytest.ini_options]` table, and no
`pytest-cov` entry in `[dependency-groups] dev`).

**Exact consequence:** the ranked coverage gaps in this report are not gated by anything. A regression
that removes an oracle, or reintroduces the argfile and cookie defects, is invisible to every party
except the developer who happens to run `pytest`. This is the "the ordered list is non-empty and
nothing in the repository gates it" finding from block (a): the 89 % figure is descriptive, and the
39 % of bodies that never execute in the highest-risk modules are not a control that anything enforces.

**Recommendation:** add a workflow that runs `uv run pytest tests` on `src/**` and `tests/**` changes.
Everything else вЂ” declaring a coverage tool, a threshold, a lint job вЂ” is `11`'s to add, and this
finding prescribes none of it. The single highest-value change is the one-command full-suite job.

---

### TST-006: The entire aiohttp layer is absent from the test tree, including the cancellation path

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_segment_downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory |

**Description:** `aiohttp` is a declared runtime dependency and is used in exactly two modules.
Searching the whole test tree (excluding worktree directories) for `aiohttp`, `ClientSession`,
`ClientTimeout`, `TCPConnector`, `ssl.`, `CERT_NONE` and `_create_connector` returns **0 matches for
every pattern**. Not one test constructs, names, or stubs an HTTP client.

`tests/test_segment_downloader.py` is 281 lines and 5 tests, all for `_fetch_playlist_with_retry`, and
even those pass a bare `MagicMock()` as the session (`:49`, `:158`, `:208`). The module under them is
302 statements.

**Evidence вЂ” R2/R3** (`--cov` missing set в€© ranges parsed with `ast`):

* `services/segment_downloader.py` вЂ” 302 statements, **67 missed (77.8 %)**. Unreachable in the run:
  `_create_connector:539-543` (the entire `ssl.CERT_NONE` branch and the
  `ssl_verification_disabled` warning), `_await_and_cancel:562-570` (the whole cancellation body:
  `task.cancel()`, `asyncio.gather(..., return_exceptions=True)`, the `download_cancelled` log),
  `_run_parallel_download_with_backoff:234-244`, `_check_backoff_before_attempt:267-269`,
  `_try_single_download_attempt:301-303` (the `aiohttp.ClientError` handler),
  `_fetch_single_playlist:456-463` (every line of the real `session.get` call and its
  `aiohttp.ClientError` handler), `_refresh_token_and_retry:440-446`,
  `_download_segment_concurrent:677, 681, 715, 720` (four `raise asyncio.CancelledError` sites),
  `_create_segment_download_tasks:746-747`, `_clear_stale_segments:120-128`.
* `services/downloader_throttle.py` вЂ” 129 statements, 13 missed. `_retry_429_with_backoff:209-253`
  loses 7 lines and `_parse_retry_after:296-299` loses 4 вЂ” the whole `Retry-After` **HTTP-date** branch
  (`datetime.now(UTC)`, the `delta > 0` comparison, the return).
* `signal_handlers.py:52-54` and `:77-82` вЂ” see TST-012.

**Exact consequence:** none of the 502 passing tests can fail on a regression in the retry ladder, the
token-refresh handoff, the TLS-verification switch, the `Retry-After` date parser, or the cancellation
cleanup. A change that makes a cancelled download leak its tasks, or that silently disables
certificate verification when `ssl_verify=false`, or that mis-parses an HTTP-date `Retry-After`,
produces a green run. The `aiohttp.ClientError` handlers are the only thing standing between a
transient network fault and a failed download, and they have never run.

**Recommendation:** this is a coverage gap, not a production defect вЂ” the bodies are not shown to be
wrong here. Start with `_create_connector` (5 statements, one setting, and a security-relevant
switch), then `_await_and_cancel`, then `_parse_retry_after`'s date branch. Each needs a test that
supplies a real `aiohttp.ClientSession` against a local HTTP server; that harness does not exist yet
and building it is the real cost, not the individual tests.

---

### TST-007: The suite replaces the subject, the runtime's scheduling primitives, and the settings model

| Field | Value |
|-------|-------|
| **ID** | TST-007 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_extractor.py`, `tests/test_hls_downloader.py`, `tests/test_cli.py` |
| **Classification** | advisory |

**Description:** R8 resolved every `patch()` first argument to a dotted name (426 sites) and assigned
each to one of four classes. Three classes disqualify the substitution.

**The subject itself** вЂ” 14 sites: `vkdownloader.services.downloader.download_hls_with_resume` (7) and
`vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg` (7). A test that replaces the
body it is named for cannot fail on it. This is the mechanical reason TST-001 and TST-003 could not
have been caught: `test_hls_downloader.py:1201, 1250, 1310, 1461, 1551, 1613, 1727` all patch
`_merge_segments_batched`, and `:1201` et al. also patch `_fetch_playlist_with_retry`, so
`download_hls_with_resume` is exercised with both of its outcomes supplied.

**A scheduling primitive the runtime uses** вЂ” 5 sites, and these are the process-global stdlib names,
not module attributes:

* `tests/test_extractor.py:161` `patch("asyncio.wait_for", side_effect=fake_wait_for)` and
  `:162` `patch("asyncio.get_running_loop")` (bare stdlib paths).
* `tests/test_hls_downloader.py:1477, 1549, 1629` `patch("asyncio.wait_for", side_effect=mock_wait_for)`.

For the duration of those tests, every `asyncio.wait_for` in the process is the stand-in вЂ” including
the ones in `infrastructure/browser.py:77, 87`, `services/ffmpeg_utils.py:200, 238`,
`services/segment_downloader.py:719` and `services/downloader_throttle.py:72, 365`, none of which
those tests are about. `get_running_loop` is replaced with a bare `MagicMock` at
`test_extractor.py:162`, so any code under test that reads loop properties reads a mock.

**A production model whose validation is the subject** вЂ” 24 sites patching
`vkdownloader.cli.Settings` with a `MagicMock` (`test_cli.py:120, 147, 176, 258, 305, 349, 395, 450,
515, 565, 598, 631, 663, 716, 757, 802, 875, 941, 992, 1045, 1088, 1138, 1429, 1458`). Pydantic
validation, defaults and coercions are not exercised in any of them.

**Counter-argument, recorded because it is real:** `tests/test_cli.py:1465-1473` documents a class
(`TestEntryPointSourcePrecedence`) that deliberately does *not* patch `cli.Settings` so the `.env`
file and the variables are exercised end to end. The mitigation exists. It covers 4 of 24 sites.

**Evidence вЂ” R8/R9:** no exact leaf-name self-substitution was found (a test never patches a symbol it
also imports by that exact name). The disqualifying sites are the ones above. Two self-confirming
classes are present and are filed under (e): read-backs of a stand-in's own call record
(`test_security.py:75` `call_kwargs = mock_logger.warning.call_args[1]`, then `:76-77` assert on
those kwargs) and values the test configured into a stand-in (the 24 `MagicMock` settings objects,
whose `max_concurrent_downloads=4` and `log_file=None` are both the input and the expectation).

**Exact consequence:** with the subject replaced there is no oracle on it, so no change to
`download_hls_with_resume` or `download_with_ffmpeg` can be detected by the tests named after them вЂ”
which is precisely the mechanism by which TST-001 and TST-003 shipped. With `asyncio.wait_for`
replaced process-wide, a change in how any *unrelated* body sequences its subprocess teardown would
be invisible in exactly the tests that were supposed to catch it.

**Recommendation:** patch the module attribute (`vkdownloader.services.downloader_throttle.asyncio.wait_for`,
as `tests/test_downloader_throttle.py:522, 626, 642` already do correctly in the same codebase) rather
than the stdlib name, and never patch `get_running_loop` when the body under test only calls it. For
the CLI tests, keep `Settings` real and vary the environment instead вЂ” `tests/test_config.py:383-460`
already shows the pattern that makes that work.

### TST-008: The `download` command's entire error tail never executes

| Field | Value |
|-------|-------|
| **ID** | TST-008 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_cli.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `tests/test_cli.py` has 50 tests that drive the Typer app through `CliRunner`, and
they cover the success path thoroughly. None of them reaches the command's failure surface. Working
tree lines (`cli.py` is uncommitted; the tail is identical at `HEAD`):

* `cli.py:258-260` вЂ” `except VideoNotFoundError:` в†’ `"Video not found. Verify the URL is correct and
  the video is public."` в†’ `raise typer.Exit(code=1)`. **Not reached.** A 404 from VK вЂ” the single
  most common user error for this product вЂ” has no executing oracle.
* `cli.py:263-266` вЂ” the generic `except Exception:` that logs `download_failed` with a sanitised URL
  and exits 1. **Not reached.**
* `cli.py:219-220` вЂ” `"Download failed"` / `typer.Exit(code=1)` on the download-exception path. **Not
  reached.**
* `cli.py:379` вЂ” `app()` under `if __name__ == "__main__"`. **Not reached.**

**Evidence вЂ” R2/R3:** `cli.py` reports missing `123, 207, 219, 220, 247, 258, 259, 260, 261, 262,
263, 264, 265, 266, 379, 383`. The nine consecutive lines `258-266` are one `try/except` arm.

**Exact consequence:** the exit code the CLI returns for a missing video, and the message it prints,
are unverified. `tests/test_cli.py:941` sets `mock_selector.select.side_effect =
QualityNotAvailableError(...)` and that arm *is* covered вЂ” so the suite has demonstrated the pattern
and simply did not apply it to `VideoNotFoundError` or to the generic handler. A change to either
message, or to the exit code, ships untested.

**Recommendation:** two `CliRunner` tests вЂ” `side_effect=VideoNotFoundError(...)` and
`side_effect=RuntimeError(...)` on `vkdownloader.cli.perform_download` вЂ” assert the printed text and
the exit code. The machinery already exists in the same file.

---

### TST-009: `test_extra_forbidden_suggests_did_you_mean` cannot fail on a wrong suggestion

| Field | Value |
|-------|-------|
| **ID** | TST-009 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_config.py` |
| **Classification** | advisory |

**Description:** `tests/test_config.py:304-312` is the only test on `format_validation_error`'s
suggestion behaviour. Its final line is a disjunction:

```python
assert "Did you mean" in formatted or "Valid fields" in formatted   # :312
```

`config.py:226-232` emits **exactly one** of those two strings, on mutually exclusive branches: the
first when `difflib.get_close_matches` returns a candidate (`:227-230`), the second when it does not
(`:231-232`). The assertion is therefore true for every input the function can receive. Nothing in the test constrains *which*
name is suggested.

**Evidence вЂ” own runtime probe** over 25 misspellings: every row took the "Did you mean" branch, so
the second disjunct is never even the relevant one; and every suggested name was a member of
`_build_valid_env_vars()`. Examples of the suggestion's *usefulness* (a different question, owned by
`02`): `quality` в†’ `VKDOWNLOADER_USER_AGENT`, `qualities` в†’ `VKDOWNLOADER_MAX_RETRIES`,
`timeout` в†’ `VKDOWNLOADER_TIMEZONE`.

**Non-reproduction, recorded with exact inputs:** on the 25 misspellings above, the suggestion is
**always a syntactically valid variable name** вЂ” 0 of 25 produced a name absent from
`Settings.model_fields`. The claim that the suggestion is *wrong* in 12 of 19 cases is **not
reproduced by this phase's measurement**; the semantic mismatch above is the only defect the probe
observed, and whether it is a defect is `02`'s to decide. What is observed here, without inheritance,
is that the test is structurally incapable of catching either a wrong name or a missing branch.

**Exact consequence:** a change to the cutoff (`0.3` at `config.py:227`), to `n=1`, or to the branch
structure would leave this test green. The test's own docstring (`:305`) promises "Should suggest the
correct field name" вЂ” the assertion does not check that.

**Recommendation:** split the disjunction. Assert `f"Did you mean: VKDOWNLOADER_{expected_field}?" in
formatted` for a parametrised set of known typos, and a separate test that the "Valid fields" branch
is reached for an input far from every field name. That is two assertions instead of one tautology,
and it is what the docstring already describes.

---

### TST-010: No test configuration file exists; 174 hand-applied async markers rest on an undeclared plugin default

| Field | Value |
|-------|-------|
| **ID** | TST-010 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `pyproject.toml`, `tests/` |
| **Classification** | advisory |

**Description:** There is no pytest configuration file anywhere: `pyproject.toml` has no
`[tool.pytest.ini_options]`, and `pytest.ini`, `tox.ini` and `setup.cfg` do not exist at the root or
in the test tree. Everything the runner does is therefore the framework's default, and the suite
depends on two of those defaults without saying so.

**Evidence вЂ” R11:** configuration files found: none. Markers used: `asyncio` Г—174, `skipif` Г—4.
Markers registered: both are registered (the first by pytest-asyncio, the second by pytest core), so
the marker diff is empty. The gap is the undeclared settings: `asyncio_mode`, `testpaths`,
`filterwarnings`, `addopts`, `xfail_strict` and `markers` are all unset.

**Evidence вЂ” R12** (the implicit default, executed, not read): a throwaway `async def` test with no
decoration, in a scratch file outside the tracked tree, run with `--rootdir=<repo>`:

```
1 failed
Failed: async def functions are not natively supported.
You need to install a suitable plugin for your async framework ...
```

pytest-asyncio 1.4.0 defaults to `asyncio_mode=strict`. The practical cost is what this measures: the
suite's entire async execution contract is 174 manually applied decorators plus an undeclared plugin
default. Under `asyncio_mode=auto` вЂ” a common project-wide setting, and one a maintainer adding a
first pytest table would plausibly write вЂ” all 174 become redundant; under a future default change,
they are the only thing keeping 174 tests from silently not running.

**Exact consequence:** the suite has no declared statement of which plugins it requires, no declared
marker registry, and no warning policy. A dependency bump that changes a default is caught, if at
all, by noticing that tests stopped running вЂ” not by a failing assertion.

**Recommendation:** add a `[tool.pytest.ini_options]` table with `asyncio_mode` stated explicitly
and `testpaths = ["tests"]`. If `auto` is chosen, the 174 decorators can be dropped in a separate,
mechanical change. Stating the mode is the whole fix; the table is a few lines.

### TST-011: The integration tier is an empty package that ships in the source distribution

| Field | Value |
|-------|-------|
| **ID** | TST-011 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/integration/`, `tests/test_packaging.py` |
| **Classification** | advisory |

**Description:** `tests/integration/` contains one file, `__init__.py`, whose entire content is
`"""Integration tests package for VK Video Downloader."""` There is no test in it. R1 collected 502
tests, all from the 19 modules directly under `tests/`. The directory is nevertheless declared as
shipped content: `tests/test_packaging.py:118` lists `tests/integration/__init__.py` in
`EXPECTED_SDIST_ENTRIES`, and `test_sdist_entry_set_matches_the_manifest` (`:418-423`) fails if it
disappears. So the one tier whose purpose is to cross the boundaries R7 records as never crossed is
asserted into the release artefact while contributing nothing.

**Evidence вЂ” R1** (`--collect-only -q`): 502 collected, every one from `tests/test_*.py`.
**Evidence вЂ” R7:** 0 unpatched constructions of any external boundary, across all 502 tests. **0
tests contributed by the tier that exists to cross them.** Two real child processes exist in the whole
suite (`test_packaging.py:309` `uv build`; `test_config.py:427` the `.env` positive-control probe) and
neither exercises a product boundary.
**Evidence вЂ” R2:** the tree still contains `tests/__pycache__/test_http_client.cpython-312*.pyc` and
`tests/integration/__pycache__/test_mock_vk_server.cpython-312*.pyc` вЂ” compiled artefacts of test
modules that no longer exist in the source tree. Recorded as inventory; the `.pyc` files are stale
build output, not evidence, and they are gitignored.

**Exact consequence:** a reader of the tree sees an integration package and reasonably infers an
integration tier. There is none, and the packaging test enforces the illusion. The consequence of
every boundary in R7 being crossed zero times is cited to the owning phases; what is filed here is
that the gap has a name and no content.

**Recommendation:** either populate the package or remove it. If it is removed, drop
`tests/integration/__init__.py` from `EXPECTED_SDIST_ENTRIES` in the same change вЂ” that test will
tell you if you forget. Building the tier itself is not an audit subject and is not prescribed here.

---

### TST-012: The signal-handling module is the least covered module in the suite, and its two real registration loops never run

| Field | Value |
|-------|-------|
| **ID** | TST-012 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_hls_downloader.py`, `src/vkdownloader/services/signal_handlers.py` |
| **Classification** | advisory |

**Description:** `services/signal_handlers.py` is 46 statements with **13 missed вЂ” 71.7 %, the lowest
of any module in the package that has a test at all.** The suite does test the module
(`test_hls_downloader.py:2636-2681`), but it does so by replacing the very thing under test.

`test_windows_fallback_registers_signal_handlers` (`:2640-2664`) patches
`asyncio.get_running_loop` to a `_FakeLoop` whose `add_signal_handler` raises `NotImplementedError`
(`:2647-2652`) **and** patches `signal_module.signal` (`:2655`). The fallback loop it claims to cover,
`signal_handlers.py:52-54`, is therefore entered but its `signal.signal` call is the mock вЂ” and
`mock_signal.call_count == 2` (`:2659`) is a read-back of the stand-in's own call record. The
`RuntimeError` guard at `:37-38` and the `_registered_signals.add` at `:44` are missing; the cleanup
loop at `:77-82` is missing.

**Evidence вЂ” R2/R3** (missing set в€© parsed ranges): `signal_handlers.py` missing `37, 38, 44, 52, 53,
54, 65, 66, 77, 78, 79, 80, 82`.

**Exact consequence:** whether a real `signal.signal` registration succeeds on this platform, and
whether `cleanup_signal_handlers` actually restores `SIG_DFL`, is unverified. `assert
mock_signal.call_count == 2` (`:2659`) is satisfied by the mock being called twice; it is not evidence
that the process's signal disposition was set or restored. Whether the handler correctly derives
shutdown state from a delivered signal belongs to `04`; the *form* of the oracle standing in for it
is what this phase files, and the guarantee is **UNVERIFIED** вЂ” a real signal is not delivered by the
test environment, and R6 confirmed no test supplies one.

**Recommendation:** keep the unit test for the branch selection, but say what it checks вЂ” branch
choice, not registration. The registration effect is only observable in a subprocess that is
actually signalled, which the current tier cannot do; recording that as a known gap in the module
docstring is better than a test name that implies otherwise.

---

### TST-013: The four file-permission oracles never execute an assertion body on the platform developers use

| Field | Value |
|-------|-------|
| **ID** | TST-013 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_config.py`, `tests/test_hls_downloader.py` |
| **Classification** | advisory |

**Description:** Four `@pytest.mark.skipif(os.name == "nt")` guards вЂ” `test_config.py:337` and `:353`
(log file mode), `test_hls_downloader.py:533` and `:679` (cookie file and argfile mode) вЂ” are skipped
on every run on the declared development platform. Each is a reported **skip**, not a reported pass,
and each carries a reason that is accurate and specific ("`os.chmod` there toggles only the read-only
attribute, so the measured mode is `0o666`"). All four are justified: the assertion is a factual claim
about a POSIX mode, and the platform does not offer the mode.

The form is the finding. Of the suite's whole security surface, exactly two artefact-permission claims
are made in tests вЂ” the temp cookie file at `test_hls_downloader.py:539-550` and the log file at
`test_config.py:343-370` вЂ” and **neither ever runs an assertion on the platform where the code is
developed.** A further 16 permission-adjacent assertions elsewhere in the suite are about paths and
content, not modes, and do execute.

**Evidence вЂ” R10** (real state read by a throwaway probe test, not searched for):

```
sys.stdin.isatty()  = True
sys.stdout.isatty() = False
sys.stderr.isatty() = False
os.name             = 'nt'
st_mode & 0o777 after chmod 0o600 = 0o666
st_file_attributes                 = 32
stat.S_IWRITE set?                 = True
```

So the guards are honest: unskipped, the assertions would fail at `0o666`, exactly as the reason
states. **The form of each oracle is a reported skip** вЂ” an assertion body that never executes.

**Exact consequence:** on the declared platform, a change to `os.chmod(path, 0o600)` at
`ytdlp_downloader.py`/`downloader.py:119`/`config.py:344` вЂ” including deleting the call entirely вЂ”
produces a green run. The `0o600` claim is carried by four tests that never assess it here, and by
nothing else. **UNVERIFIED** for whether the mode is in force; the guarantee belongs to `06` for the
credential file and `07` for the other artefacts, and this finding files only the shape of the oracle.

**Recommendation:** the guards are right; what is missing is any platform-independent assertion of
the *intent*. A test that asserts the `os.chmod(..., 0o600)` call is made вЂ” by substituting
`os.chmod` and asserting on the requested mode вЂ” would run everywhere and would catch the call being
removed. The mode check would then remain as the POSIX-only oracle it honestly is.

### TST-014: The concurrent uncommitted `_run_command_preamble` change has no test that can fail on it

| Field | Value |
|-------|-------|
| **ID** | TST-014 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_cli.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `src/vkdownloader/cli.py` carries an uncommitted edit (working tree 383 lines; `HEAD`
320). It moves the unknown-`VKDOWNLOADER_*` notice out of the logging path and into the preamble as
plain stderr text вЂ” `cli.py:119-128`:

```python
unknown_vars = warn_unknown_env_vars()
if unknown_vars:
    valid_vars = sorted(_build_valid_env_vars())
    for var in unknown_vars:
        typer.echo(f"Ignored unknown environment variable '{var}'. ...", err=True)
```

**Working-tree-anchored; this code is uncommitted and may change.** The corresponding removal in
`config.py` deletes the `unknown_env_var_ignored` warning and the module logger.

Two tests touch the preamble. `test_cli.py:1841-1854` patches
`vkdownloader.cli.warn_unknown_env_vars` with no `return_value`, so the stand-in returns a
`MagicMock` вЂ” truthy, iterating as empty вЂ” and asserts only `mock_warn.assert_called_once()`,
`mock_log_env.assert_called_once()` and `mock_setup.assert_called_once()`. `test_cli.py:1303` patches
it to raise. Neither asserts what is printed. The other two preamble tests (`:1861`, `:1884`) replace
`_run_command_preamble` wholesale.

**Evidence вЂ” R2:** `cli.py` reports line `123` вЂ” the `typer.echo(` call вЂ” as **missing**. The notice
body has never executed in any run.

**Exact consequence:** the notice's text, its `err=True` routing, and the fact that it fires **once
per unknown variable** are all unverified. A typo in the message, a missing `err=True`, or a
regression that makes the loop fire zero or twice passes. Because `warn_unknown_env_vars` returns a
truthy `MagicMock` in the only test that reaches the body, the branch is entered by accident and its
loop runs zero times вЂ” a test that reaches the code and checks nothing about it.

**Recommendation:** set `return_value=["VKDOWNLOADER_MAXRETRIES"]` on the existing patch and assert
`result.output`/the captured stderr contains that variable name and the valid-variable list. One test
addition; the patch is already there.

---

### TST-015: The test tree already carries three identifiers in this phase's own live prefix

| Field | Value |
|-------|-------|
| **ID** | TST-015 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `tests/test_cli.py`, `tests/test_hls_downloader.py` |
| **Classification** | advisory |

**Description:** The phase catalogue reserves `TST-` for itself and notes that a two-character
collision is unresolvable by the validator. The collision already exists in the tree:

* `tests/test_cli.py:277` вЂ” `(TST-002)`
* `tests/test_hls_downloader.py:501` вЂ” `"""Direct unit tests for _create_temp_cookie_file (TST-004)."""`
* `tests/test_hls_downloader.py:2843` вЂ” `(TST-006)`

**Ownership, per site, recorded before anything is filed:** all three are in *test* documentation, so
they are this phase's. None is adopted, extended or renumbered by this report вЂ” TST-001 through
TST-014 are minted fresh and skip past the occupied numbers. The other carried forms are
`CFG-001`/`CFG-002`, `DF-007`, `INT-001`вЂ¦`INT-007`, `SEC-001`вЂ¦`SEC-007`, `SRV-003`, `SRV-006`,
`STR-008`, `VAL-105`, and `D-01`вЂ¦`D-05`, `D-09`вЂ¦`D-12`.

**Evidence вЂ” R14:** all nine `D-` ids carried by the test tree **resolve** to entries in
`.ai/plans/done/01-confirmed-code-defects_DONE.md` вЂ” no stale register reference. `D-06`, `D-07`,
`D-08` and `D-13` exist in the register and are referenced by no test; `D-08`'s subject is precisely
the four permission oracles now recorded as skips in TST-013, so its absence from the tree is
consistent with the fix having landed.

**Exact consequence:** a reader вЂ” or the validator's cross-finding merge detection вЂ” cannot tell from
`TST-002` at `test_cli.py:277` whether it refers to this phase's catalogue or to the project's own
pre-audit defect list. One `TST-` identifier in the tree points at a test that has nothing to do with
test coverage.

**Recommendation:** rename the three sites to a form the audit does not use вЂ” `D-` is already
exhausted and correct for register entries, so these three want either the register's numbering if
they track a real defect, or no identifier at all. The two `TST-` sites in `test_hls_downloader.py`
describe coverage additions with no defect behind them and can simply drop the parenthetical.

---

### TST-016: Eight degradation and cancellation branches in the two download modules never execute

| Field | Value |
|-------|-------|
| **ID** | TST-016 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/utils/url_sanitizer.py` |
| **Classification** | advisory |

**Description:** Beyond the network layer in TST-006, several failure paths that exist specifically to
degrade gracefully are never entered, so the degradation they implement is unverified.

* `ffmpeg_utils.py:305-307` вЂ” `_merge_batch_segments`'s `except TimeoutError` в†’ `batch_merge_timeout`
  в†’ `return None`. The **timeout** half of a batch merge has never run; the returncode half at
  `:309-312` has.
* `ffmpeg_utils.py:352-354` вЂ” `_perform_final_merge`'s `except TimeoutError` в†’ `final_merge_timeout`
  в†’ `return False`. Same shape, opposite outcome from the tested returncode path.
* `ytdlp_downloader.py:522-529` вЂ” `except QualityNotAvailableError` and the re-raise at `:529` in
  `_attempt_segment_resume`; `:547-561` вЂ” the `except (ExtractionError, OSError)` /
  `except ValueError` arms and their `raise`s.
* `ytdlp_downloader.py:86-108` вЂ” `_await_first_and_cancel_others`: `task.cancel()`, `await task`,
  `except asyncio.CancelledError: pass` at `:103-107`, all missing.
* `downloader.py:375-382` вЂ” `download_with_ffmpeg`'s shutdown branch: when
  `shutdown_event.is_set()`, `cancel_subprocess` and `ffmpeg_cancel_not_clean`. The four
  `if not await cancel_subprocess(process)` guards at `:321, 342, 376, 404` are all missing, so the
  "the child was not reaped" warning has never been emitted in a test.
* `utils/url_sanitizer.py:29-30` вЂ” `except Exception: return "***REDACTED***"`, the redaction
  backstop. Never runs.
* `config.py:232` вЂ” the `Valid fields:` branch of `format_validation_error`, the other half of
  TST-009's disjunction. Never runs; that is why my 25-misspelling probe saw the "Did you mean"
  branch every time.

**Evidence вЂ” R2/R3** (missing set в€© parsed ranges), listed per body above. `ffmpeg_utils.py` is 94 %
and `ytdlp_downloader.py` 86 % overall вЂ” high figures that coexist with these eight unexecuted
branches, which is the concrete illustration that a module percentage says nothing about any body.

**Exact consequence:** a change to the timeout handling, the cancel-and-wait sequence, the resume
retry arms, or the redaction backstop ships untested. Each of these is a degradation path: its whole
purpose is to behave correctly when something has already gone wrong, which is exactly the situation
the suite never constructs.

**Recommendation:** these are the cheapest bodies in the report to cover вЂ” each is an `except` arm
around a stub. The shared shape is: substitute the awaited call with a stand-in that raises, assert
the return value and the logged event. `tests/test_ffmpeg_utils.py` already has
`MagicMock(spec=asyncio.subprocess.Process)` set up for exactly this.

---

## Appendix вЂ” (a) ranking evidence

The factor table below is the raw material for block (a). `O` is oracle strength (3 a test can fail on
the body В· 2 a test asserts a call or a return but not the body В· 1 a test exists whose name or
documentation claims it В· 0 no test references it), measured by R3 and R9. `C` is the consequence
class read from the owning phase's own severity vocabulary; no severity is assigned here. `E` is
reachability (2 reachable without an external boundary В· 1 only behind a boundary the suite mocks В·
0 not reachable in this environment), measured by R7. The comparator is `O` ascending в†’ `C` descending
в†’ `E` ascending в†’ owning phase ascending в†’ subject name ascending, applied with no judgement between
the table and the order.

| Body (owner) | O | C | E | Basis |
|---|---|---|---|---|
| `ffmpeg @argfile` transport, `downloader.py:303` (05) | 2 | 3 | 1 | assertions are on the argv shape only; R7 shows 0 real subprocess crossings |
| Netscape cookie file в†’ real consumer (06) | 2 | 3 | 1 | 100 % executed, 0 missed; the asserted input is the test's own constant |
| segment originals across a failed final merge, `ffmpeg_utils.py:511-515` (03) | 2 | 3 | 1 | no test drives the failing batched merge; the only failure test uses 1 temp file |
| TLS-verification switch, `segment_downloader.py:539-543` (06) | 0 | 3 | 1 | 0 references to `_create_connector`; body unexecuted |
| cancellation cleanup, `segment_downloader.py:562-570` (04) | 0 | 3 | 1 | 0 references to `_await_and_cancel`; body unexecuted |
| `Retry-After` HTTP-date parse, `downloader_throttle.py:296-299` (03) | 0 | 2 | 1 | body unexecuted |
| `download` error tail, `cli.py:258-266` (01) | 0 | 2 | 2 | body unexecuted; reachable with no boundary |
| post-resolution traversal guard, `security.py:59-62` (06) | 1 | 3 | 2 | a test's docstring claims it; the body is unexecuted |
| permission-mode oracles Г—4 (06/07) | 1 | 3 | 2 | reported skip; the assertion body never executes |
| `_await_first_and_cancel_others`, `ytdlp_downloader.py:103-107` (04) | 0 | 2 | 1 | body unexecuted |
| batch/final merge timeout arms, `ffmpeg_utils.py:305-307, 352-354` (03) | 0 | 2 | 1 | bodies unexecuted |
| redaction backstop, `url_sanitizer.py:29-30` (06) | 0 | 3 | 2 | body unexecuted |
| `format_validation_error` suggestion name (02) | 0 | 1 | 2 | the assertion is a disjunction; no test constrains the name |
| log-file format contract (08) | 0 | 1 | 2 | see `OUT-002`; structlog `BoundLogger` path (`vkdownloader.services.downloader.logger`); one test reads content & asserts ABSENCE; B2 (`ca25ad8`) adds PRESENCE |

Applying the comparator: the four `O=0, C=3` bodies lead, then the three `Oв‰¤1, C=3`, then the `O=2`
rows. **The list is non-empty, and nothing in the repository gates it** вЂ” that is the finding, filed
once as TST-005. The per-body consequence of each row belongs to the owning phase; this phase cites
the measurement and files the absence of the oracle, once each, in TST-001 through TST-016.

### Non-reproductions (recorded with exact inputs, not as clean results)

* **"The `Did you mean` suggestion names a field that does not exist."** Inputs: 25 misspellings вЂ”
  `maxretries, max_retry, max_retrie, download_dir_, downloaddir, logfil, log_leve, sslverif, quality,
  qualities, timeout, cookey_source, useragent, throttledrate, http_chunksize, browser_wait, headles,
  tz, headlesss, downlaod_dir, maxtimeout, retrys, logg_level, sslverifyy, browserr` вЂ” each passed to
  `Settings(**{bad: "1"})` with the resulting `ValidationError` handed to `format_validation_error`.
  Result: **0 of 25** produced a name absent from `Settings.model_fields`. The *test-side* fact that
  the assertion cannot detect this is filed as TST-009; the *behaviour* is not reproduced here.
* **Measured shape table for the log-file format contract (`VAL-120`; D-6 branch (a) taken: the
   phase 10 report is a working artefact and editable).** Input: `setup_logging(Settings(log_file=...,
   log_level="DEBUG"))`, then events through the product’s own logger — a structlog `BoundLogger` at
   `vkdownloader.services.downloader.logger`, the object every module obtains — for the
   success path, one single-link `logger.exception` record, and one two-link chained record:

   | Scenario | Total non-empty lines | Parseable-JSON lines |
   |---|---|---|
   | success path | 1 | 1 |
   | single-link `logger.exception` record | 1 | 1 |
   | two-link chained exception record | 1 | 1 |

   All three produce 100 % parseable JSON. Phase-08’s `OUT-002` remains the surviving
   finding for the failure-path record shape; `_ExcInfoClearingFormatter` (`config.py:365-367`,
   commit `65d1c0a`, P13-B3) clears `exc_info` before `JSONRenderer` serialises, eliminating
   the non-JSON lines that path observed. One test reads the log file’s content and asserts
   ABSENCE; B2 (`ca25ad8`) now adds a positive oracle asserting PRESENCE. The gap was: no
   test asserted that a record the product emitted was present in the log file —
   this is now closed.
* **The four permission skips.** Reproduced as reported skips, and their stated reason verified
  independently (see TST-013, R10). Not re-filed as anything other than the form of the oracle.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 4 |
| MEDIUM | 6 |
| LOW | 3 |

## Mandatory Fixes

- **TST-001** вЂ” `tests/test_hls_downloader.py:275-288, 725, 742, 787` assert an `ffmpeg @argfile`
  transport that the installed muxer does not read. Add a real process crossing for this body; demote
  the argv-shape tests to the secrecy claim they actually check.
- **TST-002** вЂ” `tests/test_cookies.py:25` hard-codes `_DOMAIN = ".vkvideo.ru"` in all four
  round-trip tests, so the host-only domain that makes the whole cookie file unloadable is never
  constructed. Add both column-agreement shapes to the `_cookie()` builders.
- **TST-003** вЂ” a forced final-merge failure leaves 0 of 250 segment originals, and the only
  failure-path test asserts a boolean over a single temp file. Add the batched failing-merge test, and
  reconcile the production behaviour with the resume guarantee the other two tests assert.
- **TST-006** вЂ” the aiohttp layer has zero references in the test tree; 67 of 302 statements in
  `segment_downloader.py`, including the whole cancellation body, never execute. Start with
  `_create_connector` and `_await_and_cancel`.

## Advisory Recommendations

- **TST-004** вЂ” `tests/test_security.py:195-209` claims a guard its own comments say it does not
  reach; `security.py:60-62` is never executed.
- **TST-005** вЂ” no workflow runs the suite; `packaging-check.yml:44` runs 14 of 502 tests, and no
  coverage measurement is declared anywhere.
- **TST-007** вЂ” the subject (14 sites), process-global `asyncio.wait_for` / `get_running_loop`
  (5 sites) and `vkdownloader.cli.Settings` (24 sites) are replaced. Patch module attributes, not
  stdlib names; keep `Settings` real in the CLI tests.
- **TST-008** вЂ” `cli.py:258-266`, the `VideoNotFoundError` arm and the generic handler, never execute.
- **TST-009** вЂ” `tests/test_config.py:312` is a disjunction over two mutually exclusive branch markers
  and cannot fail.
- **TST-010** вЂ” no pytest configuration file; 174 async markers rest on an undeclared plugin default.
- **TST-011** вЂ” `tests/integration/` is an empty package asserted into the source distribution.
- **TST-012** вЂ” `signal_handlers.py` is 71.7 % covered; its two real registration loops never run.
- **TST-013** вЂ” both artefact-permission claims are permanently skipped on the declared platform.
- **TST-014** вЂ” the uncommitted `cli.py:119-128` notice has no test; `cli.py:123` is unexecuted.

## Doc Updates Needed

- **TST-015** вЂ” the test tree carries `TST-002` (`test_cli.py:277`), `TST-004` and `TST-006`
  (`test_hls_downloader.py:501, 2843`) in this phase's own live prefix. Rename or drop; none is
  adopted here. All nine `D-` ids carried by the suite resolve against
  `.ai/plans/done/01-confirmed-code-defects_DONE.md`; no stale register reference.
