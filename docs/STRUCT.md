# Project Structure

Source layout of the `vkdownloader` package. Build artifacts (`__pycache__`,
`.pyc`, `.egg-info`) are excluded — they are generated at runtime and should
not be used as the source of truth for the project structure.

```
src/
└── vkdownloader/
    ├── __init__.py
    ├── __main__.py              # `python -m vkdownloader` entry point
    ├── cli.py                   # Typer CLI commands (thin entry layer)
    ├── config.py                # Settings model, logging, env validation
    ├── exceptions.py            # Domain exceptions + legacy status mapping
    ├── stealth.min.js           # Anti-bot browser evasion stub
    ├── infrastructure/
    │   ├── __init__.py
    │   ├── browser.py           # Playwright-based browser cookie extraction
    │   └── network_monitor.py   # Download rate watchdog
    ├── models/
    │   ├── __init__.py
    │   ├── dtos.py              # Data transfer objects (Stream, StreamInfo)
    │   ├── enums.py             # StrEnum constants (Quality, Method, CookieSource, etc.)
    │   └── video.py             # Video metadata dataclass
    ├── services/
    │   ├── __init__.py
    │   ├── batch_downloader.py  # Batch orchestration (ConcurrencyTracker, _TrackedSemaphore, run_batch)
    │   ├── concurrency.py       # Concurrency primitives (re-export / compatibility)
    │   ├── cookies.py           # Browser cookie acquisition and Netscape formatting
    │   ├── downloader.py        # Single-video download pipeline (download_video)
    │   ├── downloader_throttle.py # Adaptive throttling (ProgressManager, URLBackoffCoordinator, get_shutdown_event)
    │   ├── extractor.py         # Stream extraction (VKVideoExtractor, is_valid_video_url)
    │   ├── ffmpeg_utils.py      # FFmpeg discovery and stream concatenation
    │   ├── progress_display.py   # RichProgressReporter (multi-line batch progress display)
    │   ├── quality.py           # Quality selection (QualitySelector)
    │   ├── segment_downloader.py # HTTP segment downloader with retries
    │   └── signal_handlers.py   # SIGINT/SIGTERM handler registration
    └── utils/
        ├── __init__.py          # Exports sanitize_url_for_log, _strip_auth_params, validate_output_path
        ├── correlation.py       # Correlation ID binding (structlog contextvars)
        ├── formatting.py        # Human-readable byte-size rendering (format_bytes)
        ├── security.py          # Security utilities (output path validation, title sanitization)
        └── url_sanitizer.py     # URL redaction (_strip_auth_params, sanitize_url_for_log)
```

## Layering

- **Entry layer**: `cli.py`, `__main__.py` — argument parsing, Settings construction, error presentation, exit codes. No business logic or private-symbol imports from service/utils layers.
- **Service layer**: `services/` — streaming download orchestration, stream extraction, quality selection, throttling, batch coordination. Imports private symbols from `utils/` internally.
- **Models layer**: `models/` — Pydantic/StrEnum definitions shared with services and entry layer.
- **Utils layer**: `utils/` — low-level helpers (URL sanitization, correlation IDs, security validation, byte-size formatting).
- **Infrastructure layer**: `infrastructure/` — Playwright browser automation, network monitoring.
