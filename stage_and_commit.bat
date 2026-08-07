@echo off
cd /d C:\py_exp\mko_vkideo

echo Step 1: Stage all changes
git add -A

echo.
echo Step 2: Show staged changes
git status --short

echo.
echo Step 3: Creating commit
git commit -m "refactor: improve error message and logging clarity

Structlog processor chain improvements (config.py):
- Add merge_contextvars for context variable propagation
- Add format_exc_info for richer exception logging
- Add UnicodeDecoder for robust encoding handling
- Use utc=True for consistent UTC timestamps

ErrorCode StrEnum with structured exception attributes (enums.py, exceptions.py):
- ErrorCode enum for consistent error classification
- VKDownloadError base with error_code, status_label(), user_message(), log_context()
- Replace raw ValueError with typed domain exceptions

InvalidVideoUrlError replacing ValueError in URL parsing (exceptions.py, extractor.py):
- Dedicated exception for URL parsing failures
- Clearer error context and classification

hide_input_in_errors on Settings (config.py):
- Prevent sensitive input from being exposed in error messages

Correlation ID utility module (utils/correlation.py):
- New module for request tracing across extract/select/download pipeline

quality.py ValueError replacement:
- Replace ValueError with QualityNotAvailableError"

echo.
echo Step 4: Confirm commit
git log --oneline -1

pause
