# Block H Audit Findings — FFmpeg transport (commit 13757de)

**Author:** auditor
**Validated by:** not run
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no
**Commit measured:** 13757ded7bd519978858e272fc0dd3dd3b9ead8f
**Working-tree state:** clean
**Dirty paths:** none

---

## Verification performed

- `uv run pytest tests/test_ffmpeg_transport.py tests/test_ffmpeg_utils.py tests/test_downloader.py tests/test_cli.py tests/test_packaging.py -q` -> 196 passed, 2 skipped.
- `uv run ruff check src tests` -> All checks passed.
- `uv run ruff format --check src tests` -> 71 files already formatted.
- `git diff --check` -> no whitespace errors.
- `uv run pytest -q` -> 1235 passed, 5 skipped, 2 failed. The 2 failures are in `tests/test_batch_downloader.py::TestBatchDownloaderSemaphore` (permit-leak/deadlock scenarios) and reproduce on the measured commit; they are not in the Block H scoped test set and are not caused by the FFmpeg branch (the failing paths use `DownloadMethod.AUTO`).
- `uv run mypy src` -> 45 errors in 7 files; 12 of them are in the new/changed Block H code (`src/vkdownloader/services/ffmpeg_transport.py`, plus the `FfmpegTransport` import and `state_machine.backend` access in `src/vkdownloader/services/downloader.py`).
- Runtime probe of the actual FFmpeg binary: `ffmpeg @<argfile>` is rejected by the installed build (`Error opening output file @...: Invalid argument`), confirming the transport's invocation form is not accepted by FFmpeg.
- Secret-safety inspection: `asyncio.create_subprocess_exec` receives only `["ffmpeg", "@<argfile>"]`; signed URLs, cookies, and cookie-file paths are confined to the 0o600 argfile. However, the transport's generic exception log records `str(exc)` without sanitization.

---

## Findings

### BH-001: FFmpeg transport invokes `ffmpeg @argfile`, which the installed FFmpeg does not accept

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Reproduced with the installed binary: `ffmpeg @<tempfile>` exits with "Error opening output file @...: Invalid argument". The @file response-file form used by `FfmpegTransport.download` is therefore not a working invocation on the target FFmpeg, so the adapter cannot complete a real download.
> - **See also:** BH-002

| Field | Value |
|-------|-------|
| **ID** | BH-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/ffmpeg_transport.py, src/vkdownloader/services/ffmpeg_utils.py |
| **Classification** | mandatory |
| **Verification** | observed |

**Description:** `FfmpegTransport.download` builds the full argument list, writes it to a temporary file via `_temp_argfile`, and spawns `ffmpeg @<argfile>`. FFmpeg does not treat a leading `@` argument as a response file in the installed build; it interprets the whole token as an output URL and fails before reading any input. The adapter consequently returns `None` for every real invocation, even though the unit tests pass because they replace `create_subprocess_exec` with a fake.

**Evidence:** `src/vkdownloader/services/ffmpeg_transport.py` lines 97-105:
```python
async with _temp_argfile(ffmpeg_args) as argfile:
    cmd: list[str] = ["ffmpeg", f"@{argfile}"]
    process = await asyncio.create_subprocess_exec(
        *cmd, ...
    )
```
Runtime probe (2026-11-06): `ffmpeg @C:\Users\...\a.args` -> `Error opening output file @...: Invalid argument`.

**Recommendation:** Replace the `@argfile` invocation with a form FFmpeg actually accepts. If the goal is to keep secrets out of argv, use FFmpeg's documented `-/option <file>` syntax for individual string options (for example `-/headers`) or pass the argument list directly; do not rely on an unsupported whole-command response file. Keep `shell=False` and an argument array in all cases.

---

### BH-002: The argfile is deleted before the FFmpeg process can read it

> **Validation Note:**
> - **Action:** validated
> - **Detail:** The `async with _temp_argfile(...)` block ends immediately after `create_subprocess_exec` returns, so `finally: Path(path).unlink(missing_ok=True)` runs while the child is still starting. Even on an FFmpeg build that supported response files, this is a use-after-free of the argument file.
> - **See also:** BH-001

| Field | Value |
|-------|-------|
| **ID** | BH-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/ffmpeg_transport.py, src/vkdownloader/services/ffmpeg_utils.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** `_temp_argfile` is an async context manager whose lifetime is scoped to the spawn call only. The process is created inside the `async with` block, but the block exits immediately afterwards, unlinking the file before FFmpeg has necessarily opened it. The argfile must live for the entire subprocess lifetime (until `process.wait()` completes) and be removed in the existing `finally` cleanup path.

**Evidence:** `src/vkdownloader/services/ffmpeg_transport.py` lines 97-106:
```python
async with _temp_argfile(ffmpeg_args) as argfile:
    cmd = ["ffmpeg", f"@{argfile}"]
    process = await asyncio.create_subprocess_exec(*cmd, ...)
# <-- context exits here, unlinking argfile
```
`src/vkdownloader/services/ffmpeg_utils.py` lines 177-188:
```python
async with _temp_argfile(...) as argfile:
    ...
finally:
    Path(path).unlink(missing_ok=True)
```

**Recommendation:** Move the `_temp_argfile` context to enclose the whole `try/except/finally` process lifecycle (progress reading, waiting, cancellation, cleanup), so the file exists until the child has exited, and is still removed on every exit path.

---

### BH-003: Cookie file path is appended to the signed media URL

> **Validation Note:**
> - **Action:** validated
> - **Detail:** The transport builds `ffmpeg_url = f"{ffmpeg_url}{separator}cookies=file:{cookie_file}"`. This is not a documented FFmpeg HTTP option form, so cookies are unlikely to be applied, and the cookie artifact path is embedded in the signed URL that is written to the argfile.
> - **See also:** BH-001

| Field | Value |
|-------|-------|
| **ID** | BH-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/ffmpeg_transport.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** FFmpeg's HTTP protocol does not accept a `cookies=file:` query parameter on the input URL. The correct mechanisms are the `-cookies` option or a `Cookie` header. As written, authenticated videos will fail with 403 and the cookie artifact path is mixed into the signed playlist URL inside the argfile.

**Evidence:** `src/vkdownloader/services/ffmpeg_transport.py` lines 68-71:
```python
ffmpeg_url = binding.media_playlist_url
if cookie_file is not None:
    separator = "&" if "?" in ffmpeg_url else "?"
    ffmpeg_url = f"{ffmpeg_url}{separator}cookies=file:{cookie_file}"
```

**Recommendation:** Pass cookies through FFmpeg's supported `-cookies` option (or `-headers "Cookie: ..."`) loaded from the temp file, and keep the input URL limited to `binding.media_playlist_url`. Continue to create and delete the cookie artifact in the existing `finally` block.

---

### BH-004: Generic exception path logs `str(exc)` without sanitization

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `logger.error("ffmpeg_transport_error", error=str(exc))` records the raw exception text. Other sinks in this codebase sanitize child/exception text via `sanitize_text_for_log`/`sanitize_exception`; this path does not.
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BH-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/ffmpeg_transport.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** An unexpected exception from cookie creation, process spawning, or I/O may contain the signed URL, cookie file path, or local username-bearing temp path. Logging `str(exc)` directly can leak those values into the structured log sink and diagnostic files, defeating the redaction guarantees established in Blocks C/E.

**Evidence:** `src/vkdownloader/services/ffmpeg_transport.py` lines 163-165:
```python
except Exception as exc:  # noqa: BLE001
    logger.error("ffmpeg_transport_error", error=str(exc))
    return None
```

**Recommendation:** Replace `str(exc)` with `sanitize_exception(exc)` (or `sanitize_text_for_log(str(exc))`), matching the handling used for `ffmpeg_download_failed` stderr in the same module.

---

### BH-005: State-machine backend is set as an ad-hoc attribute and not persisted

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `DownloadStateMachine` has no `backend` attribute; `state_machine.backend = "ffmpeg"` creates a transient instance attribute. `job_state.backend` is set, but `persist()` is never called, so the recorded value is not written to `state.json`. mypy reports `DownloadStateMachine has no attribute "backend"`.
> - **See also:** BG-005

| Field | Value |
|-------|-------|
| **ID** | BH-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/services/state_machine.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** The acceptance criterion requires the FFMPEG branch to record `backend="ffmpeg"` on the state machine. The current code sets both `state_machine.backend` (a non-existent property, shadowed only in memory) and `state_machine.job_state.backend`, but never persists the state. It also does not record the binding's `variant_id` as `stream_variant_id`, unlike the yt-dlp path. On reload, the backend field reverts to whatever was last persisted (likely `None`).

**Evidence:** `src/vkdownloader/services/downloader.py` lines 296-301:
```python
if state_machine is not None:
    state_machine.backend = "ffmpeg"
    try:
        state_machine.job_state.backend = "ffmpeg"
    except Exception:  # noqa: BLE001
        pass
```
`perform_download` does not call `state_machine.persist()` afterwards.

**Recommendation:** Set `state_machine.job_state.backend = "ffmpeg"` (and `stream_variant_id = getattr(binding, "variant_id", None)`), then call `state_machine.persist()` (guarded). Remove the non-existent `state_machine.backend` assignment. If the state machine cannot be mutated safely, log and continue without claiming the backend was recorded.

---

### BH-006: `ssl_verify=False` inserts `-tls_verify`/`0` at the wrong positions

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `ffmpeg_args.insert(5, "-tls_verify")` followed by `insert(6, "0")` places the value between `-tls_verify` and the existing `-headers` argument, producing `-tls_verify 0` only by accident and shifting the option out of its intended input-option position.
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BH-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/ffmpeg_transport.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** The conditional insertion uses hard-coded indices into a list whose layout is defined a few lines above. A future edit to the argument list silently breaks the SSL-disable option. The option should be inserted immediately before `-i` (as an input option) or, better, added to the argument list by name.

**Evidence:** `src/vkdownloader/services/ffmpeg_transport.py` lines 90-92:
```python
if not getattr(self.settings, "ssl_verify", True):
    ffmpeg_args.insert(5, "-tls_verify")
    ffmpeg_args.insert(6, "0")
```

**Recommendation:** Build the list with the SSL option in its correct position (for example insert both tokens before the `-i` token by locating it), or append them to a dedicated input-options section, rather than relying on magic indices.

---

### BH-007: `DownloadTransport` and `FfmpegTransport.download` are typed against `object`

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `download(self, binding, workspace: object)` forces `getattr(workspace, ...)` access and produces 12 mypy errors in the new module (`"object" has no attribute "staging_dir"/"final_path"` and `**dict[str, int | bool]` incompatibility for `_SPAWN_BOUNDARY_KWARGS`). The Protocol is therefore not actually type-safe.
> - **See also:** BG-006

| Field | Value |
|-------|-------|
| **ID** | BH-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/ffmpeg_transport.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** The Protocol declares `workspace: object`, so every attribute access is unchecked and the boundary kwargs (`dict[str, int | bool]`) are rejected by mypy's `create_subprocess_exec` overloads. This mirrors the explicit-`Any` problem flagged in Block G and weakens the contract the Protocol is meant to provide.

**Evidence:** `src/vkdownloader/services/ffmpeg_transport.py` lines 34-38 and 50-52:
```python
async def download(self, binding: StreamBinding, workspace: object) -> Path | None: ...
...
if workspace is not None and getattr(workspace, "staging_dir", None) is not None:
    output_file = workspace.staging_dir / workspace.final_path.name
```
`uv run mypy src` reports `"object" has no attribute "staging_dir"` and `"object" has no attribute "final_path"`.

**Recommendation:** Import `DownloadWorkspace` under `TYPE_CHECKING` and type the parameter as `DownloadWorkspace | None` (keeping the runtime import lazy to preserve `--help` startup). Cast `_SPAWN_BOUNDARY_KWARGS` to the expected mapping type at the call site, as other spawn sites in the codebase do.

---

### BH-008: Unrelated `config.py` logging changes shipped in the Block H commit

> **Validation Note:**
> - **Action:** validated
> - **Detail:** The commit modifies `setup_logging` to preserve handlers whose class name contains "Capture"/"caplog" and to tolerate non-`LogLevel` settings. Neither change is listed in `task_H_ffmpeg_transport.yaml` and neither is required by the Block H acceptance criteria.
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BH-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py |
| **Classification** | advisory |
| **Verification** | observed |

**Description:** The commit touches `src/vkdownloader/config.py` even though the task spec's file list and staging instructions for Block H do not include it. The change is benign (it keeps pytest's caplog handler alive and falls back to INFO for mock settings), but it is scope creep in a commit that is supposed to be strictly Block H, and it was not part of the reviewed/audited surface for this block.

**Evidence:** `git show 13757de -- src/vkdownloader/config.py` modifies `setup_logging` (caplog-handler preservation and `LogLevel` fallback). `task_H_ffmpeg_transport.yaml` `files:` and `commit.staging` do not list `config.py`.

**Recommendation:** Split this change into a separate, explicitly scoped commit (or fold it into the test-infrastructure changes) so the Block H diff contains only the FFmpeg transport work. If it stays, document the logging behaviour change in the operator/developer notes.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 3 |

## Mandatory Fixes

- BH-001: Replace the unsupported `ffmpeg @argfile` invocation with a real FFmpeg invocation form; the current adapter cannot complete a download.
- BH-002: Keep the argfile alive for the full subprocess lifetime; do not unlink it immediately after spawn.
- BH-003: Apply cookies through FFmpeg's supported option instead of appending `cookies=file:` to the signed URL.
- BH-004: Sanitize exception text before logging it in the transport's generic error path.
- BH-005: Persist `backend="ffmpeg"` (and the binding variant id) on the state machine instead of setting a non-existent attribute.

## Advisory Recommendations

- BH-006: Remove magic indices when conditionally adding `-tls_verify`.
- BH-007: Type the Protocol/workspace against `DownloadWorkspace` instead of `object`.
- BH-008: Move the unrelated `config.py` logging changes out of the Block H commit.

## Doc Updates Needed

none
