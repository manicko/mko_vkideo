# P12-B2 Auditor Context (`context_a`)

**Block:** P12-B2 — make the warning reach the user (`ART-009`, §3.3 / §6.3)
**PoO decision:** option (a) — warn everywhere (all call sites).
**Live working tree:** HEAD = `12af960`, `src/` and `tests/` clean in the working tree (no uncommitted modifications to production source or tests). `B1` (`12af960`, "fix(security): detect traversal by path component, not substring") is **committed**, not uncommitted as the task preamble states — the working tree carries the B1 change at its committed state.

---

## 1. `validate_output_path` — the function and its two guard layers

**File:** `src/vkdownloader/utils/security.py`
**Lines:** 36–88 (definition), 74 (`repo_root`), 91–120 (`_resolve_output_file`)

The function has **three** security-relevant sections, not two "warning-emitting branches". The task preamble's phrasing conflates the two `..`-detection guards (which raise) with the one warning (which logs). Concretely:

### Layer 1 — pre-resolution traversal guard (line 56)
```python
if ".." in path.parts:
    exc = DownloadError(f"Path traversal detected in output path: {path}")
    exc.error_code = ErrorCode.PATH_TRAVERSAL
    raise exc
```
**B1 changed this from `".." in str(path)` to `".." in path.parts`.** This is a `raise`, not a `logger.warning`. It fires when an unresolved input `Path` contains an exact `..` component.

### Layer 2 — post-resolution traversal guard (line 68)
```python
if ".." in resolved.parts:
    exc = DownloadError(f"Path traversal detected in resolved path: {resolved}")
    exc.error_code = ErrorCode.PATH_TRAVERSAL
    raise exc
```
**B1 changed this from `".." in str(resolved)` to `".." in resolved.parts`.** Also a `raise`, not a `logger.warning`. Defense-in-depth on the resolved path (catches symlinks/UNC paths that retain `..`).

### The warning-emitting section — containment check (lines 73–86)
```python
repo_root = Path(__file__).resolve().parent.parent.parent
try:
    resolved.relative_to(repo_root)
    if warning:
        logger.warning(
            "output_path_inside_repository",
            path=str(resolved),
            repo_root=str(repo_root),
            error_code="output_path_in_root",
        )
except ValueError:
    pass
```
This is the **only** `logger.warning` in the function. The `warning` parameter gates it. There is **no** pre-resolution containment warning — the `repo_root` check runs once, on the resolved path only.

### The `repo_root` derivation defect (line 74)
```python
repo_root = Path(__file__).resolve().parent.parent.parent
```
- `__file__` resolves to `C:\py_exp\mko_vkideo\src\vkdownloader\utils\security.py`
- `.parent` → `...\src\vkdownloader\utils\`
- `.parent` → `...\src\vkdownloader\`
- `.parent` → `...\src\` ← **this is the live value** (`C:\py_exp\mko_vkideo\src`)

The repository root is `C:\py_exp\mko_vkideo`. The expression is **one `.parent` short** — it derives `src/`, not the repo root. This is B2's domain per plan §3.3 item 2 and §6.3. It was confirmed unchanged at both `4bf9efb` (audit base) and `58bb7ce` (plan baseline) and is **unchanged at `12af960`** — `git diff HEAD -- src/vkdownloader/utils/security.py` produces no output. The file's last commit before B1 was `e59523c`, and B1's commit `12af960` touched only the two `..` guards, not `repo_root`.

**Consequence:** `resolved.relative_to(repo_root)` succeeds for paths under `src\` but raises `ValueError` (caught, no warning) for paths under the rest of the repo (e.g. `docs/`, `tests/`, project root files). The warning fires only inside `src/`, and stays silent everywhere else in the repo tree — even though Decision B says those paths are accepted too.

---

## 2. `_resolve_output_file` (lines 91–120) — the B10 → B2 edge

```python
def _resolve_output_file(video, output, settings, index) -> Path:
    output_path = output if str(output) != "." else settings.download_dir
    output_path = Path(output_path).resolve()

    validated_output = validate_output_path(output_path, warning=False)  # ← line 111
    validated_output.mkdir(parents=True, exist_ok=True)                   # ← line 112, C9 side effect

    safe_title = sanitize_title(video.title) if video.title else None
    if safe_title:
        output_file = validated_output / f"{safe_title}_{video.id}.mp4"   # ← line 116
    else:
        output_file = validated_output / f"{index}_{video.id}.mp4"       # ← line 118
    return output_file
```

**Findings:**
- **Call:** `validate_output_path(output_path, warning=False)` at line 111. This is one of the two `warning=False` call sites.
- **Key producer:** this function composes `{safe_title}_{video.id}.mp4` (or `{index}_{video.id}.mp4` when no title) and returns the resolved `Path`. That `Path` is the dedup key for P12-B10.
- **`mkdir` side effect (C9):** line 112 unconditionally creates the output directory. Every call to `_resolve_output_file` — including from the B10 pre-pass for a skipped entry — creates the directory. This is harmless when the directory is shared (it is, per batch), but it is observable.
- **Unchanged since `e59523c`:** the function body, the `warning=False` argument, and the `repo_root` derivation it triggers are all at their pre-B1 baseline. B1 only touched the two `..` guards inside `validate_output_path`.

**B10 → B2 edge:** B10's pre-pass (in the working tree, `batch_downloader.py:390`) calls `_resolve_output_file(_video, output, settings, i)` for every URL. That call reaches `validate_output_path(..., warning=False)` at security.py:111, **suppressing the warning**. This is the loader path's single place where the warning should fire per B2 option (a). The change is: **remove `warning=False` from `_resolve_output_file`** so it uses the default `warning=True`.

---

## 3. `cli.py` — the `download` and `batch` commands

**File:** `src/vkdownloader/cli.py`

### Single-URL `download` command (lines 347–472)
The `download` command **does not** call `validate_output_path` directly. Its call chain is:

```
cli.py::download (line 394)
  → download_video(url, quality_spec, output, ..., settings, log_available_qualities=True)
    → downloader.py:360  _resolve_output_file(video, output, settings, output_index)
      → security.py:111   validate_output_path(output_path, warning=False)   ← suppressed
```

The warning **is** suppressed on the loader path. The `output` argument to `download` defaults to `Path(".")` (line 351), so by default `download_video` receives `.` and `_resolve_output_file` resolves it to `settings.download_dir` before validation.

**No direct `validate_output_path` call exists in `cli.py`.** Grep for `validate_output_path` in `cli.py` returns zero matches.

### `batch` command (lines 475–591)
The `batch` command reads URLs (lines 540–548), validates them with `is_valid_video_url` (URL shape only, not dedup), counts invalid ones into `skipped_count` (line 546), and dispatches to `run_batch` (line 561) → `_run_batch_with_progress` (batch_downloader.py). The batch reader does **not** call `validate_output_path` or `_resolve_output_file` — those happen inside the service layer.

---

## 4. `services/batch_downloader.py` — the B10 pre-pass (working tree)

**File:** `src/vkdownloader/services/batch_downloader.py` — **modified in working tree** (uncommitted; see `git diff HEAD`).

The pre-pass is inserted inside `_run_batch_with_progress` at lines **376–418** (working tree):

```python
# --- Pre-pass: resolve every URL to its output path before dispatch (B10, Decision A) ---
_batch_extractor = VKVideoExtractor(settings=settings, backoff_coordinator=None)
_batch_selector = QualitySelector()
_resolved: list[tuple[VideoWithStreams, Stream, Path] | str | None] = [None] * len(urls)
for i, url in enumerate(urls):
    try:
        _video = await _batch_extractor.extract_streams(url)
        _stream = _batch_selector.select(_video.streams, quality)
        _resolved[i] = (
            _video,
            _stream,
            _resolve_output_file(_video, output, settings, i),   # ← line 390
        )
    except (...) as exc:
        _resolved[i] = _status
        ...
```

**Confirmed:**
- The pre-pass **does** call `_resolve_output_file` for each URL (line 390).
- The warning **is** suppressed there: `_resolve_output_file` → `validate_output_path(..., warning=False)` (security.py:111).
- B2 option (a) means the warning should fire here. The fix is at the `_resolve_output_file` call site (remove `warning=False`), which covers **both** the batch pre-pass and the single-URL `download` path (since both go through `_resolve_output_file`).

### Tier 2 filename-collision dedup (lines 404–418)
The pre-pass also performs last-wins filename dedup:
```python
_filename_registry: dict[Path, int] = {}
for i, entry in enumerate(_resolved):
    if isinstance(entry, str) or entry is None:
        continue
    _, _, resolved_path = entry
    if resolved_path in _filename_registry:
        _loser = _filename_registry[resolved_path]
        ...reporter.finish_task(_loser, ProgressStatus.SKIPPED)...
    _filename_registry[resolved_path] = i
```

### `DownloadContext` changes (working tree)
`DownloadContext` gained `video_data` and `selected_stream` fields (lines 109–110) so the pre-pass can hand buffered extraction forward to `_download_single` → `download_video`, avoiding a re-extraction.

### `_download_single` changes (working tree)
Lines 193–194 read `video_data`/`selected_stream` from context; lines 252–253 pass them to `download_video`.

### `download_video` changes (working tree, `downloader.py`)
Gained `video_data`/`selected_stream` keyword-only params (line 290–291). When both are provided (line 336), `extract_streams` is skipped and `video_data` is used directly. The `stream` is forwarded as `selected_stream` to `perform_download` (lines 365–366).

### `enums.py` changes (working tree)
`ProgressStatus.SKIPPED` docstring updated to mention "Tier 1 (exact-URL duplicate) or Tier 2 (resolved-filename collision, last-wins)". This is a docstring-only change; the member value `"skipped"` is unchanged.

---

## 5. All call sites of `validate_output_path` and `_resolve_output_file` across `src/`

### `validate_output_path` — 3 direct call sites (grep confirmed)

| # | File | Line | Call | `warning` arg | Fires? |
|---|---|---|---|---|---|
| 1 | `utils/security.py` (inside `_resolve_output_file`) | 111 | `validate_output_path(output_path, warning=False)` | `False` | **No** |
| 2 | `services/segment_downloader.py` (inside `download_hls_with_resume`) | 1205 | `validate_output_path(request.output_file)` | default `True` | **Yes** |
| 3 | `services/ytdlp_downloader.py` (inside `download_with_ytdlp_with_resume_fallback`, retry-loop probe) | 909 | `validate_output_path(output_file, warning=False)` | `False` | **No** |

**Summary:** 1 site fires (default), 2 sites suppress (`warning=False`).

### `_resolve_output_file` — 2 call sites (grep confirmed)

| # | File | Line | Context |
|---|---|---|---|
| 1 | `services/downloader.py` (inside `download_video`) | 360 | Single-URL `download` path AND batch path (via `_download_single`) |
| 2 | `services/batch_downloader.py` (inside pre-pass) | 390 | B10 pre-pass — resolves every URL before dispatch |

Both call sites pass through to `validate_output_path(..., warning=False)` at security.py:111, so **both suppress the warning**.

### Import sites (not call sites)

| File | Line | |
|---|---|---|
| `services/segment_downloader.py` | 23 | `from ..utils.security import validate_output_path` |
| `services/ytdlp_downloader.py` | 46 | `from ..utils.security import validate_output_path` |
| `services/downloader.py` | 23 | `from ..utils.security import _resolve_output_file, sanitize_title` |
| `services/batch_downloader.py` | 37 | `from ..utils.security import _resolve_output_file` |

`utils/__init__.py` is a **docstring-only** module (confirmed at line 1: `"""Utility modules for VK Video Downloader."""` — no `__all__`, no re-exports).

---

## 6. The loader path traced end-to-end

The default loader path (yt-dlp, `DownloadMethod.AUTO` or `YTDLP`) is:

```
cli.download
  → download_video (downloader.py:394 → 360)
      → _resolve_output_file (security.py:111) → validate_output_path(warning=False)  ← suppressed
  → perform_download (downloader.py:368)
      → download_with_ytdlp_with_resume_fallback (ytdlp_downloader.py:229)
          → _download_with_ytdlp (subsystem spawn)
          [on retry, line 909:] validate_output_path(output_file, warning=False)  ← suppressed
          [on partial file + token refresh:] _attempt_segment_resume → download_hls_with_resume
              → validate_output_path(request.output_file)  ← default warning=True  ← FIRES
```

The warning fires **only** on the segment-fallback path (`download_hls_with_resume`), which is the non-default path entered only when yt-dlp fails and partial output exists. On the default loader path (both the initial resolution in `download_video` and the retry-loop probe in `download_with_ytdlp_with_resume_fallback`), the warning is **suppressed** at both sites.

---

## 7. The warning message (current)

**Code:** `security.py:78–83`
```python
logger.warning(
    "output_path_inside_repository",
    path=str(resolved),
    repo_root=str(repo_root),
    error_code="output_path_in_root",
)
```

| Attribute | Value |
|---|---|
| Event name | `"output_path_inside_repository"` |
| Log level | `WARNING` |
| Logger | `structlog.get_logger("vkdownloader.utils.security")` (module-level `logger = get_logger(__name__)` at line 12) |
| Structured fields | `path` (resolved absolute path), `repo_root` (the derived root), `error_code` (literal `"output_path_in_root"`) |
| Trigger condition | `resolved.relative_to(repo_root)` succeeds **and** `warning` is `True` |
| Channel | structlog JSON sink (configured by `config.setup_logging`) — the warning reaches whatever sink the structured logger is configured with (stderr, file, or rich console), not `typer.echo` |

No human-readable prose message is attached to the `logger.warning` call — the event name and fields *are* the message. The `error_code` field duplicates the plan's `ErrorCode` enum conceptually but is a plain string literal, not the enum.

---

## 8. Answers to the key questions for B2

### Q: How many call sites pass `warning=True` (or default) vs `warning=False`?
- **1** passes default (`warning=True`): `segment_downloader.py:1205`
- **2** pass `warning=False`: `security.py:111` (inside `_resolve_output_file`) and `ytdlp_downloader.py:909` (retry-loop probe)

### Q: What does the warning message look like currently?
- Event: `output_path_inside_repository`
- Level: WARNING via structlog
- Fields: `path`, `repo_root`, `error_code="output_path_in_root"`
- No prose message; the event name + structured fields are the payload.

### Q: Does the single-URL `download` command pass through `validate_output_path`?
- **Indirectly, yes.** `cli.download` → `download_video` → `_resolve_output_file` → `validate_output_path(warning=False)`. The warning is **suppressed** on this path. No direct `validate_output_path` call exists in `cli.py`.

### Q: The B10 → B2 edge — what needs to change so the warning fires through the pre-pass?
- **Change 1:** In `_resolve_output_file` (security.py:111), remove `warning=False` → use default `warning=True`. This single change covers both the B10 pre-pass (`batch_downloader.py:390`) and the single-URL `download` path (`downloader.py:360`), since both call `_resolve_output_file`.
- **Change 2:** In `ytdlp_downloader.py:909` (the retry-loop probe), remove `warning=False` → default. This is the second suppression site.
- **No change** to `segment_downloader.py:1205` — it already uses the default and fires.
- Per B2 option (a) "warn everywhere," **all three** call sites should fire. After the two changes above, the warning fires at every `validate_output_path` call.
- B1 is committed; the pre-pass (B10) is in the working tree. The `B10 → B2` edge means B2 should change the `_resolve_output_file` call (security.py:111), not re-add the warning at `batch_downloader.py:390` — B10 is restructuring the pre-pass and that call site should not be touched by B2.

### Q: Is `repo_root` still wrong (one level too deep)?
- **Yes.** `Path(__file__).resolve().parent.parent.parent` yields `C:\py_exp\mko_vkideo\src`, not `C:\py_exp\mko_vkideo`. The fix is **one additional `.parent`** (four total). This is B2's domain and is mandatory regardless of option (a) or (b) for the suppression question — a wrong root means the warning fires only under `src/` and stays silent everywhere else in the repo, which is the whole of the guard's observable behaviour under Decision B.

---

## 9. Test coverage note (for B2's Validator)

`tests/test_security.py::TestValidateOutputPath::test_path_inside_repo_warns` (lines 57–78) **mocks `Path.resolve`**, returning a `MagicMock` whose `relative_to` always succeeds. It asserts `mock_logger.warning.assert_called_once()` with `path` and `repo_root` kwargs. **This mock replaces the entire `repo_root` derivation** — the test cannot detect that `repo_root` points one level too deep. A B2 oracle must assert the derivation **by value** (e.g., that a path under the repo root but outside `src/` warns, and a path under `src/` still warns), using the real `repo_root`, not a mock. This is plan §3.3 item 3 and §6.3 mechanical verification (ii) and (iii).
