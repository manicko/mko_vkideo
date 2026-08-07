# Modern Python Error Handling, Logging & Exception Design — 2025–2026 Research Report

**Scope:** Python 3.12+ / structlog 25+ / FastAPI 0.110+ / Pydantic v2.  
**Codebase context:** `mko_vkideo` (VK Video Downloader) — a Typer CLI using structlog, Pydantic v2, `StrEnum`, Python 3.12. No FastAPI currently, but recommendations cover both the existing CLI and a prospective FastAPI layer.

## Confidence & Verification

| Finding | Confidence | Source |
|---|---|---|
| structlog production processor chain | **HIGH** | structlog 26.1.0 official docs — "Rendering within structlog" + "Logging Best Practices" |
| `merge_contextvars` must be first processor | **HIGH** | structlog 26.1.0 "Context Variables" + "Logging Best Practices" |
| Pydantic v2 `ValidationError.errors()` shape | **HIGH** | pydantic.dev official docs — "Error Handling" |
| FastAPI handler signature `@app.exception_handler` | **HIGH** | fastapi.tiangolo.com official tutorial + reference |
| PEP 678 `add_note()` | **HIGH** | peps.python.org |
| PEP 654 ExceptionGroup / `except*` | **HIGH** | peps.python.org |
| RFC 7807 / 9457 Problem Details | **HIGH** | rfc-editor.org |
| "Raise low, catch high" principle | **HIGH** | Real Python best practices |

---

## 1. Executive Summary & Codebase Findings

The codebase already follows several modern conventions:

- **Custom exception hierarchy** with a `VKDownloadError` base class and structured subclasses (`QualityNotAvailableError` carrying `requested`/`available` fields). ✅ aligns with best practice.
- **structlog** is configured with `BoundLogger`, `LoggerFactory`, `TimeStamper`, `JSONRenderer`/`ConsoleRenderer`, and `cache_logger_on_first_use`. ✅
- **`StrEnum`** used for all constants (`LogLevel`, `DownloadMethod`). ✅
- **`logger.exception()` / `logger.warning(..., exc_info=...)`** used to capture tracebacks. ✅
- Security-conscious logging: `_strip_auth_params` used to avoid leaking tokens in log messages. ✅
- **No `print()`** — rule explicitly enforced. ✅

**Gaps identified vs. 2025–2026 best practices:**

1. The structlog processor chain is **missing `structlog.contextvars.merge_contextvars`** as the first processor. Without it, context variables (correlation/request IDs) bound via `bind_contextvars` are silently dropped. This is the single most important modern addition.
2. The chain is **missing `structlog.processors.format_exc_info`** (or equivalent) — unhandled exceptions logged via `logger.exception()` won't get structured tracebacks in JSON output.
3. The existing exception hierarchy uses a **dict-based dispatch** (`_EXCEPTION_STATUS_HANDLERS`) instead of polymorphic methods on the exceptions themselves. A cleaner pattern is to give each exception a `status_code` / `error_code` attribute and a `to_dict()` method.
4. There is **no correlation-ID infrastructure** — every batch download operation is untraceable end-to-end across worker threads.
5. No FastAPI layer exists yet — the FastAPI recommendations below are forward-looking templates.

---

## 2. Structured Error-Handling Patterns

### 2.1 Raise Low, Catch High (Real Python)

> Let lower-level functions raise exceptions; catch them at the **edges** of the program (CLI entry point, web handler, event loop).

The codebase **already does this correctly** (`cli.py` catches `QualityNotAvailableError`, `VideoNotFoundError`, `VKDownloadError`, `Exception` at the CLI boundary). Keep this pattern; never bury `try/except` in the middle of business logic.

### 2.2 Catch Specific, Then Broad

The codebase's `_download_single` already follows this: `asyncio.CancelledError` → re-raise; `QualityNotAvailableError` → structured; `Exception` → log + fallback. ✅

```python
try:
    result = await download_video(...)
except asyncio.CancelledError:
    raise                      # Always re-raise cancellation
except QualityNotAvailableError as e:
    return (url, "", _map_exception_to_status(e))
except VKDownloadError as e:
    return (url, "", _map_exception_to_status(e))
except Exception as e:
    logger.exception("unexpected_error_in_batch_download", url=_strip_auth_params(url))
    return (url, "", _map_exception_to_status(e))
```

### 2.3 Exception Groups (PEP 654) for Concurrent Work

The batch download path uses `asyncio.as_completed` + manual `gather`. **Modern recommendation (2025–2026):** migrate to `asyncio.TaskGroup` + `except*`. This surfaces *all* failures instead of masking later ones.

**Before (current pattern hides concurrent failures):**
```python
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Recommended (Python 3.12+, structured concurrency):**
```python
import asyncio

async def _run_batch(urls: list[str], ...) -> tuple[list[DownloadResult], int]:
    results: list[DownloadResult] = []
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(_download_single(url, ...), name=f"dl-{url}")
            for url in urls
        ]
    # If any task raises, TaskGroup cancels siblings and raises ExceptionGroup

# Caller handles it:
try:
    await _run_batch(urls, ...)
except* VideoNotFoundError as eg:
    for exc in eg.exceptions:
        logger.error("batch_video_not_found", url=str(exc))
except* QualityNotAvailableError as eg:
    for exc in eg.exceptions:
        logger.error("batch_quality_error", requested=exc.requested)
except* VKDownloadError as eg:
    for exc in eg.exceptions:
        logger.error("batch_download_error", error=str(exc))
```

**Key rules for `except*`:**
- Each `except*` branch handles **every matching** sub-exception (not just the first).
- Unmatched exceptions are **re-raised** as a smaller group — never silently swallowed.
- `CancelledError` and `KeyboardInterrupt` are **not** wrapped in a group; they propagate directly.

### 2.4 `add_note()` (PEP 678) for Contextual Metadata

Use `add_note()` to attach diagnostic context (e.g., "retry attempt 2/3", "token was 34s old") to an exception *without* changing its type. Notes appear in tracebacks but are not structured data — store structured data as exception **attributes** instead.

```python
try:
    result = await _download_with_ytdlp(...)
    if result is None:
        exc = DownloadError(f"yt-dlp failed for {video_id}")
        exc.add_note(f"retry_count={retry_count}")
        exc.add_note(f"yt-dlp returncode={getattr(proc, 'returncode', 'n/a')}")
        raise exc
except DownloadError:
    # ... fallback to segment download ...
    raise
```

> **Rule:** Prefer `add_note()` when you want to annotate an exception with human-readable debugging info for a traceback. Prefer exception **attributes** when downstream code needs to read the value programmatically.

---

## 3. Exception Design — Custom Hierarchies (2025–2026)

### 3.1 Base Exception Carries Structured Metadata

The codebase's `QualityNotAvailableError` is a good example — it carries `requested: str` and `available: list[str]` as attributes and the CLI reads them directly (`e.requested`, `e.available`) instead of parsing the message string. **This is the recommended pattern.**

**Recommended enhancement** — give every exception an `error_code` and `status_code`:

```python
# src/vkdownloader/exceptions.py
from __future__ import annotations

class VKDownloadError(Exception):
    """Base exception for all application-domain errors.

    Attributes:
        error_code: Stable, machine-readable code for client/programmatic use.
        status_code: HTTP status if this were raised in an API context.
        user_message: Human-readable message safe to show to end users.
    """
    error_code: str = "INTERNAL_ERROR"
    status_code: int = 500
    user_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, error_code: str | None = None) -> None:
        super().__init__(message or self.user_message)
        if error_code is not None:
            self.error_code = error_code

    def to_dict(self) -> dict[str, object]:
        """Serialize to a structured dict for logging/API responses."""
        return {
            "error": self.error_code,
            "message": str(self),
        }


class VideoNotFoundError(VKDownloadError):
    error_code = "VIDEO_NOT_FOUND"
    status_code = 404
    user_message = "The requested video could not be found."


class QualityNotAvailableError(VKDownloadError):
    error_code = "QUALITY_NOT_AVAILABLE"
    status_code = 422
    user_message = "The requested quality is not available."

    requested: str
    available: list[str]

    def __init__(self, requested: str, available: list[str], message: str | None = None) -> None:
        self.requested = requested
        self.available = available
        if message is None:
            if not available:
                message = "No streams found for this video; it may be private or unavailable."
            else:
                message = (
                    f"Quality '{requested}' not available. "
                    f"Available: {', '.join(available)}"
                )
        super().__init__(message)
        # Attach structured context as attributes (not in the message string)
        self.context = {"requested": requested, "available": available}

    def to_dict(self) -> dict[str, object]:
        return {
            "error": self.error_code,
            "message": str(self),
            "requested": self.requested,
            "available": self.available,
        }
```

### 3.2 Exception Hierarchy — One Base, Semantic Subclasses

```
Exception
└── VKDownloadError              # base; catches everything app-related
    ├── VideoNotFoundError       # 404 equivalent
    ├── QualityParseError        # 422 — invalid input
    ├── QualityNotAvailableError # 422 — valid input, unavailable resource
    ├── ExtractionError          # 502 — upstream failure
    ├── DownloadError            # 502 — download transport failure
    └── ConfigError              # 500/503 — configuration failure
```

**Do not** subclass built-in `ValueError`/`TypeError` for business errors — it couples domain logic to stdlib types and makes FastAPI handler registration ambiguous. The codebase already raises `ValueError` from `parse_video_id` for URL validation; in a FastAPI context this should become a domain exception.

### 3.3 Replace Dict-Based Dispatch with Polymorphism

The current `_EXCEPTION_STATUS_HANDLERS` dict works but is fragile — adding a new exception requires editing a separate mapping. Replace with a method on the base class:

```python
class VKDownloadError(Exception):
    ...
    def status_label(self) -> str:
        """Return a stable status label for batch reporting."""
        return self.error_code.lower()

class QualityNotAvailableError(VKDownloadError):
    ...
    def status_label(self) -> str:
        if not self.available and self.requested:
            return f"no_streams:{self.error_code.lower()}"
        return f"{self.error_code.lower()}:requested={self.requested}"
```

Then `_map_exception_to_status(exc)` simply becomes `exc.status_label()`.

---

## 4. Logging Best Practices — structlog (2025–2026)

### 4.1 Production Processor Chain (Verified)

The structlog 26.1.0 official docs specify this canonical chain when rendering within structlog (interoperating with stdlib `logging`):

```python
# src/vkdownloader/logging_config.py
import logging
import sys
import structlog


def configure_structlog(dev_mode: bool = False, log_level: int = logging.INFO) -> None:
    """Configure structlog for production (JSON) or development (console) output.

    Call ONCE at application startup, before any get_logger() calls.
    """
    shared_processors = [
        # MUST be first: pulls structlog.contextvars bound vars into the event dict
        structlog.contextvars.merge_contextvars,
        # Add log level as a structured field
        structlog.stdlib.add_log_level,
        # Human-readable ISO 8601 timestamp in UTC
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Render exception info as a structured dict (not a formatted string)
        structlog.processors.format_exc_info,
        # Decode bytes → str (prevents serialization errors in JSON output)
        structlog.processors.UnicodeDecoder(),
    ]

    if dev_mode:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to pass through structlog's format
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
```

### 4.2 What the Existing Code Is Missing

The current `setup_logging` in `config.py`:

```python
# CURRENT — incomplete chain
processors=[
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.JSONRenderer() if settings.log_file else structlog.dev.ConsoleRenderer(),
],
```

**Missing:** `merge_contextvars` (context propagation won't work) and `format_exc_info` (tracebacks logged via `logger.exception()` are lost in JSON mode). This is the **highest-priority fix**.

### 4.3 Canonical Log Lines

structlog docs recommend minimizing log noise to **one structured log line per logical operation** (the "Canonical Log Line" pattern from Stripe). Each line carries all the context needed to trace the operation.

Apply this to the download pipeline:

```python
# Instead of many scattered log.info() calls, emit one rich log at key milestones:
logger.info(
    "download.completed",
    video_id=video.id,
    url=_strip_auth_params(url),
    quality=str(quality),
    method=str(method),
    output=str(output_file),
    duration_seconds=round(duration, 2),
    file_size=output_file.stat().st_size,
)
```

### 4.4 Log Levels — When to Use What

| Level | When | The codebase |
|---|---|---|
| `DEBUG` | Diagnostic, high-volume, off in prod | ✅ Used (`parsed_video_id`, `simulating_video_interaction`) |
| `INFO` | Business milestones, request lifecycle | ✅ Used (`extracting_streams`, `download_completed`) |
| `WARNING` | Recoverable issue, needs attention | ✅ Used (`ytdlp_extraction_error`, `ssl_verification_disabled`) |
| `ERROR` | Failure requiring investigation | ✅ Used (`ffmpeg_download_failed`, `max_retries_exceeded`) |
| `CRITICAL` | System is down | ⚠️ Not used (rarely needed in CLI) |

**Rule:** If everything is `ERROR`, nothing is. Reserve `ERROR` for actual failures, not expected conditions like "quality not available."

### 4.5 Never Log Sensitive Data

The codebase already uses `_strip_auth_params(url)` before logging URLs — extend this practice:
- Never log cookies, tokens, full headers.
- Use `repr()`-free structured fields; structlog handles serialization.
- For `ValidationError` input values: use `hide_input_in_errors` in FastAPI (see §6).

### 4.6 Async Logging

structlog offers `await logger.ainfo(...)` (async variants) for non-blocking logging in async code. For the batch downloader where yt-dlp runs in a thread pool, the current sync `logger.info()` is fine — but for any **pure async path**, prefer the `a`-prefixed methods to avoid blocking the event loop on I/O-heavy rendering.

---

## 5. FastAPI HTTP Exception Handling (Forward-Looking Template)

Since the project may add an API layer, here are the 2025–2026 best practices verified against FastAPI 0.116+ docs.

### 5.1 Custom Exceptions Inherit from `Exception` (Not `HTTPException`)

```python
# src/vkdownloader/api/exceptions.py
class AppError(Exception):
    """Base error for application-domain failures.

    Business logic raises these; FastAPI handlers translate them to HTTP.
    """
    def __init__(self, message: str, *, error_code: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
```

### 5.2 Register Global Handlers (Decoupled from Routes)

```python
# src/vkdownloader/api/error_handlers.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.error(
            "app_error",
            path=str(request.url),
            method=request.method,
            error_code=exc.error_code,
            error=str(exc),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://api.example.com/errors/{exc.error_code.lower()}",
                "title": "Application Error",
                "status": exc.status_code,
                "detail": exc.message,
                "instance": str(request.url),
            },
            headers={"X-Request-ID": _get_request_id(request)},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("validation_error", path=str(request.url), errors=exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "type": "https://api.example.com/errors/validation-failed",
                "title": "Validation Failed",
                "status": 422,
                "detail": "Request body or parameters failed validation.",
                "errors": [
                    {
                        "field": ".".join(str(p) for p in err["loc"] if p != "body"),
                        "code": err["type"],
                        "message": err["msg"],
                    }
                    for err in exc.errors()
                ],
            },
            headers={"X-Request-ID": _get_request_id(request)},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = _get_request_id(request)
        logger.error(
            "unhandled_exception",
            path=str(request.url),
            error_type=type(exc).__name__,
            error=str(exc),
            exc_info=True,
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=500,
            content={
                "type": "https://api.example.com/errors/internal-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred. Reference ID: " + correlation_id,
                "instance": str(request.url),
            },
            headers={"X-Request-ID": correlation_id},
        )
```

### 5.3 RFC 7807 / Problem Details (Recommended for APIs)

Use the `application/problem+json` shape. Verified fields: `type` (URI), `title` (short summary), `status` (int), `detail` (this instance), `instance` (URI). Add `correlation_id` / extension fields for domain context.

> **Never** return raw stack traces to clients. Log them server-side; return a reference ID.

### 5.4 Override Starlette's `HTTPException` for Unified Handling

FastAPI's `HTTPException` inherits from Starlette's. Register the handler on **Starlette's** `HTTPException` so you catch both:

```python
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://api.example.com/http/{exc.status_code}",
            "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url),
        },
        headers={"X-Request-ID": _get_request_id(request), **(exc.headers or {})},
    )
```

### 5.5 FastAPI Constructor: `exception_handlers` Dict

FastAPI accepts a dict at construction time:

```python
app = FastAPI(
    exception_handlers={
        AppError: app_error_handler,
        RequestValidationError: validation_handler,
        StarletteHTTPException: http_exception_handler,
        Exception: unhandled_handler,  # catch-all, must be last conceptually
    },
)
```

**Pitfall:** The generic `Exception` handler must not shadow more specific handlers — FastAPI resolves handlers most-specific-first, so this is safe, but a bare `except Exception` in route code that swallows and re-raises as `HTTPException` will bypass your domain handlers. Avoid catching-and-re-raising generically inside routes.

---

## 6. Pydantic v2 Error Handling (2025–2026)

### 6.1 The Stable Contract: `type` + `loc`

Verified against pydantic.dev official docs. `ValidationError.errors()` returns `ErrorDetails`:

```python
{
    "type": "greater_than",      # ✓ stable contract (machine-readable)
    "loc": ("gt_int",),         # ✓ stable contract (field path)
    "msg": "Input should be greater than 42",  # ✗ display-only; changes between versions
    "input": 21,                 # ⚠️ contains raw user input — PII risk
    "ctx": {"gt": 42},           # context for message interpolation
    "url": "https://errors.pydantic.dev/...",
}
```

**Rule:** Never build client-facing logic on `msg`. Key on `type` + `loc` for programmatic handling and localization.

### 6.2 Never Return Raw `ValidationError` to Clients

```python
from pydantic import ValidationError

def format_validation_error(e: ValidationError) -> dict[str, object]:
    """Convert Pydantic ValidationError to a safe, stable API envelope."""
    return {
        "type": "validation-failed",
        "title": "Validation Failed",
        "status": 422,
        "detail": "One or more fields failed validation.",
        "errors": [
            {
                "field": ".".join(str(p) for p in err["loc"] if p != "body"),
                "code": err["type"],          # stable
                "message": err["msg"],        # human-readable (can be localized)
            }
            for err in e.errors()
        ],
    }
```

### 6.3 Prevent Input Leakage (Security)

The `input` field in `ErrorDetails` contains **raw user-supplied data**. Passwords, credit cards, tokens will leak into responses and logs.

```python
# Pydantic v2: suppress input in error responses
class SafeModel(BaseModel):
    model_config = ConfigDict(
        hide_input_in_errors=True,  # removes `input` from errors()
    )

# Or programmatically when inspecting errors:
e.errors(include_input=False)    # Pydantic v2.5+
e.errors(include_url=False)     # drop the pydantic docs URL too
```

The codebase already redacts received values in `_format_validation_error` (`<redacted>`); elevate this to the model level with `hide_input_in_errors=True`.

### 6.4 Custom Validator Errors: Use `ValueError` or `PydanticCustomError`

In validators, **never use `assert`** — Python strips `assert` statements under `python -O`. The codebase's `validate_cookie_source` uses `ValueError`, which is correct.

```python
from pydantic import field_validator, PydanticCustomError

class Settings(BaseSettings):
    @field_validator("throttled_rate")
    @classmethod
    def validate_throttle(cls, v: int) -> int:
        if v < 1000:
            raise PydanticCustomError(
                "value_error.throttle_too_low",
                "throttled_rate must be at least 1000 bytes/sec (got {value})",
                {"value": v},
            )
        return v
```

`PydanticCustomError` lets you assign a **stable `type`** and a **templated `msg`** — this is how you get i18n via a dictionary keyed on `type`.

### 6.5 WrapValidator for Friendly Fallback Messages

A `mode="wrap"` validator lets you intercept validation, attempt correction, and return a friendlier message on failure:

```python
from typing import Annotated
from pydantic import WrapValidator, ValidationInfo

def _coerce_quality(v: str, handler: ..., info: ValidationInfo) -> QualityEnum:
    # Try the raw value first
    try:
        return handler(v)
    except ValueError:
        # Strip "p" suffix and retry
        try:
            return handler(v.rstrip("p"))
        except ValueError:
            raise PydanticCustomError(
                "quality_parse",
                "Invalid quality '{input}'. Use one of: 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p, best, worst.",
                {"input": v},
            )

QualityField = Annotated[QualityEnum, WrapValidator(_coerce_quality)]
```

---

## 7. Error Message Design Principles

### 7.1 Separate Machine Code from Human Message

| Field | Purpose | Audience |
|---|---|---|
| `error_code` / `type` | Stable, programmatic | Systems, clients |
| `message` / `msg` | Human-readable | End users, devs |
| `detail` | Instance-specific context | Debugging |
| `instance` / `correlation_id` | Traceability | Support |

The codebase already separates these well: `VideoNotFoundError` has a stable message but could expose an `error_code`.

### 7.2 Error Messages Should Be Actionable

**Bad:** `"No streams found"`
**Good:** `"No streams found for this video; the video may be private or unavailable."`

The codebase's `QualityNotAvailableError` message (`f"Quality '{requested}' not available. Available: {available}"`) is a good example — it tells the user exactly what went wrong and what options they have.

### 7.3 User-Facing vs. Developer-Facing Messages

- **User-facing:** Short, no internal details, suggests an action ("Check the URL and try again"). The codebase's CLI messages (`"Video not found. Verify the URL is correct and the video is public."`) are good.
- **Log-level:** Full detail with field values, trace IDs, retry counts.
- **API responses:** Return `error_code` + generic `detail`; put specifics in logs.

### 7.4 Localization Considerations (2025–2026)

Pydantic v2 has **no built-in i18n**. The standard approach (verified from tomodahinata.com guide, June 2026):

1. Keep `type` (e.g., `int_parsing`, `greater_than`) as the **stable key**.
2. Maintain a `dict[str, str]` mapping from `type` → translated message per locale.
3. Apply client-side or via a `convert_errors()` function before serialization.

```python
MESSAGES_TR = {
    "int_parsing": "Geçerli bir tamsayı girin.",
    "greater_than": "Değer {gt} veya daha büyük olmalı.",
    "missing": "Bu alan gereklidir.",
}

def localize_errors(e: ValidationError, lang: str = "en") -> list[dict]:
    messages = MESSAGES_TR if lang == "tr" else MESSAGES_EN
    return [
        {
            "field": ".".join(str(p) for p in err["loc"] if p != "body"),
            "code": err["type"],
            "message": messages.get(err["type"], err["msg"]).format(**(err.get("ctx") or {})),
        }
        for err in e.errors(include_input=False)
    ]
```

This keeps `type` and `loc` as the contract; message text is swapped per locale.

---

## 8. Logging Context — Correlation IDs & Request Context

### 8.1 The structlog ContextVars Pattern (Verified)

This is the modern, async-safe way to propagate correlation IDs:

```python
# src/vkdownloader/logging_setup.py
import sys
import uuid
import logging
import structlog

def setup_logging_with_correlation() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # pulls bound contextvars
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not _is_tty() else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
```

### 8.2 CLI Correlation ID

For the batch downloader, generate one correlation ID per batch run and bind it:

```python
import uuid
from structlog.contextvars import clear_contextvars, bind_contextvars

def _run_batch_with_progress(urls, ...):
    correlation_id = str(uuid.uuid4())
    clear_contextvars()
    bind_contextvars(correlation_id=correlation_id, batch_size=len(urls))

    logger.info("batch.started", correlation_id=correlation_id)
    # ... all downstream logs now include correlation_id ...
```

For per-URL tracing, bind a `video_id` context that gets merged:

```python
from structlog.contextvars import bound_contextvars

async def _download_single(url, ...):
    video_id = extract_id(url)
    with bound_contextvars(video_id=video_id, correlation_id=correlation_id):
        # ... all log calls inside this block carry video_id + correlation_id
        await download_video(url, ...)
```

### 8.3 FastAPI Correlation ID Middleware

```python
from fastapi import FastAPI, Request
import structlog.contextvars
import uuid

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    # Extract from header or generate
    cid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=cid,
        path=request.url.path,
        method=request.method,
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = cid
    return response
```

### 8.4 Thread Safety (Critical for yt-dlp Integration)

The codebase's progress callbacks fire from yt-dlp's **thread-pool executor** (`loop.run_in_executor`), not from the asyncio event loop thread. `contextvars` are **not automatically propagated** across thread boundaries.

**Recommendation:** When binding a `video_id` for logging in a thread, pass it explicitly to the thread function and bind it inside the thread, or use `contextvars.copy_context()` to explicitly propagate:

```python
import contextvars

async def _download_with_ytdlp(...):
    ctx = contextvars.copy_context()
    result = await loop.run_in_executor(
        None,
        lambda: ctx.run(_sync_download, ydl_opts, video_id_for_context),
    )
```

Inside `_sync_download`, bind the contextvars so logs from that thread carry the `video_id`.

---

## 9. Concrete Recommendations for This Codebase

### Priority 1 (Immediate — fix logging chain)

Add `merge_contextvars` and `format_exc_info` to the processor chain in `config.py`:

```python
# In setup_logging(), modify the processors list:
processors=[
    structlog.contextvars.merge_contextvars,    # ADD — enables correlation IDs
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.format_exc_info,       # ADD — structured tracebacks in JSON
    structlog.processors.JSONRenderer() if settings.log_file else structlog.dev.ConsoleRenderer(),
],
```

### Priority 1 (Immediate — correlation ID for batches)

In `cli.py`'s `_run_batch_with_progress`, generate and bind a correlation ID:

```python
import uuid
from structlog.contextvars import clear_contextvars, bind_contextvars, bound_contextvars

async def _run_batch_with_progress(urls, ...):
    batch_correlation_id = str(uuid.uuid4())
    clear_contextvars()
    bind_contextvars(correlation_id=batch_correlation_id)
    logger.info("batch.started", url_count=len(urls))
    ...
```

And in `_download_single`, bind per-URL context:
```python
with bound_contextvars(video_id=_strip_video_id(url)):
    ...download logic...
```

### Priority 2 (Refactor exceptions to carry metadata)

Add `error_code`, `status_code`, and `user_message` to `VKDownloadError`; give each subclass a stable code. Replace `_map_exception_to_status` with a `status_label()` method on each exception.

### Priority 3 (Async migration)

Consider migrating `_run_batch_with_progress` from `asyncio.as_completed` + `gather(return_exceptions=True)` to `asyncio.TaskGroup` + `except*` for proper exception-group handling. This surfaces all concurrent failures and integrates with `CancelledError` propagation more cleanly.

### Priority 4 (FastAPI layer — if added)

If an API is introduced:
- Reuse the existing `VKDownloadError` hierarchy as the **domain** exception base.
- Register FastAPI handlers that catch `VKDownloadError` subclasses and return **Problem Details** (`application/problem+json`) with `type`, `title`, `status`, `detail`, `instance`, plus a `correlation_id` from context.
- Use `hide_input_in_errors=True` on all Pydantic models exposed to the API boundary to prevent input leakage.
- Add `bind_contextvars(request_id=...)` middleware (above).
- Log full tracebacks server-side with `logger.error(..., exc_info=True)`; return only a reference ID to the client.

---

## 10. Code Templates (Copy-Paste Ready)

### Template A: Modern Exception Base (with structured metadata)

```python
from __future__ import annotations

class AppError(Exception):
    """Base for all application-domain errors.

    Subclasses set class-level constants; instantiation may add context.
    """
    error_code: str = "INTERNAL_ERROR"
    status_code: int = 500
    user_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)

    def to_dict(self) -> dict[str, object]:
        return {"error": self.error_code, "message": str(self)}
```

### Template B: structlog Production Configuration

```python
import logging, sys, structlog

def configure_logging(dev: bool = False) -> None:
    base = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    structlog.configure(
        processors=base + [
            structlog.dev.ConsoleRenderer() if dev else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
```

### Template C: FastAPI Problem-Details Handler

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception",
            path=str(request.url), error_type=type(exc).__name__,
            exc_info=True,
        )
        return JSONResponse(500, {
            "type": "https://api.example.com/errors/internal-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred.",
            "instance": str(request.url),
        })
```

---

## 11. Anti-Patterns to Avoid (2025–2026)

| Anti-Pattern | Correct Approach |
|---|---|
| `logging.basicConfig()` in library code | Libraries: add only `NullHandler`; apps: configure at entry point |
| `print()` for diagnostics | Use `logger.debug()` or `logger.info()` |
| Bare `except:` or `except Exception:` in business logic | Catch specific types; let `Exception` bubble to the boundary |
| `assert` in validators | Use `raise PydanticCustomError(...)` or `raise ValueError(...)` |
| Parsing error message strings for logic | Store structured fields on exception attributes |
| Returning raw `ValidationError` to clients | Convert to stable envelope (`type` + `loc` + `code`) |
| Logging full request bodies / cookies | Use `_strip_auth_params` or redaction fields |
| `raise X from None` when context matters | Use `add_note()` to preserve traceback context |
| `asyncio.gather(return_exceptions=True)` for batch ops | Use `TaskGroup` + `except*` to surface all failures |
