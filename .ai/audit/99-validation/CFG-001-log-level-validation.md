---
name: CFG-001-log-level-validation
description: Research for log_level field validation in Settings model
agent: researcher
status: complete
validated: yes
---

# CFG-001 Implementation Recommendation: Log Level Validation for Settings Model

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py, src/vkdownloader/models/enums.py |
| **Classification** | advisory |

## Problem Analysis

### Current State
- `log_level: str = Field(default="INFO")` in `Settings` class (src/vkdownloader/config.py:91-94)
- `logging.getLevelName(settings.log_level)` used in `setup_logging()` (line 122)
- **Critical Issue**: `logging.getLevelName()` accepts ANY string, returning `"Level {string}"` for invalid levels instead of raising an error

### Runtime Evidence
```python
>>> logging.getLevelName('INFO')      # Valid
20
>>> logging.getLevelName('INVALID')   # Invalid - NO ERROR raised!
'Level INVALID'
```

When an invalid log level reaches `structlog.make_filtering_bound_logger()`, it raises `TypeError` because it expects an `int`, not a `str`.

## Project Architecture Context

### Enum Pattern Usage
The project already uses `StrEnum` for all domain constants (src/vkdownloader/models/enums.py):
- `DownloadMethod` - download method selection
- `CookieSource` - cookie acquisition strategy
- `QualityEnum` - video quality options
- `StreamFormat` - stream format types
- `DownloadStatus` - download states

**Pattern Consistency**: Using `StrEnum` aligns with existing project conventions (Rule #10: "StrEnum for All Constants").

### Settings Model Pattern
Other settings fields use `Field()` constraints:
- `max_retries: int = Field(default=3, ge=1, le=10)` - range validation
- `download_method: DownloadMethod = Field(default=DownloadMethod.AUTO)` - enum type

## Research: Pydantic v2 Validation Options

### Option 1: StrEnum + field_validator (Recommended)

**Source**: Pydantic v2 field_validator mode='before' for case-insensitive normalization, verified via Context7

```python
from enum import StrEnum
from pydantic import field_validator

class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Settings(BaseSettings):
    log_level: LogLevel = Field(default=LogLevel.INFO)
    
    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str | LogLevel) -> LogLevel:
        if isinstance(v, LogLevel):
            return v
        return LogLevel(v.upper())  # Raises ValueError if invalid
```

**Pros**:
- Consistent with existing project pattern (Rule #10)
- Case-insensitive input support (users can pass "info", "INFO", "Info")
- Automatic validation with clear error messages from Pydantic
- String values work directly with `logging.getLevelName()` via `.value` property

**Cons**:
- Slightly more code than pure enum approach

### Option 2: Literal Type (Rejected)
**Source**: Pydantic official documentation - Context7 query confirmed

Same as before - inconsistent with project enum pattern.

### Option 3: field_validator alone (Rejected)
Same as before - does not follow project StrEnum pattern.

## Recommended Solution

**Use StrEnum with field_validator(mode='before') for case-insensitive normalization**. This combines:
1. The project's established `StrEnum` pattern for constants
2. Case-insensitive input support (users can pass "info", "INFO", "Info")
3. Automatic ValidationError for invalid values

### Implementation

**src/vkdownloader/models/enums.py** - Add to existing file:
```python
class LogLevel(StrEnum):
    """Standard logging level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
```

**src/vkdownloader/config.py** - Modify Settings:
```python
from pydantic import field_validator
from vkdownloader.models.enums import CookieSource, DownloadMethod, LogLevel

class Settings(BaseSettings):
    # ... existing fields ...
    
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    
    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str | LogLevel) -> LogLevel:
        if isinstance(v, LogLevel):
            return v
        return LogLevel(v.upper())  # Raises ValueError if invalid
```

**src/vkdownloader/config.py** - Update `setup_logging()`:
```python
def setup_logging(settings: Settings | None = None) -> None:
    """Configure structlog for the application."""
    if settings is None:
        settings = Settings()
    
    # Convert enum to integer level for structlog
    level_value = logging.getLevelName(settings.log_level.value)
    
    structlog.configure(
        processors=[...],
        wrapper_class=structlog.make_filtering_bound_logger(level_value),
        ...
    )
```

**src/vkdownloader/models/__init__.py** - Update exports:
```python
from .enums import DownloadStatus, LogLevel, QualityEnum, StreamFormat

__all__ = [
    # ... existing exports ...
    "LogLevel",
]
```

Add test case in `tests/test_config.py`:
```python
def test_log_level_validation() -> None:
    """Test log_level rejects invalid values and accepts valid ones."""
    from vkdownloader.models.enums import LogLevel
    
    # Valid log levels - case insensitive
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        s = Settings(log_level=level)
        assert s.log_level == LogLevel[level]
    
    # Lowercase input also works
    s = Settings(log_level="info")
    assert s.log_level == LogLevel.INFO
    
    # Invalid log level raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        Settings(log_level="INVALID")
    assert "log_level" in str(exc_info.value)
```

## Confidence Level: HIGH

- Pydantic v2 enum behavior verified via Context7 documentation
- `logging.getLevelName()` behavior verified at runtime
- Project pattern consistency verified by codebase inspection
- **Test Impact**: Existing tests in `test_config.py` lines 23 and 51 compare `settings.log_level == "INFO"` - these will need updating to `settings.log_level == LogLevel.INFO` or `settings.log_level.value == "INFO"` after implementation