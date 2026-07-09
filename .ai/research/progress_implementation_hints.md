# FFmpeg Progress Implementation Hints

## Current Code Issue (downloader.py:72-78)

```python
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)

stdout, stderr = await process.communicate()  # BLOCKING: waits for completion
```

**Problem**: `communicate()` собирает весь вывод и ждёт завершения процесса. Невозможно отследить прогресс.

## Solution Pattern

### 1. FFmpeg Command Modification
```python
def _build_ffmpeg_cmd(
    self, m3u8_url: str, output_file: Path, cookies: str | None = None
) -> list[str]:
    cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""
    headers = f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n{cookie_part}"

    cmd = [
        "ffmpeg",
        "-y",
        "-progress", "pipe:2",  # Progress to stderr
        "-nostats",             # No stats to stdout (keep clean)
        "-headers",
        headers,
        "-i",
        m3u8_url,
        "-c",
        "copy",
        str(output_file),
    ]
    return cmd
```

### 2. Async Progress Reader (Python 3.10+)
```python
import asyncio
from dataclasses import dataclass
from typing import Optional

@dataclass
class FfmpegProgress:
    frame: Optional[int] = None
    fps: Optional[float] = None
    speed: Optional[float] = None  # multiplier (e.g., 1.2x)
    total_size: Optional[int] = None
    out_time_us: Optional[int] = None
    progress: Optional[str] = None  # "continue" or "end"

class ProgressParser:
    @staticmethod
    def parse_line(line: str) -> tuple[str, str] | None:
        if "=" in line:
            key, value = line.strip().split("=", 1)
            return key, value
        return None

async def read_progress(stderr: asyncio.StreamReader) -> AsyncIterator[FfmpegProgress]:
    progress = FfmpegProgress()
    while True:
        line = await stderr.readline()
        if not line:
            break
        parsed = ProgressParser.parse_line(line.decode())
        if parsed:
            key, value = parsed
            if key == "frame":
                progress.frame = int(value) if value != "N/A" else None
            elif key == "speed":
                # Parse "1.2x" -> 1.2
                progress.speed = float(value.rstrip("x")) if value != "N/A" else None
            elif key == "total_size":
                progress.total_size = int(value) if value != "N/A" else None
            elif key == "out_time_us":
                progress.out_time_us = int(value) if value != "N/A" else None
            elif key == "progress":
                progress.progress = value
                yield progress
                if value == "end":
                    break
                progress = FfmpegProgress()  # Reset for next block
```

### 3. Integration with Tqdm
```python
async def download_with_ffmpeg(
    self, m3u8_url: str, output_file: Path, quality: str = "best", cookies: str | None = None
) -> Path | None:
    cmd = self._build_ffmpeg_cmd(m3u8_url, output_file, cookies)
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    # Create progress bar
    pbar = tqdm(total=100, desc="Downloading", unit="%")
    
    async def monitor_progress():
        async for prog in read_progress(process.stderr):
            if prog.out_time_us and hasattr(self, '_duration_ms'):
                percent = min(100, (prog.out_time_us / 1000) / self._duration_ms * 100)
                pbar.n = percent
                if prog.speed:
                    pbar.set_postfix(speed=f"{prog.speed}x")
                pbar.refresh()
    
    await process.wait()
    pbar.close()
    
    return output_file if process.returncode == 0 else None
```

### 4. Getting Video Duration (Optional for ETA)
```python
async def get_video_duration(m3u8_url: str) -> Optional[int]:
    """Get duration in milliseconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        m3u8_url
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if stdout:
        return int(float(stdout.decode()) * 1000)
    return None
```

---

## Key FFmpeg Progress Fields Reference

| Key | Format | Example | Meaning |
|-----|--------|---------|---------|
| frame | int | `frame=120` | Frames processed |
| fps | float | `fps=30.00` | Output FPS |
| speed | string | `speed=1.2x` | Speed multiplier relative to realtime |
| total_size | int | `total_size=524288` | Bytes written to output |
| out_time_us | int | `out_time_us=4000000` | Microseconds processed |
| out_time_ms | int | `out_time_ms=4000000` | Milliseconds processed |
| out_time | string | `out_time=00:00:04.000000` | Human-readable time |
| progress | string | `progress=continue` | Block terminator (`continue` or `end`) |
| bitrate | string | `bitrate=1024.5kbits/s` | Current bitrate |
| dup_frames | int | `dup_frames=0` | Duplicate frames |
| drop_frames | int | `drop_frames=0` | Dropped frames |