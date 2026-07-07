# VK Video Downloader Module - Recommendations & Improvements (Part 5)

## 1. Priority Variant Selection

### 1.1 Recommended Primary Approach: Browser-First with ffmpeg Direct Download

**Обоснование выбора:**
- **Надежность**: VK API недокументирован и часто меняется - браузерный подход стабилен
- **Поддерживаемость**: Селекторы проще поддерживать чем reverse-engineering API
- **Экономия ресурсов**: ffmpeg напрямую вместо сборки сегментов на Python
- **Современные практики 2026**: Playwright + stealth наиболее актуальны для anti-detection

### 1.2 Архитектурные варианты (приоритет от повышенной надежности к экспериментальным):

| Вариант | Надежность | Скорость | Сложность | Приоритет |
|---------|-----------|----------|-----------|-----------|
| Browser → ffmpeg direct | ★★★★★ | ★★★★☆ | ★★☆☆☆ | **ПРИОРИТЕТНЫЙ** |
| Hybrid (API → browser) | ★★★★☆ | ★★★★★ | ★★★★☆ | Phase 2 optimization |
| aria2 parallel download | ★★★★☆ | ★★★★★ | ★★★☆☆ | Optional dependency |

## 2. Modern Anti-Detection Improvements (2026)

### 2.1 Playwright Stealth Enhancements

Based on current best practices for bypassing VK's bot detection:

```python
# src/vkdownloader/infrastructure/stealth.py
import json
from playwright.async_api import async_playwright

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });
window.chrome = { runtime: {} };
const originalPermissions = window.navigator.permissions.query;
window.navigator.permissions.query = (function(permission) {
    if (permission === 'notifications') { return Promise.resolve({ state: 'default' }); }
    return originalPermissions(permission);
});
"""

async def create_stealth_context(playwright, settings):
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir="",
        headless=settings.headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ],
        user_agent=settings.user_agent,
        viewport={"width": 1920, "height": 1080},
        locale="ru-RU",
        timezone_id="Europe/Moscow",
    )
    return context
```

**Key improvements:**
- Use `launch_persistent_context` with real Chrome profile when possible
- Add timezone and locale matching user context
- Remove all automation-specific browser properties
- Disable sandbox in headless mode for reliability

### 2.2 Network Interception Strategy

```python
# src/vkdownloader/infrastructure/network_monitor.py
import re
from typing import Optional

class NetworkMonitor:
    # Extended patterns based on VK's current API structure
    M3U8_PATTERNS = [
        re.compile(r"https?://[^/]*vk[^/]*/video/.*\.m3u8"),
        re.compile(r"https?://[^/]*vk[^/]*/powerproxy/.*"),
        re.compile(r"https?://cdn.*\.m3u8"),
        re.compile(r"https?://[^/]*\.vkcdn.*\?url=.*"),
    ]
    
    JSON_PATTERNS = [
        re.compile(r"https://vkvideo\.ru/api/video"),
        re.compile(r"https://vk\.com/api/video"),
        re.compile(r"https://vk\.com/al_video\.php"),
        re.compile(r"https://vkvideo\.ru/method/video"),
    ]

    def __init__(self, page):
        self.page = page
        self.stream_urls: list[str] = []
        self.video_metadata: dict = {}
        self._setup_interceptors()

    def _setup_interceptors(self):
        self.page.on("response", self._intercept_response)

    async def _intercept_response(self, response):
        url = response.url
        for pattern in self.M3U8_PATTERNS:
            if pattern.match(url):
                self.stream_urls.append(url)
        
        for pattern in self.JSON_PATTERNS:
            if pattern.match(url):
                try:
                    data = await response.json()
                    self._extract_streams_from_json(data)
                except:
                    pass
```

## 3. HLS Download Strategy Improvements

### 3.1 Direct HLS to MP4 Conversion (Recommended)

**Instead of downloading segments separately, use ffmpeg directly:**

```python
# src/vkdownloader/services/hls_downloader.py
import asyncio
import aiohttp
from pathlib import Path

class HLSDownloader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None

    async def download_with_ffmpeg(self, m3u8_url: str, output_file: Path, quality: str):
        """Download HLS stream using ffmpeg - most reliable approach"""
        cmd = [
            "ffmpeg", "-y",
            "-headers", f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n",
            "-i", m3u8_url,
            "-c", "copy",
            "-metadata", f"title=VK Video {quality}p",
            str(output_file)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return output_file if process.returncode == 0 else None
```

**Advantages:**
- ffmpeg handles segment downloading, retries, and muxing
- Native HLS support in ffmpeg is more reliable
- Faster for high-quality videos
- Less memory usage

### 3.2 Alternative: Use aria2 for Parallel Downloads

For very large videos, aria2 with m3u8 support:

```python
async def download_with_aria2(self, m3u8_url: str, output_file: Path):
    cmd = [
        "aria2c",
        "--continue=true",
        "--auto-file-renaming=false",
        "--header=User-Agent: " + self.settings.user_agent,
        "--header=Referer: https://vkvideo.ru/",
        "--dir", str(output_file.parent),
        "--out", output_file.name,
        m3u8_url
    ]
    # ... execute command
```

## 4. VK API Integration (Phase 2 Enhancement)
 
### 4.1 Direct API Method

Instead of browser automation, consider VK's undocumented API:

```python
# src/vkdownloader/services/vk_api.py
import hashlib
import time
import aiohttp

class VKAPIClient:
    def __init__(self):
        self.api_endpoint = "https://vkvideo.ru/inner.php"
        
    async def get_video_info(self, owner_id: str, video_id: str, access_token: Optional[str] = None):
        """Use VK's internal API to get stream URLs"""
        params = {
            "act": "video_info",
            "oid": owner_id,
            "vid": video_id,
            "al": 1,
            "device_id": self._generate_device_id(),
        }
        # Handle authentication if needed
        # Parse response for m3u8 URLs
```

**Note:** This requires maintaining session cookies and may need regular updates as API changes.

## 5. Recommended Architecture Changes

### 5.1 Priority: Browser-First with ffmpeg

```python
# src/vkdownloader/services/extractor.py
class VKVideoExtractor:
    async def extract_streams(self, url: str) -> VideoWithStreams:
        # Primary: Browser automation with m3u8 interception
        return await self._browser_extraction(url)
```

### 5.2 Secondary: Hybrid Approach (API as optimization)

```python
# src/vkdownloader/services/extractor.py
class VKVideoExtractor:
    async def extract_streams(self, url: str) -> VideoWithStreams:
        # 1. Try direct API extraction (fast, no browser needed) - Phase 2
        try:
            result = await self._try_api_extraction(url)
            if result:
                return result
        except Exception:
            pass
        
        # 2. Fall back to browser automation (primary, reliable)
        return await self._browser_extraction(url)
```

### 5.3 Session Persistence Layer

```python
# src/vkdownloader/infrastructure/session_store.py
import json
from pathlib import Path

class SessionStore:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path / "sessions"
        self.storage_path.mkdir(exist_ok=True)

    def save_cookies(self, cookies: list[dict], video_id: str):
        with open(self.storage_path / f"{video_id}.json", "w") as f:
            json.dump({
                "cookies": cookies,
                "timestamp": time.time(),
            }, f)

    def get_cookies(self, video_id: str, max_age_hours: int = 1):
        # Return valid session cookies if available
```

## 6. Testing Improvements

### 6.1 Mock Server for Integration Tests

```python
# tests/conftest.py
from aiohttp import web

async def mock_vk_video_server():
    app = web.Application()
    
    async def mock_video_page(request):
        return web.Response(
            content_type="text/html",
            text="""
            <div class="VideoPlayer">
                <video src="https://example.com/video.m3u8"></video>
            </div>
            <script>
            window._videoConfig = {
                m3u8Url: "https://example.com/master.m3u8",
                qualities: { "240": "...", "360": "...", "720": "..." }
            };
            </script>
            """
        )
    
    async def mock_m3u8(request):
        return web.Response(
            content_type="application/vnd.apple.mpegurl",
            text="#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=1280x720\nhttps://example.com/720p.m3u8\n"
        )
    
    app.router.add_get("/video-{oid}_{vid}", mock_video_page)
    app.router.add_get("/video.m3u8", mock_m3u8)
    return app
```

### 6.2 Real Video Testing Strategy

```python
# tests/integration/test_real_videos.py
import pytest

@pytest.mark.integration
async def test_real_vk_video_extraction():
    pytest.skipif(
        not os.getenv("TEST_REAL_VIDEOS"),
        reason="Real video tests disabled by default"
    )
    extractor = VKVideoExtractor()
    streams = await extractor.extract_streams(
        "https://vkvideo.ru/video-225794656_456242637"
    )
    assert len(streams.streams) > 0
```

## 7. Configuration Improvements

### 7.1 Multi-Profile Rotation

```python
# src/vkdownloader/utils/browser_profiles.py
BROWSER_PROFILES = [
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "locale": "ru-RU",
        "timezone": "Europe/Moscow",
    },
    {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119.0.0.0 Safari/537.36",
        "locale": "ru-RU",
        "timezone": "Europe/Moscow",
    },
]

def get_random_profile() -> dict:
    return random.choice(BROWSER_PROFILES)
```

### 7.2 Rate Limiter with Dynamic Delay

```python
# src/vkdownloader/infrastructure/adaptive_throttle.py
import asyncio
import random
from collections import defaultdict

class AdaptiveThrottle:
    def __init__(self, base_rpm: int = 20, max_rpm: int = 60):
        self.base_rpm = base_rpm
        self.max_rpm = max_rpm
        self.current_delay = 2.0
        
    async def wait(self):
        delay = self.current_delay + random.uniform(0, 1)
        await asyncio.sleep(delay)
        
    def on_rate_limited(self):
        self.current_delay = min(self.current_delay * 1.5, 10.0)
        
    def on_success(self):
        self.current_delay = max(self.current_delay * 0.95, 1.0)
```

## 8. Security & Compliance Notes

### 8.1 Cookie Encryption

```python
# src/vkdownloader/infrastructure/encrypted_store.py
from cryptography.fernet import Fernet

class SecureCookieStore:
    def __init__(self, encryption_key: Optional[str] = None):
        self.key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def save_cookies(self, cookies: list[dict], video_id: str):
        encrypted = self.cipher.encrypt(json.dumps(cookies).encode())
        Path(f"{video_id}.enc").write_bytes(encrypted)
```

### 8.2 Legal Considerations

- Add user agreement acceptance
- Implement download limits per hour
- Add delay between downloads to mimic human behavior
- Provide clear attribution to source

## 9. Implementation Priority Recommendations

### Phase 1: MVP (Browser-First) - Priority Variant
1. **Basic browser automation with Playwright** - основа
2. **m3u8 interception and ffmpeg direct download** - не отдельная загрузка сегментов
3. **Simple quality selection CLI**

### Phase 2: Reliability + Optimizations
1. Session persistence
2. Retry logic with backoff
3. **Hybrid extraction (API as fallback)** - оптимизация скорости
4. Proper error handling

### Phase 3: Scale
1. Rate limiting
2. Proxy support  
3. Batch processing

### Phase 4: Advanced
1. aria2 integration (optional)
2. Account support
3. Format conversion options

## 10. Known Limitations & Mitigations

| Limitation | Mitigation | Priority |
|------------|------------|----------|
| Token expiration (1-2 hours) | Monitor and refresh tokens before expiry | High |
| Geo-restrictions | Add proxy support or error message | Medium |
| Login required videos | Implement credential management (later) | Low |
| Rate limiting | Adaptive throttling with profile rotation | High |
| Browser update breaking selectors | Use multiple selector strategies with fallbacks | High |

## 11. Quick Start Implementation Plan

```bash
# 1. Setup project
poetry init
poetry add playwright aiohttp pydantic pydantic-settings ffmpeg-python typer structlog

# 2. Create minimal extractor (start here)
# src/vkdownloader/extractor.py - basic version with browser + m3u8 interception

# 3. Test with single video
python -c "
from vkdownloader.extractor import extract_video
import asyncio
result = asyncio.run(extract_video('https://vkvideo.ru/video-225794656_456242637'))
print(result)
"
```

---

## SUMMARY OF PRIORITY DECISIONS

### Выбор приоритетного сценария:

1. **Основа (MVP)**: Browser automation + ffmpeg direct download
   - Наиболее надежный и проверенный подход
   - Не зависит от изменений недокументированного API

2. **Оптимизация (Phase 2)**: Hybrid API-first approach
   - Добавляем как улучшение после стабилизации MVP

3. **Дополнительно**: aria2 support
   - Опциональная зависимость для больших файлов

### Ключевые улучшения выбранного сценария:
- **Stealth**: Полный набор скрытия автоматизации
- **ffmpeg direct**: Нативная поддержка HLS вместо ручного сбора сегментов
- **Adaptive throttle**: Самонастраиваемый rate limiter
- **Session store**: Персистентность для авторизованных видео