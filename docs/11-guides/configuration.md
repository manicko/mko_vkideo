---
id: configuration-guide
domain: guide
tags:
  - config
  - yaml
  - settings
  - telethon
  - monitoring
related:
  - cli-reference
---

# Configuration Guide

**Applies to:** `mko-telebot` v0.1+

This document describes all configuration files used by mko-telebot: their locations, schema, field descriptions, path resolution rules, and how sensitive values are handled.

---

## Table of Contents

1. [File Locations & Path Resolution](#file-locations--path-resolution)
2. [`config.yaml` — Monitoring Configuration](#configyaml--monitoring-configuration)
3. [`secrets.yaml` — Telethon API Credentials](#secretsyaml--telethon-api-credentials)
4. [`log_config.yaml` — Logging Configuration](#log_configyaml--logging-configuration)
5. [SecretStr Handling](#secretstr-handling)
6. [Validation Rules](#validation-rules)
7. [Example Files](#example-files)

---

## File Locations & Path Resolution

### Default Package Settings

The application ships with default config files inside the package at:

```
src/mko_telebot/settings/
├── config.yaml
├── secrets.yaml
└── log_config.yaml
```

These are templates. **Do not edit them in-place** — they are overwritten on package upgrades.

### User Config Directory

User-specific config files live in the platform-specific user config directory, resolved via [`platformdirs`](https://pypi.org/project/platformdirs/):

| Platform | Path |
|----------|------|
| Linux    | `~/.config/mko_telebot/settings/` |
| macOS    | `~/Library/Application Support/mko_telebot/settings/` |
| Windows  | `C:\Users\<USER>\AppData\Local\mko_telebot\mko_telebot\settings\` |

The application creates the following subdirectory structure:

```
<mko_telebot_user_dir>/
├── settings/
│   ├── config.yaml          ← User overrides for monitoring
│   ├── secrets.yaml         ← Telethon credentials (sensitive)
│   ├── log_config.yaml      ← Logging configuration
│   ├── state/               ← Persistent application state
│   └── sessions/            ← Telethon session files
└── logs/                    ← Log output files
```

### Path Resolution Rules

The `TelepostConfigReader` resolves paths in the following order:

1. **Home-directory expansion:** `~` / `~user` in paths is expanded first via `Path.expanduser()`.
2. **Absolute paths:** If the path is already absolute (starts with `/` or drive letter), it is used as-is.
3. **Relative paths:** Resolved against the **user settings directory** (`~/.config/mko_telebot/settings/` by default).
4. **Log file paths:** Relative `filename` values in `log_config.yaml` handlers are resolved against the **log directory** (`~/.config/mko_telebot/logs/`).

If a required file is missing, `ConfigError` is raised with the file path in the error message.

### Automatic Config Selection

The `TelepostConfigReader.from_user_dir()` factory method automatically sets up paths pointing to the user config directory:

| Property | Default Path |
|----------|-------------|
| `config_path` | `<user_dir>/config.yaml` |
| `secrets_path` | `<user_dir>/secrets.yaml` |
| `log_config_path` | `<user_dir>/log_config.yaml` |

---

## `config.yaml` — Monitoring Configuration

This file defines the **MONITORING** section of the application — which channels to watch, how often to scan, and how to filter/forward messages.

### Top-Level Structure

```yaml
MONITORING:
  channels_delay: <int>
  channels:
    DEFAULTS:
      scan_interval: <int>
      stagger_start_seconds: <int>
      history_limit: <int>
      history_days: <int | null>
      overlap: <int>
      forward_to: <list[str]>
      keywords: <list[str]>
    <channel_name>:
      ...
```

The root key `MONITORING` maps to `ChatsConfig` in the Pydantic model. The `DEFAULTS` key inside `channels` is automatically removed during validation and its values applied as defaults — it does **not** represent a real channel.

### Field Reference

#### `ChatsConfig` (top-level monitoring)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `channels_delay` | `int` | `30` | Delay in seconds between successive channel scans. Minimum: 1. |
| `channels` | `dict` | _required_ | Map of channel name → `ChannelConfig`. See below. |
| `defaults` | `ChannelDefaults` | `{}` | Default settings inherited by every channel. Configurable via `DEFAULTS` key (see ChannelDefaults). |

#### `ChannelDefaults`

Applied to every channel that does not override a given field. Configurable inside the `channels` dict under the special `DEFAULTS` key.

| Field | Type | Default | Valid Range | Description |
|-------|------|---------|-------------|-------------|
| `scan_interval` | `int` | `420` | ≥ 60 | Interval in seconds between scanning the channel for new messages. |
| `stagger_start_seconds` | `int` | `5` | ≥ 0 | Stagger offset in seconds to distribute initial scan start times across channels. |
| `history_limit` | `int` | `50` | ≥ 1 | Maximum number of historical messages to fetch on first scan. |
| `history_days` | `int` or `null` | `null` | any positive int | Number of days of historical messages to fetch. `null` means no day-based limit. |
| `overlap` | `int` | `5` | ≥ 1 | Number of overlapping messages between consecutive scans — avoids gaps from messages arriving during a scan. |
| `forward_to` | `list[str]` | `[]` | — | List of target entities (channel @username, chat ID, or t.me link) to forward matched messages to. |
| `keywords` | `list[str]` | `[]` | — | Keyword patterns for filtering messages. Only messages matching at least one keyword are forwarded. An empty list forwards all messages. |

#### `ChannelConfig` (per-channel entry)

Each key inside `channels` (except `DEFAULTS`) defines a monitored channel. All fields from `ChannelDefaults` apply here, plus:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | _required_ | Channel identifier — can be a Telegram @username, a `t.me/...` link, or a numeric chat ID. This field is typically inferred from the dict key, but can be set explicitly for custom display names. |

All other fields (`scan_interval`, `history_limit`, `history_days`, `overlap`, `forward_to`, `keywords`) default to the values set in `DEFAULTS` if not explicitly overridden.

---

## `secrets.yaml` — Telethon API Credentials

This file holds the **TELETHON_API** section — credentials needed to connect to Telegram via the Telethon library.

### Top-Level Structure

```yaml
TELETHON_API:
  is_user: <bool>
  phone_or_token: "<str>"
  max_retries: <int>
  client:
    session: "<str>"
    api_id: <int>
    api_hash: "<str>"
    device_model: "<str>"
    system_version: "<str>"
    system_lang_code: "<str>"
    lang_code: "<str>"
```

The root key `TELETHON_API` maps to `TelethonConfig` in the Pydantic model.

### Field Reference

#### `TelethonConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `is_user` | `bool` | `true` | `true` = authenticate as a user account (phone-based auth). `false` = authenticate as a bot (bot token auth). |
| `phone_or_token` | `str` (SecretStr) | _required_ | Phone number with country code (e.g. `+79123456789`) for user accounts, or bot token (e.g. `123456:ABC-DEF1234...`) for bots. Stored as a SecretStr — see [SecretStr Handling](#secretstr-handling). Minimum length: 5 characters. |
| `max_retries` | `int` | `5` | Maximum number of retry attempts when sending messages fails. Valid range: 1–20. |
| `client` | `ClientConfig` | _required_ | Telethon client configuration (see below). |

#### `ClientConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `session` | `str` | `"first_session"` | Session name or path. Determines the session file name used by Telethon to persist authentication. |
| `api_id` | `int` | _required_ | Telegram API ID. Obtain from [my.telegram.org/apps](https://my.telegram.org/apps). Must be a positive integer. The placeholder value `12345` is rejected. |
| `api_hash` | `str` (SecretStr) | _required_ | Telegram API hash. Obtain from [my.telegram.org/apps](https://my.telegram.org/apps). Stored as a SecretStr. Minimum length: 1, max length: 64. Values starting with `YOUR_` are rejected as placeholders. |
| `device_model` | `str` or `null` | `null` | Device model string sent to Telegram (optional). Values starting with `YOUR_` are rejected. |
| `system_version` | `str` or `null` | `null` | System version string sent to Telegram (optional). Values starting with `YOUR_` are rejected. |
| `system_lang_code` | `str` or `null` | `null` | System language code (e.g. `en-US`). |
| `lang_code` | `str` or `null` | `null` | Telegram interface language code (e.g. `ru`). |

---

## `log_config.yaml` — Logging Configuration

This file follows the standard Python [`logging.config.dictConfig()`](https://docs.python.org/3/library/logging.config.html#logging-config-dictconfig) format wrapped in a `LOGGING` key.

### Top-Level Structure

```yaml
LOGGING:
  version: 1
  disable_existing_loggers: false
  formatters:
    <formatter_name>:
      class: "logging.Formatter"
      format: "<format_string>"
      datefmt: "<date_format>"
  handlers:
    <handler_name>:
      class: "<handler_class>"
      level: "<LEVEL>"
      formatter: "<formatter_name>"
      # Handler-specific kwargs...
  loggers:
    <logger_name>:
      level: "<LEVEL>"
      handlers: [<handler_name>, ...]
      propagate: <bool>
  root:
    level: "<LEVEL>"
    handlers: [<handler_name>, ...]
```

### Field Reference

| Section | Description |
|---------|-------------|
| `version` | Always `1`. Reserved for schema versioning. |
| `disable_existing_loggers` | Set to `false` to avoid silencing third-party loggers. |
| `formatters` | Map of formatter name → formatter config. Each uses `class: "logging.Formatter"` with optional `format` and `datefmt` strings. |
| `handlers` | Map of handler name → handler config. Supports any Python `logging.Handler` subclass. Common handlers: `logging.StreamHandler`, `logging.handlers.RotatingFileHandler`. Handler kwargs are passed directly to the class constructor. |
| `loggers` | Map of logger name → logger config. Each specifies `level`, `handlers`, and `propagate`. |
| `root` | Root logger configuration (fallback for all unconfigured loggers). |

### Default Handlers

| Handler | Class | Level | Description |
|---------|-------|-------|-------------|
| `console` | `logging.StreamHandler` | `INFO` | Outputs to stdout (`ext://sys.stdout`). |
| `rotating_file` | `logging.handlers.RotatingFileHandler` | `INFO` | Writes to a file with rotation at 2 MB (`maxBytes: 2000000`), keeping 2 backups (`backupCount: 2`). Encoding: UTF-8. |

### Default Loggers

| Logger | Level | Handlers | Propagate |
|--------|-------|----------|-----------|
| `__main__` | `INFO` | `rotating_file` | `false` |
| `tests` | `INFO` | `rotating_file` | `false` |
| `telebot` | `INFO` | `console`, `rotating_file` | `false` |
| _root_ | `INFO` | `console`, `rotating_file` | — |

### Path Resolution for Log Files

Handler `filename` values that are relative paths are automatically resolved against the application log directory (`~/.config/mko_telebot/logs/`). For example, `filename: "log.log"` becomes `~/.config/mko_telebot/logs/log.log`.

---

## SecretStr Handling

Sensitive fields use Pydantic's [`SecretStr`](https://docs.pydantic.dev/latest/concepts/fields/#secret-fields) type:

| Field | Location | Purpose |
|-------|----------|---------|
| `phone_or_token` | `secrets.yaml` → `TELETHON_API.phone_or_token` | Phone number or bot token |
| `api_hash` | `secrets.yaml` → `TELETHON_API.client.api_hash` | Telegram API hash |

### How SecretStr Works

- **In memory:** The value is stored as a `SecretStr` object. Accessing the string through standard attribute access returns `'**********'` — the actual value is hidden.
- **Retrieving the value:** To get the plaintext value in code, call `.get_secret_value()` on the field.
- **Serialization:** By default, `SecretStr` fields serialize as `'**********'` in model dumps unless explicitly configured to show the value.
- **No encryption in transit:** `SecretStr` masks values in logs, error messages, and serialized output. It does **not** encrypt or decrypt data — the raw value is stored in memory.

### Placeholder Detection

The application rejects placeholder values to prevent accidental use of template credentials:

- **api_id:** The value `12345` is rejected as a template placeholder.
- **api_hash:** Any value starting with `YOUR_` is rejected.
- **phone_or_token:** Any value starting with `YOUR_` is rejected.
- **device_model, system_version, session:** Any value starting with `YOUR_` is rejected.

If any field fails validation, a `ConfigError` with a descriptive message is raised during `load()`.

---

## Validation Rules

The configuration is validated against Pydantic v2 models when `TelepostConfigReader.load()` is called. The validation pipeline:

1. **Required files check** — both `config.yaml` and `secrets.yaml` must exist.
2. **YAML parsing** — both files are parsed with `yaml.safe_load()`. Malformed YAML raises `ConfigError`.
3. **Deep merge** — `secrets.yaml` is merged into `config.yaml` (secrets values win on conflict).
4. **Pydantic validation** — the merged dict is validated against `TelepostSettings`, which recursively validates:
   - `TelethonConfig` (from `TELETHON_API` key)
   - `ClientConfig` (from `TELETHON_API.client` key)
   - `ChatsConfig` (from `MONITORING` key)
5. **Model validators** run custom checks:
   - `DEFAULTS` key is removed from the `channels` dict after defaults are applied
   - Placeholder values are rejected (see [SecretStr Handling](#secretstr-handling))

### Common Validation Errors

| Error | Cause |
|-------|-------|
| `Required config file not found` | Missing `config.yaml` in user settings dir |
| `Required secrets file not found` | Missing `secrets.yaml` in user settings dir |
| `Configuration file not found` | Missing file at the specified path |
| `Malformed YAML in configuration file` | Syntax error in YAML |
| `api_hash appears to be a placeholder value` | `api_hash` value starts with `YOUR_` |
| `api_id value 12345 is a template placeholder` | `api_id` is still the template value |
| `phone_or_token appears to be a placeholder value` | `phone_or_token` value starts with `YOUR_` |

---

## Example Files

### Minimal `config.yaml`

```yaml
MONITORING:
  channels_delay: 30
  channels:
    DEFAULTS:
      scan_interval: 420
      stagger_start_seconds: 5
      history_limit: 50
      history_days: 2
      overlap: 5
      forward_to: []
      keywords: []
```

### Full `config.yaml` with Multiple Channels

```yaml
MONITORING:
  channels_delay: 30
  channels:
    DEFAULTS:
      scan_interval: 420
      stagger_start_seconds: 5
      history_limit: 50
      history_days: 2
      overlap: 5
      forward_to: []
      keywords: []

    my_channel:
      name: "@my_channel"
      scan_interval: 300
      keywords:
        - "alert"
        - "important"
      forward_to:
        - "@admin_chat"

    another_channel:
      name: "https://t.me/another_channel"
      history_days: 7
      forward_to:
        - 123456789
```

### Minimal `secrets.yaml`

```yaml
TELETHON_API:
  is_user: true
  phone_or_token: "+79123456789"
  max_retries: 5
  client:
    session: "my_session"
    api_id: 12345
    api_hash: "your_actual_api_hash_here"
    device_model: null
    system_version: null
    system_lang_code: "en-US"
    lang_code: "ru"
```

### Full `secrets.yaml` (User Account)

```yaml
TELETHON_API:
  is_user: true
  phone_or_token: "+79123456789"
  max_retries: 5
  client:
    session: "my_session"
    api_id: 123456
    api_hash: "0123456789abcdef0123456789abcdef"
    device_model: "PC"
    system_version: "Windows 10"
    system_lang_code: "en-US"
    lang_code: "ru"
```

### Full `secrets.yaml` (Bot)

```yaml
TELETHON_API:
  is_user: false
  phone_or_token: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
  max_retries: 5
  client:
    session: "my_bot_session"
    api_id: 123456
    api_hash: "0123456789abcdef0123456789abcdef"
    device_model: null
    system_version: null
    system_lang_code: "en-US"
    lang_code: "ru"
```

### Full `log_config.yaml`

```yaml
LOGGING:
  version: 1
  disable_existing_loggers: false
  formatters:
    basic:
      class: "logging.Formatter"
      format: "%(asctime)s - %(levelname)s - %(message)s - %(name)s"
      datefmt: "%d-%m-%y %I:%M:%S %p"
  handlers:
    console:
      class: "logging.StreamHandler"
      formatter: "basic"
      level: "INFO"
      stream: "ext://sys.stdout"
    rotating_file:
      class: "logging.handlers.RotatingFileHandler"
      level: "INFO"
      formatter: "basic"
      filename: "log.log"
      maxBytes: 2000000
      backupCount: 2
      encoding: "utf-8"
  loggers:
    __main__:
      handlers:
        - "rotating_file"
      level: "INFO"
      propagate: false
    tests:
      level: "INFO"
      handlers:
        - "rotating_file"
      propagate: false
    telebot:
      level: "INFO"
      handlers:
        - "console"
        - "rotating_file"
      propagate: false
  root:
    level: "INFO"
    handlers:
      - "console"
      - "rotating_file"
```