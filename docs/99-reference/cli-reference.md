---
id: cli-reference
domain: reference
tags:
  - cli
  - commands
  - usage
related:
  - configuration-guide
  - ast-editor
---

# CLI Command Reference

**Package:** `mko-telebot` — Telegram channel monitoring and keyword-based message forwarding.

The CLI is built with [Typer](https://typer.tiangolo.com/) and uses [Rich](https://rich.readthedocs.io/) for console output.

---

## Global Invocation

```bash
mko-telebot [OPTIONS] COMMAND [ARGS]...
```

The `mko-telebot` command is registered as a console script in `pyproject.toml`:

```toml
[project.scripts]
mko-telebot = "mko_telebot.cli:app"
```

| Flag | Description |
|------|-------------|
| `--help` | Show the help message listing all commands and global options. |
| `--install-completion` | Install shell completion for the current shell. |
| `--show-completion` | Show shell completion source code. |

---

## Commands

### 1. `init` — Initialize user configuration

Copy default template files to the user config directory.

**Source:** `mko_telebot/cli.py` → `init()`

```bash
mko-telebot init [OPTIONS]
```

**Options:**

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--force` | `-f` | bool | `False` | Overwrite existing user config files if they exist. |

**Behavior:**

- Reads template files from the application's built-in `settings/` directory.
- Copies them to `~/.config/mko_telebot/settings/` (platform-dependent, see [Config File Locations](#config-file-locations)).
- If a file already exists at the destination and `--force` is not set, it is skipped.
- Creates the destination directory if it does not exist.

**Template files copied:**

| File | Description |
|------|-------------|
| `config.yaml` | Monitoring configuration (channels, keywords, intervals). |
| `secrets.yaml` | Telegram API credentials (api_id, api_hash, phone/token). |
| `log_config.yaml` | Logging configuration (handlers, formatters, levels). |
| `keyw_config_example_keep.yaml` | Keyword configuration example (kept as reference). |

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Success — files copied (or skipped where applicable). |
| `1` | Template settings directory not found (`app_settings_dir` missing). |

**Examples:**

```bash
# Initialize config with default templates
mko-telebot init

# Force overwrite of existing config files
mko-telebot init --force

# Force overwrite (shorthand)
mko-telebot init -f
```

---

### 2. `validate` — Validate configuration

Check that configuration files exist and are valid without starting the monitor.

**Source:** `mko_telebot/cli.py` → `validate()`

```bash
mko-telebot validate
```

**Options:** None.

**Behavior:**

1. Creates a `TelepostConfigReader` pointing at the user config directory.
2. Calls `validate_files()` which checks that both `config.yaml` and `secrets.yaml` exist.
3. If valid, prints a success message in green.
4. If validation fails, prints the error in red and exits with code `1`.

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Configuration files are valid (both `config.yaml` and `secrets.yaml` exist). |
| `1` | Configuration error — a required file is missing (`ConfigError` raised). |

**Examples:**

```bash
# Validate current configuration
mko-telebot validate

# Typical output on success:
# Configuration files are valid.

# Typical output on failure:
# Configuration error: Required config file not found (path: /home/user/.config/mko_telebot/settings/config.yaml)
```

---

### 3. `run` — Start the monitoring service

Start the Telegram monitoring service: authenticate, connect to channels, scan for keyword matches, and forward messages.

**Source:** `mko_telebot/cli.py` → `run()`

```bash
mko-telebot run
```

**Options:** None.

**Behavior:**

1. Sets up logging from `log_config.yaml` (falls back to `basicConfig(level=INFO)` if file missing).
2. Creates a `TelepostConfigReader` and loads/validates `config.yaml` + `secrets.yaml`.
3. Creates a Telethon `TelegramClient` (session files stored in `APP_PATHS.session_dir`).
4. Starts the monitoring loop:
   - Connects to each configured Telegram channel.
   - Fetches new messages since the last scan.
   - Checks messages against configured keywords.
   - Forwards matching messages to configured targets.
   - Saves state (last seen message IDs) per channel.
   - Reschedules each channel for its configured `scan_interval`.
5. Runs until interrupted by `Ctrl+C` (prints "Monitoring stopped by user.").

**Error handling:**

| Scenario | Behavior |
|----------|----------|
| Missing/invalid config | Prints error, exits with code `1`. |
| `KeyboardInterrupt` (Ctrl+C) | Prints yellow message, exits gracefully with code `0`. |
| Telegram auth failure | Logged as error; loop continues for other channels. |
| FloodWait from Telegram | Waits the required duration, then retries. |

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Normal exit (monitor stopped by user via Ctrl+C). |
| `1` | Configuration error — cannot load or validate config files. |

**Examples:**

```bash
# Start the monitoring service (runs until Ctrl+C)
mko-telebot run
```

---

### 4. `config` — Display application path locations

Show all filesystem paths used by the application.

**Source:** `mko_telebot/cli.py` → `config()`

```bash
mko-telebot config
```

**Options:** None.

**Behavior:**

Prints a Rich table with two columns (Path, Value) showing all application paths.

**Paths displayed:**

| Path Name | Description |
|-----------|-------------|
| Config file | Main configuration file (`config.yaml`). |
| Secrets file | Secrets file (`secrets.yaml`). |
| Log config file | Logging configuration file (`log_config.yaml`). |
| State directory | Directory for persistent state (last message IDs). |
| Session directory | Directory for Telethon session files (`.session`). |
| Log directory | Directory for log files. |
| App settings dir | Built-in application settings directory (template source). |
| User settings dir | User-specific settings directory (config destination). |

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Always — command reads static paths, no failure modes. |

**Examples:**

```bash
# Show all config paths
mko-telebot config

# Example output:
# ┌─────────────────────┬──────────────────────────────────────────────────┐
# │ Path                │ Value                                            │
# ├─────────────────────┼──────────────────────────────────────────────────┤
# │ Config file         │ C:\Users\user\.config\mko_telebot\settings\config.yaml        │
# │ Secrets file        │ C:\Users\user\.config\mko_telebot\settings\secrets.yaml       │
# │ Log config file     │ C:\Users\user\.config\mko_telebot\settings\log_config.yaml     │
# │ State directory     │ C:\Users\user\.config\mko_telebot\settings\state              │
# │ Session directory   │ C:\Users\user\.config\mko_telebot\settings\sessions           │
# │ Log directory       │ C:\Users\user\.config\mko_telebot\logs                        │
# │ App settings dir    │ C:\Python\site-packages\mko_telebot\settings                  │
# │ User settings dir   │ C:\Users\user\.config\mko_telebot\settings                    │
# └─────────────────────┴──────────────────────────────────────────────────┘
```

---

### 5. `version` — Show installed version

Display the installed version of `mko-telebot`.

**Source:** `mko_telebot/cli.py` → `version()`

```bash
mko-telebot version
```

**Options:** None.

**Behavior:**

Retrieves the version from package metadata (`importlib.metadata.version("mko-telebot")`) and prints it with bold formatting.

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Always — version retrieval from installed package metadata. |

**Examples:**

```bash
# Show version
mko-telebot version

# Example output:
# mko-telebot version 0.0.1
```

---

## Exit Codes Summary

| Code | Meaning | Commands |
|------|---------|----------|
| `0` | Success | `init`, `validate`, `run`, `config`, `version` |
| `1` | Failure — config error, missing directory, or validation error | `init`, `validate`, `run` |

---

## Config File Locations

### User Configuration Directory

Cross-platform via [platformdirs](https://pypi.org/project/platformdirs/):

| OS | Path |
|----|------|
| **Linux** | `~/.config/mko_telebot/settings/` |
| **macOS** | `~/Library/Application Support/mko_telebot/settings/` |
| **Windows** | `C:\Users\<user>\AppData\Local\mko_telebot\mko_telebot\settings\` |

### Config Files

All user config files live under the user settings directory:

| File | Purpose | Required |
|------|---------|----------|
| `config.yaml` | Monitoring configuration: channels, keywords, intervals, forwarding targets. | Yes |
| `secrets.yaml` | Telegram API credentials: `api_id`, `api_hash`, `phone_or_token`. | Yes |
| `log_config.yaml` | Logging configuration: handlers, formatters, log levels. | No (fallback to basicConfig) |

### Application Template Directory

The built-in template files are located at the package install path:

```
<site-packages>/mko_telebot/settings/
```

These are copied to the user directory via `mko-telebot init`.

---

## Usage Examples

### Quick Start

```bash
# 1. Initialize configuration
mko-telebot init

# 2. Edit the config files (see configuration guide)
#    $EDITOR ~/.config/mko_telebot/settings/config.yaml
#    $EDITOR ~/.config/mko_telebot/settings/secrets.yaml

# 3. Validate the configuration
mko-telebot validate

# 4. Start monitoring
mko-telebot run
```

### Reset Configuration

```bash
# Overwrite existing config with fresh templates
mko-telebot init --force

# Re-validate after editing
mko-telebot validate
```

### Troubleshooting

```bash
# Check where config files are expected
mko-telebot config

# Verify the installed version
mko-telebot version

# Validate config without running
mko-telebot validate
```

### Docker / Headless Environments

```bash
# The config path is platform-dependent.
# On Linux: ~/.config/mko_telebot/settings/
# Bind-mount or copy config files before running:
mko-telebot validate && mko-telebot run
```

---

## Global Options Reference

The `--help` flag is available on every command:

```bash
# Top-level help
mko-telebot --help

# Per-command help
mko-telebot init --help
mko-telebot validate --help
mko-telebot run --help
mko-telebot config --help
mko-telebot version --help
```

---

## Shell Completion

Typer provides built-in shell completion:

```bash
# Install completion for the current shell
mko-telebot --install-completion

# Show the completion script (for manual installation)
mko-telebot --show-completion
```

Supports: Bash, Zsh, Fish, and PowerShell.

---

## See Also

- [Configuration Guide](../11-guides/configuration.md) — detailed field-by-field config reference.
- [Specification](../../docs/SPEC.md) — project specification and architecture.