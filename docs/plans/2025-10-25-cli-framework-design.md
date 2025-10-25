# CLI Application Framework Design

## Overview

Design for the command-line application framework that provides initialization, configuration management, logging, and signal handling for the talk-it-out voice-to-text utility. This framework establishes the foundation for Phase 1 (CLI application) before implementing core voice-to-text functionality.

**Goals:**
- Clean application startup/shutdown lifecycle
- TOML-based configuration with validation
- Structured logging to stderr
- Graceful signal handling with cleanup timeout
- Subcommand support (run, config-edit)
- Permission checks (input group membership)

**Success Criteria:**
- Application starts, loads config, logs to stderr, exits cleanly on Ctrl-C
- Config can be created with defaults, edited, and validated
- User gets clear error messages for missing permissions or invalid config
- Framework code follows Functional Core, Imperative Shell pattern

## Architecture

**Pattern:** Functional orchestrator - pure functions for config/logging/cleanup orchestrated by thin imperative shell in main.py.

**Structure:**
```
src/talk_it_out/
├── main.py                    # Shell: Typer app + orchestration
├── framework/
│   ├── config.py              # Core: config load/validate/save
│   ├── logging_setup.py       # Core: structlog configuration
│   ├── signals.py             # Core: cleanup registration
│   └── permissions.py         # Core: group membership checks
└── commands/
    └── config_edit.py         # Shell: editor + validation
```

**Control Flow:**
1. `main()` is imperative shell
2. Check permissions via `permissions.check_input_group()`
3. Load config via `config.load_config()` → dict or error
4. Setup logging via `logging_setup.configure_logging(config)` → logger
5. Register signal handlers via `signals.setup_signal_handlers(cleanup_fns)`
6. Pass logger/config to application logic (future phases)
7. On SIGINT/SIGTERM: run cleanup with 3s timeout, exit

**Key Principle:** Framework functions are pure (testable without I/O mocks). Only `main()` and commands perform side effects.

## Existing Patterns

This is a greenfield project with no existing code patterns. Established patterns:

- **FCIS (Functional Core, Imperative Shell):** Framework modules are functional core, main.py/commands are imperative shell
- **Result types:** Functions return `Result[T, Error]` or dict/None patterns for explicit error handling
- **uv package manager:** Already in use for dependency management
- **pyproject.toml:** Project uses pyproject.toml (not setup.py or requirements.txt)

**Keyboard library decision:** python-evdev selected for Wayland compatibility (see docs/research/wayland_keyboard_monitoring_research.md). Requires user in `input` group.

## Implementation Phases

### Phase 1: Project Structure and Dependencies
**Goal:** Set up Python package structure with dependencies

**Components:**
- `src/talk_it_out/__init__.py` - Package marker
- `pyproject.toml` - Add dependencies: typer, structlog, evdev
- Entry point configuration in `[project.scripts]`

**Dependencies:**
```toml
dependencies = [
    "typer>=0.9.0",
    "structlog>=24.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
    "evdev>=1.6.0",
]

[project.scripts]
talk-it-out = "talk_it_out.main:app"
```

**Testing:** `uv pip install -e .` succeeds, `talk-it-out --help` shows command

### Phase 2: Configuration System
**Goal:** TOML config loading, validation, defaults

**Components:**
- `src/talk_it_out/framework/config.py`
  - `get_config_path() -> Path` - returns ~/.config/talk-it-out/config.toml
  - `default_config() -> dict` - returns default configuration
  - `load_config(path: Path) -> dict` - loads, validates, creates default if missing
  - `validate_config(config: dict) -> list[str]` - returns validation errors
  - `save_config(path: Path, config: dict) -> None` - writes TOML

**Config Format:**
```toml
[keys]
combination = ["super", "alt"]

[audio]
sample_rate = 16000
channels = 1
device = ""

[whisper]
model = "base"
language = ""

[paste]
method = "clipboard"

[logging]
level = "INFO"
```

**Validation Rules:**
- `keys.combination` must be non-empty list of valid key names (super/alt/ctrl/shift)
- `audio.sample_rate` must be positive int
- `audio.channels` must be 1 or 2
- `whisper.model` must be in: tiny, base, small, medium, large
- `logging.level` must be: DEBUG, INFO, WARNING, ERROR

**Key Name Mapping:**
```python
VALID_KEYS = {
    "super": (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA),
    "alt": (ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT),
    "ctrl": (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL),
    "shift": (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT),
}
```

**First-run Behavior:**
- If config doesn't exist, create with defaults
- Create parent directory if needed
- Log creation at INFO level

**Testing:**
- Valid config loads successfully
- Invalid config returns errors
- Missing config creates defaults
- Validation catches bad values

### Phase 3: Logging System
**Goal:** Structured logging to stderr with structlog

**Components:**
- `src/talk_it_out/framework/logging_setup.py`
  - `configure_logging(log_level: str = "INFO") -> structlog.BoundLogger`
  - `get_log_level(config: dict) -> str`

**Structlog Configuration:**
```python
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),  # Colored, human-readable
    ],
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)
```

**Usage Pattern:**
```python
log = configure_logging("INFO")
log.info("application_started", version="0.1.0")
log.error("config_invalid", path=str(config_path), errors=errors)
```

**Key Decisions:**
- Output to stderr (keeps stdout clean)
- Human-readable format (not JSON for CLI)
- ISO timestamps
- Colored output via ConsoleRenderer
- Log level from config

**Testing:**
- Logs appear on stderr
- Log level filtering works
- Structured context fields work

### Phase 4: Permission Checks
**Goal:** Verify user is in `input` group for evdev

**Components:**
- `src/talk_it_out/framework/permissions.py`
  - `check_input_group() -> tuple[bool, str]` - returns (success, error_message)
  - `get_user_groups() -> list[str]` - returns list of user's groups

**Implementation:**
```python
import os
import grp

def get_user_groups() -> list[str]:
    """Get list of groups current user belongs to."""
    groups = os.getgroups()
    return [grp.getgrgid(gid).gr_name for gid in groups]

def check_input_group() -> tuple[bool, str]:
    """Check if user is in 'input' group."""
    groups = get_user_groups()
    if "input" not in groups:
        error_msg = (
            "User is not in 'input' group. python-evdev requires this for keyboard access.\n"
            "Run: sudo usermod -a -G input $USER\n"
            "Then log out and log back in."
        )
        return (False, error_msg)
    return (True, "")
```

**Testing:**
- Function detects group membership correctly
- Error message is helpful

### Phase 5: Signal Handling and Cleanup
**Goal:** Graceful shutdown with timeout on SIGINT/SIGTERM

**Components:**
- `src/talk_it_out/framework/signals.py`
  - `CleanupRegistry` - class to register/run cleanup functions
  - `setup_signal_handlers(registry: CleanupRegistry, timeout: float = 3.0) -> None`

**Implementation:**
```python
import signal
import sys
from typing import Callable

class CleanupRegistry:
    def __init__(self):
        self.cleanup_fns: list[Callable] = []

    def register(self, fn: Callable) -> None:
        self.cleanup_fns.append(fn)

    def run_all(self, timeout: float) -> None:
        """Run all cleanup functions with timeout."""
        # Setup timeout alarm
        signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError()))
        signal.alarm(int(timeout))

        try:
            for fn in self.cleanup_fns:
                fn()
        except TimeoutError:
            print("⚠️  Cleanup timeout exceeded, forcing exit", file=sys.stderr)
        finally:
            signal.alarm(0)

def setup_signal_handlers(registry: CleanupRegistry, timeout: float = 3.0) -> None:
    """Install SIGINT/SIGTERM handlers."""
    def handler(signum, frame):
        print("\n🛑 Shutting down...", file=sys.stderr)
        registry.run_all(timeout)
        exit_code = 0 if signum == signal.SIGTERM else 130
        sys.exit(exit_code)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
```

**Usage Pattern:**
```python
registry = CleanupRegistry()
registry.register(lambda: keyboard_monitor.stop())
registry.register(lambda: log.info("cleanup_complete"))
setup_signal_handlers(registry, timeout=3.0)
```

**Testing:**
- SIGINT triggers cleanup
- Timeout prevents hanging
- Exit codes correct (0 for SIGTERM, 130 for SIGINT)

### Phase 6: Main Application Entry Point
**Goal:** Typer app with run/config-edit commands

**Components:**
- `src/talk_it_out/main.py`

**Implementation:**
```python
import typer
import sys
from pathlib import Path
from typing import Optional

from talk_it_out.framework import config, logging_setup, permissions, signals

app = typer.Typer()

@app.command()
def run(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
    log_level: Optional[str] = typer.Option(None, "--log-level", "-l"),
):
    """Start voice-to-text listener (default command)."""

    # Check permissions
    ok, error = permissions.check_input_group()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Load config
    path = config_path or config.get_config_path()
    cfg = config.load_config(path)

    # Override log level if specified
    if log_level:
        cfg["logging"]["level"] = log_level

    # Setup logging
    log = logging_setup.configure_logging(cfg["logging"]["level"])
    log.info("application_started", config_path=str(path))

    # Setup cleanup
    registry = signals.CleanupRegistry()
    registry.register(lambda: log.info("shutdown_complete"))
    signals.setup_signal_handlers(registry, timeout=3.0)

    # TODO: Start keyboard monitoring, audio recording, etc.
    log.info("framework_ready")

    # Keep alive (will be replaced with actual event loop)
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

@app.command()
def config_edit():
    """Edit configuration file in $EDITOR and validate."""
    from talk_it_out.commands.config_edit import edit_config
    sys.exit(edit_config())

if __name__ == "__main__":
    app()
```

**Testing:**
- `talk-it-out --help` shows commands
- `talk-it-out run` starts and responds to Ctrl-C
- `talk-it-out config-edit` opens editor

### Phase 7: Config Edit Command
**Goal:** Interactive config editing with validation

**Components:**
- `src/talk_it_out/commands/config_edit.py`

**Implementation:**
```python
import os
import sys
import subprocess
import typer
from talk_it_out.framework import config

def edit_config() -> int:
    """Edit config in $EDITOR, validate on exit. Returns exit code."""
    config_path = config.get_config_path()

    # Create default if doesn't exist
    if not config_path.exists():
        cfg = config.default_config()
        config.save_config(config_path, cfg)
        print(f"✅ Created default config at {config_path}")

    # Get editor
    editor = os.environ.get("EDITOR", "nano")

    # Launch editor
    result = subprocess.run([editor, str(config_path)])
    if result.returncode != 0:
        return result.returncode

    # Validate
    try:
        cfg = config.load_config(config_path)
        errors = config.validate_config(cfg)

        if errors:
            print("❌ Config validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  • {error}", file=sys.stderr)

            # Ask to re-edit
            if typer.confirm("Edit again?"):
                return edit_config()  # Recursive retry
            return 1

        print("✅ Config validated successfully")
        return 0

    except Exception as e:
        print(f"❌ Error loading config: {e}", file=sys.stderr)
        if typer.confirm("Edit again?"):
            return edit_config()
        return 1
```

**Testing:**
- Creates default config on first run
- Opens editor correctly
- Validation catches errors
- Offers to re-edit on failure

### Phase 8: Integration Testing
**Goal:** Verify all components work together

**Test Scenarios:**
1. Fresh install → creates default config → runs successfully
2. Invalid config → shows validation errors → exits with error
3. Ctrl-C during run → cleanup executes → exits cleanly
4. config-edit → modify values → validation passes/fails appropriately
5. Missing input group → shows helpful error → exits
6. CLI flags override config → log level changes correctly

**Integration test script:**
```bash
#!/bin/bash
set -e

# Test 1: Fresh start
rm -rf ~/.config/talk-it-out
talk-it-out run &
PID=$!
sleep 2
kill -INT $PID
wait $PID

# Test 2: Config edit
echo "model = \"invalid\"" >> ~/.config/talk-it-out/config.toml
! talk-it-out run  # Should fail

# Test 3: Valid edit
talk-it-out config-edit  # Manual test

# Test 4: Override log level
talk-it-out run --log-level DEBUG &
PID=$!
sleep 2
kill -INT $PID
wait $PID
```

## Additional Considerations

### Error Handling Strategy
- Config errors: print to stderr, exit with code 1
- Permission errors: print helpful instructions, exit with code 1
- Cleanup timeout: log warning, force exit
- Validation errors: show all errors at once (not just first)

### Future Extensibility
- Config schema can grow (add sections as needed)
- Cleanup registry supports multiple cleanup functions
- Logging context can be enriched per-component
- Subcommands easily added to Typer app

### Dependencies on Future Phases
- Phase 1.5 (keyboard monitoring) will use evdev constants from config validation
- Phase 1.6 (audio recording) will use audio.* config section
- Phase 1.7 (transcription) will use whisper.* config section
- Phase 2 (GUI) will use same config system, different logging target

### FCIS Compliance
**Functional Core (framework/):**
- `config.py` - pure functions, no I/O in validation
- `logging_setup.py` - pure configuration, returns logger
- `permissions.py` - pure check (reads /proc but no mutations)
- `signals.py` - registry is data structure, handlers are pure setup

**Imperative Shell:**
- `main.py` - orchestrates calls, performs I/O
- `commands/config_edit.py` - spawns editor, handles user interaction

**Pattern comments added to each file:**
```python
# pattern: Functional Core
# Pure functions for configuration management
```

```python
# pattern: Imperative Shell
# Orchestrates framework components and handles I/O
```
