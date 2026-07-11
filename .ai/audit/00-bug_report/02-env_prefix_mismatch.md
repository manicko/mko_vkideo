# Bug Report: `.env` File Prefix Mismatch with Settings Configuration

**Date:** 2026-07-11
**Severity:** High
**Affected Files:** `src\vkdownloader/config.py`, `.env`

## Problem Description

The `.env` configuration file uses `VKDOWNLOADER_` prefix for all environment variables (e.g., `VKDOWNLOADER_USER_AGENT`, `VKDOWNLOADER_COOKIE_SOURCE`), but the Settings class in `config.py` does not have `env_prefix` configured in the model_config.

## Impact

When the `.env` file is present in the project directory, importing `Settings` or running tests fails with validation errors:
- `pydantic_core._pydantic_core.ValidationError` for every field
- Error: "Extra inputs are not permitted" for fields like `vkdownloader_user_agent`, etc.

This causes:
- Tests cannot run with `.env` present
- Application cannot start with default `.env` configuration

## Root Cause

The `model_config` in `Settings` class lacks the `env_prefix` setting:

```python
model_config = {
    "env_file": ".env",
    "env_file_encoding": "utf-8",
    "extra": "forbid",
}
```

## Proposed Fix

Add `env_prefix` to `model_config`:

```python
model_config = {
    "env_file": ".env",
    "env_file_encoding": "utf-8",
    "extra": "forbid",
    "env_prefix": "VKDOWNLOADER_",
}
```

Or alternatively, rename all variables in `.env` to remove the prefix (but this would be inconsistent with pydantic-settings best practices).

## Workaround Used

For testing purposes, `.env` was temporarily renamed to allow tests to run.