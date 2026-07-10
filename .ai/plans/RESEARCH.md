# Research: FFmpeg Progress Display for Download Operations

## 1. Current Architecture Analysis

### Current Implementation (`src/vkdownloader/services/downloader.py`)
- **Method `download_with_ffmpeg`** (lines 58-86): Запускает ffmpeg через `asyncio.create_subprocess_exec` с захватом stdout/stderr, но **не выводит прогресс в реальном времени**
- **Problem**: stdout/stderr собираются только после завершения процесса через `process.communicate()`, что делает невозможным отображение скорости, процента и ETA во время загрузки

### Current Implementation (`src/vkdownloader/services/downloader.py`)
- **Method `download_hls_with_resume`** (lines 89-166): Скачивает сегменты HLS по отдельности с отображением количества скачанных сегментов
- **Progress tracking**: Частично реализован через metadata файл с `downloaded_count`, но без скорости и ETA

### CLI Integration (`src/vkdownloader/cli.py`)
- Использует `tqdm` для прогресс-бара в batch-режиме
- Только для счетчика завершённых загрузок, не для прогресса внутри каждой загрузки

### Models (`src/vkdownloader/models/video.py`)
- **DownloadProgress** (lines 39-48): Существует модель для отслеживания прогресса, но не используется в текущей реализации ffmpeg

---

## 2. Modern FFmpeg Progress Monitoring Practices (2025-2026)

### Key Finding: `-progress pipe:1` Flag

FFmpeg поддерживает машинно-читаемый формат прогресса через флаг **`-progress pipe:1`** (stdout) или **`-progress pipe:2`** (stderr).

#### Standard Progress Output Format:
```
frame=120
fps=30.00
bitrate=1024.5kbits/s
total_size=524288
out_time_us=4000000
out_time_ms=4000000
out_time=00:00:04.000000
dup_frames=0
drop_frames=0
speed=1.2x
progress=continue
```

#### Key Fields:
| Field | Description | Units |
|-------|-------------|-------|
| `frame` | Processed frames count | count |
| `fps` | Current encoding speed | frames/sec |
| `bitrate` | Current bitrate | kbits/s |
| `total_size` | Total output bytes | bytes |
| `out_time_us` | Processed time | microseconds |
| `out_time_ms` | Processed time | milliseconds |
| `speed` | Speed multiplier | X (e.g., 1.2x = 1.2x realtime) |
| `progress` | State: `continue` or `end` | - |

**Source Confidence**: HIGH - FFmpeg official documentation, FFmpeg-devel mailing list, libffmpeg Rust bindings

### Real-time Parsing Approaches:

1. **Direct subprocess with async reading** (Python stdlib)
   - Read stdout line-by-line while process runs
   - Parse KEY=VALUE pairs
   - Requires calculating percentage from `out_time_us` / total duration

2. **ffmpeg-python wrapper**
   - `run_async(pipe_stdout=True)` for background execution
   - Manual progress parsing from output

3. **Third-party libraries**:
   - **`parsed-ffmpeg`**: Provides `FfmpegStatus` with `on_status` callback, built-in percentage calculation
   - **`better-ffmpeg-progress`**: Rich/tqdm integration, automatic progress bar
   - **`yt-dlp-ffmpeg-progress`**: Fork with integrated tracking

4. **yt-dlp approach** (reference implementation):
   - Uses `FFmpegProgressTracker` с Queue+Thread pattern
   - Парсит `-progress pipe:1` вывод
   - Поддерживает ETA calculation, speed, bytes outputted

---

## 3. Priority Recommendation for Implementation

### Selected Approach: Custom Solution with `-progress pipe:1` + Real-time Parsing

**Rationale**:
1. **Надёжность**: Не требует внешних зависимостей, работает с vanilla ffmpeg
2. **Контроль**: Полный контроль над форматом вывода и расчётом процента
3. **Совместимость**: Совместим с текущей архитектурой на asyncio
4. **Прозрачность**: Явная логика парсинга, легко отлаживается

### Implementation Steps:

#### Step 1: Modify ffmpeg command to output progress
```python
# Current command (downloader.py, line 44-54)
cmd = [
    "ffmpeg",
    "-y",
    "-headers", headers,
    "-i", m3u8_url,
    "-c", "copy",
    str(output_file),
]

# Modified command with progress output
cmd = [
    "ffmpeg",
    "-y",
    "-progress", "pipe:2",  # Write progress to stderr
    "-stats",
    "-headers", headers,
    "-i", m3u8_url,
    "-c", "copy",
    str(output_file),
]
```

**Note**: `-progress pipe:2` пишет в stderr (чтобы stdout остался чистым), `-stats` включает статистику.

#### Step 2: Real-time parsing with asyncio
```python
async def download_with_ffmpeg(...) -> Path | None:
    cmd = self._build_ffmpeg_cmd(...)
    cmd.extend(["-progress", "pipe:2", "-nostats"])  # Override stats to stderr only
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    # Parse stderr in real-time while process runs
    async def parse_progress():
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            # Parse KEY=VALUE and emit progress events
            
    # Run both concurrently
    await asyncio.gather(process.wait(), parse_progress())
```

#### Step 3: Enhance DownloadProgress model
```python
class DownloadProgress(BaseModel):
    video_id: str
    downloaded_bytes: int
    total_bytes: int | None = None
    speed: float | None = None  # bytes/sec
    eta_seconds: int | None = None
    percent: float | None = None
    status: DownloadStatus
    error: str | None = None
```

#### Step 4: Integrate with tqdm for display
- Использовать существующий tqdm в CLI
- Добавить callback для обновления прогресс-бара из парсера

### Alternative Considered (Not Recommended):

| Option | Pros | Cons | Confidence |
|--------|------|------|------------|
| `ffmpeg-python` | Готовая обёртка | Нужна дополнительная зависимость, тот же самый parsing | MEDIUM |
| `parsed-ffmpeg` | Асинхронный, готовый parsing | Новая зависимость, мало звёзд на GitHub | LOW |
| `better-ffmpeg-progress` | Rich прогресс-бар | Несовместим с tqdm в проекте, Windows-специфичный | MEDIUM |

---

## 4. Key Technical Details

### ETA Calculation:
```python
# From out_time_us and speed
elapsed_ms = out_time_us / 1000
if speed > 0 and estimated_duration:
    eta_seconds = (estimated_duration - elapsed_ms) / 1000 / speed
```

### Estimated Duration Extraction:
Для HLS-потоков можно использовать ffprobe:
```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 input.m3u8
```

### Stream Copy vs Re-encode:
Текущий код использует `-c copy` (без перекодировки), поэтому:
- `speed` будет очень высоким (обычно 100+x)
- `fps` может быть 0
- `out_time_us` всё равно показывает прогресс

### ETA Calculation for HLS Streams:

Для HLS-потоков длительность можно получить двумя способами:

1. **Через ffprobe** (перед скачиванием):
```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 "input.m3u8"
```

2. **Из m3u8 плейлиста** (парсинг тега `#EXT-X-TARGETDURATION`):**
```
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
segment_0.ts
#EXTINF:10.0,
segment_1.ts
```

### Percentage Calculation:
```python
# out_time_us показывает время в микросекундах, которое обработал ffmpeg
if estimated_duration_ms:
    percent = (out_time_us / 1000) / estimated_duration_ms * 100
else:
    # Без длительности - нельзя посчитать процент
    # Можно отображать только скорость и общий размер
    pass

# ETA через скорость:
# speed=1.2x значит, что процесс идёт в 1.2x реального времени
elapsed_seconds = (time.time() - start_time)
video_processed_seconds = out_time_us / 1000000
if speed > 0:
    eta_seconds = (estimated_duration_ms / 1000 - video_processed_seconds) / speed
```

### Segment-based ETA (for HLS resume downloads):

Для метода `download_hls_with_resume` (сегментное скачивание):
- Общее количество сегментов известно из плейлиста
- Можно отображать процент: `segments_downloaded / segments_total`
- Средняя скорость: `total_bytes / elapsed_time`
- ETA: `(segments_total - segments_downloaded) * avg_segment_time`

### Speed Display Format (like yt-dlp):
```
[download] 7.0% of 535.39MiB at 190.78KiB/s ETA 44:32
```

Расчёт:
```python
downloaded_mb = total_size / (1024 * 1024)
speed_kbs = total_size / elapsed_seconds / 1024
eta_formatted = format_eta(eta_seconds)
status = f"[{percent}% of {downloaded_mb:.2f}MiB at {speed_kbs:.2f}KiB/s ETA {eta_formatted}]"
```

---

## 5. Implementation Priority

1. **HIGH**: Добавить `-progress pipe:2` к ffmpeg команде и парсить stderr в реальном времени
2. **HIGH**: Реализовать `FFmpegProgressParser` класс для парсинга KEY=VALUE вывода
3. **MEDIUM**: Интегрировать с tqdm для отображения в CLI
4. **LOW**: Добавить ETA расчёт (требует длительности видео)