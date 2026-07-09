# CLI-004: Duplicate Entry Point Analysis - main.py vs cli.py

## Research Date: 2026-07-09

## Issue Summary

Two CLI entry points exist in the project with overlapping functionality but different capabilities.

---

## Architecture Comparison

### cli.py (Registered Entry Point)
| Aspect | Details |
|--------|---------|
| Location | `src\vkdownloader\cli.py` |
| Framework | Typer (modern CLI framework) |
| Entry point | `vkdownloader = "vkdownloader.cli:cli"` in pyproject.toml |
| Commands | `download`, `batch` |
| Lines of code | 165 |
| Logging compliance | ✅ Uses `typer.echo()` for output |
| Method selection | ❌ Not available |

### main.py (Orphaned Entry Point)
| Aspect | Details |
|--------|---------|
| Location | Root level `main.py` |
| Framework | Raw `sys.argv` parsing |
| Entry point | Not registered (only via `python main.py`) |
| Commands | Single `download` via positional args |
| Lines of code | 240 |
| Logging compliance | ❌ 9+ `print()` statements (violates rule #12) |
| Method selection | ✅ Has `DownloadMethod` enum (yt-dlp, ffmpeg, auto) |

---

## Unique Functionality in main.py (NOT in cli.py)

### 1. DownloadMethod Parameter
```python
# main.py:24, 64-86
method: DownloadMethod = DownloadMethod.AUTO
# Supports: YTDLP (~100KB/s reliable), FFMPEG (~1MB/s faster), AUTO (fallback)
```

### 2. yt-dlp to Segment Resume Fallback
```python
# main.py:89-166
async def download_with_ytdlp_with_resume_fallback(...) -> Path | None:
    # 1. Try yt-dlp download
    # 2. On failure with partial file: get fresh token via browser
    # 3. Switch to segment-based resume
```

This fallback logic is critical for handling VK's expiring m3u8 tokens (documented in limitations.md).

### 3. Duplicate Calls Bug
```python
# main.py:41 (inefficient)
video_id = extractor.parse_video_id(url)[0] + "_" + extractor.parse_video_id(url)[1]
```

---

## Documentation References

### docs\11-guides\vkdownloader-limitations.md (Lines 92, 101)
```bash
# Recommended for fastest download
python main.py "VIDEO_URL" QUALITY . ffmpeg

# Recommended for most reliable download  
python main.py "VIDEO_URL" QUALITY . yt-dlp
```

Status: ✅ HIGH confidence - File explicitly references main.py for workarounds.

---

## Key Findings

1. **entry point conflict**: pyproject.toml registers `vkdownloader.cli:cli`, not main.py
2. **missing feature**: cli.py lacks DownloadMethod selection (critical workaround)
3. **rule violation**: main.py has 9 `print()` statements violating rule #12
4. **undocumented pattern**: cli.py's batch command uses `download_hls_with_resume` but main.py imports it separately (line 12)

---

## Recommended Solution: **CONSOLIDATE INTO CLI**

### Action Required:

**Option A (Recommended): Remove main.py entirely**
1. Add `method` option to cli.py `download` command using DownloadMethod enum
2. Port yt-dlp-to-segment fallback logic into service layer
3. Update documentation to use Typer CLI syntax

**Option B: Move main.py to scripts/ and add deprecation warning**
- Less preferable - maintains technical debt

---

## Implementation Requirements

If consolidating into cli.py:

```python
# New cli.py signature
@app.command()
def download(
    url: str = typer.Argument(...),
    quality: QualityEnum = typer.Option(QualityEnum.BEST),
    output: Path = typer.Option(".", "--output", "-o"),
    method: DownloadMethod = typer.Option(DownloadMethod.AUTO),  # NEW
) -> None:
    ...
```

### Functions to Port from main.py:
1. `download_video()` - core orchestration (simplified)
2. `download_with_ytdlp_with_resume_fallback()` - into downloader service
3. `_download_with_ytdlp()` - already inline-able into downloader.py

---

## Confidence Levels

| Finding | Confidence | Source |
|---------|------------|--------|
| main.py has print() violations | HIGH | Direct file inspection |
| cli.py lacks method selection | HIGH | Direct file inspection |
| Documentation references main.py | HIGH | Direct file inspection |
| main.py not registered as entry point | HIGH | pyproject.toml inspection |