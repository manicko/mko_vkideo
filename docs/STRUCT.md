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
    │   ├── quality.py           # Quality specification model (QualitySpec)
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
    │   ├── signal_handlers.py   # SIGINT/SIGTERM handler registration
    │   └── ytdlp_downloader.py  # yt-dlp subprocess wrapper (cookie artefact lifecycle, B2/R1/R2)
    └── utils/
        ├── __init__.py          # Package docstring only; no re-exports
        ├── correlation.py       # Correlation ID binding (structlog contextvars)
        ├── formatting.py        # Human-readable byte-size rendering (format_bytes)
        ├── security.py          # Security utilities (output path validation, title sanitization)
        └── url_sanitizer.py     # URL redaction & artefact redaction (_strip_auth_params, sanitize_url_for_log, sanitize_text_for_log, redact_log_event)
```

## Layering

- **Entry layer**: `cli.py`, `__main__.py` — argument parsing, Settings construction, error presentation, exit codes. No business logic or private-symbol imports from service/utils layers. Measured import cost on the post-Block-7 tree: ~660 ms (varies 625–683 ms across runs; see Block 13 commit body for the measurement command).
- **Service layer**: `services/` — streaming download orchestration, stream extraction, quality selection, throttling, batch coordination. Imports private symbols from `utils/` internally.
- **Models layer**: `models/` — Pydantic/StrEnum definitions shared with services and entry layer.
- **Utils layer**: `utils/` — low-level helpers (URL sanitization, correlation IDs, security validation, byte-size formatting).
- **Infrastructure layer**: `infrastructure/` — Playwright browser automation, network monitoring.

## Advisory — import-order inversion: `utils/security.py` → `config.py`

**`utils/security.py` imports `Settings` from `..config` at module level`.** The
inversion itself survives Block 7. What Block 7 changed is the chain that made
the inversion dangerous: `utils/__init__.py` is now a docstring-only module and
no longer eagerly imports `from .security import …`, so importing the
`vkdownloader.utils` package does **not** transitively import `config.py`.

`config.py`'s `B6` deferred import of `redact_log_event` remains in place per
this plan's scope boundaries (the deferral was not lifted here — see §1.3,
ENT-013 lazy-import refactor is OUT). With the `utils/__init__` → `.security`
chain gone, `url_sanitizer` (stdlib-only at module scope) no longer bridges
`config.py` to `security.py` through the package root, so the original
cycle's trigger path is removed even though the deferral itself was left in
place. The `B6` comment in `config.py` still describes the pre-Block-7 chain
for historical context.
