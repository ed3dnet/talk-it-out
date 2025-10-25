# CLI Application Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the CLI application framework with configuration, logging, and signal handling for the talk-it-out voice-to-text utility.

**Architecture:** Functional orchestrator pattern - pure functions in framework/ orchestrated by imperative shell in main.py and commands/.

**Tech Stack:** Python 3.14, Typer (CLI), structlog (logging), TOML (config), python-evdev (keyboard - Phase 1.5)

**Scope:** 8 phases from original design (complete CLI framework)

**Codebase verified:** 2025-10-25

---

## Phase 1: Project Structure and Dependencies

### Task 1: Create Package Structure

**Files:**
- Create: `src/talk_it_out/__init__.py`
- Create: `src/talk_it_out/framework/__init__.py`
- Create: `src/talk_it_out/commands/__init__.py`

**Step 1: Create src directory structure**

Run:
```bash
mkdir -p src/talk_it_out/framework src/talk_it_out/commands
```

Expected: Directories created without error

**Step 2: Create package marker files**

Create `src/talk_it_out/__init__.py`:
```python
"""talk-it-out: Voice-to-text utility for Linux/KDE Plasma."""

__version__ = "0.1.0"
```

Create `src/talk_it_out/framework/__init__.py`:
```python
"""Framework modules for application initialization and configuration."""
```

Create `src/talk_it_out/commands/__init__.py`:
```python
"""CLI subcommand implementations."""
```

**Step 3: Verify structure**

Run:
```bash
tree src/
```

Expected output:
```
src/
└── talk_it_out/
    ├── __init__.py
    ├── commands/
    │   └── __init__.py
    └── framework/
        └── __init__.py
```

**Step 4: Commit**

```bash
git add src/
git commit -m "feat: create Python package structure

- Add src/talk_it_out/ package directory
- Add framework/ subpackage for core functionality
- Add commands/ subpackage for CLI commands"
```

### Task 2: Update pyproject.toml with Dependencies

**Files:**
- Modify: `pyproject.toml:6-7`

**Step 1: Add dependencies to pyproject.toml**

Replace line 6 (`dependencies = []`) with:
```toml
dependencies = [
    "typer>=0.9.0",
    "structlog>=24.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
    "evdev>=1.6.0",
]
```

**Step 2: Add entry point configuration**

Add after the `dependencies` section:
```toml

[project.scripts]
talk-it-out = "talk_it_out.main:app"
```

**Step 3: Verify pyproject.toml syntax**

Run:
```bash
uv pip install -e .
```

Expected: Installation succeeds (may show "No module named 'talk_it_out.main'" - this is expected, we'll fix in Phase 6)

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add project dependencies and entry point

Dependencies:
- typer: CLI framework with subcommand support
- structlog: structured logging to stderr
- tomli: TOML parsing (backport for Python <3.11)
- evdev: keyboard monitoring for Wayland

Entry point: talk-it-out command"
```

### Task 3: Verify Installation

**Step 1: Install package in development mode**

Run:
```bash
uv pip install -e .
```

Expected: Installation completes successfully

**Step 2: Verify command is available (will fail for now)**

Run:
```bash
which talk-it-out
```

Expected: Shows path to installed command (e.g., `/home/ed/.local/bin/talk-it-out` or similar)

Note: Running `talk-it-out` will fail with "No module named 'talk_it_out.main'" - this is expected and will be fixed in Phase 6.

**Step 3: Verify dependencies installed**

Run:
```bash
python -c "import typer, structlog, evdev; print('Dependencies OK')"
```

Expected output: `Dependencies OK`

---

## Phase 2: Configuration System

### Task 1: Write Tests for Configuration Path Functions

**Files:**
- Create: `tests/framework/test_config.py`

**Step 1: Create test directory structure**

Run:
```bash
mkdir -p tests/framework
touch tests/__init__.py tests/framework/__init__.py
```

**Step 2: Write test for get_config_path()**

Create `tests/framework/test_config.py`:
```python
# pattern: Functional Core tests
# Tests for pure configuration functions

from pathlib import Path
from talk_it_out.framework import config


def test_get_config_path_returns_xdg_config_location():
    """Config path should be ~/.config/talk-it-out/config.toml"""
    path = config.get_config_path()

    assert isinstance(path, Path)
    assert path.name == "config.toml"
    assert "talk-it-out" in str(path)
    assert ".config" in str(path)
```

**Step 3: Run test to verify it fails**

Run:
```bash
pytest tests/framework/test_config.py::test_get_config_path_returns_xdg_config_location -v
```

Expected: FAIL with "No module named 'talk_it_out.framework.config'"

**Step 4: Commit**

```bash
git add tests/
git commit -m "test: add test for config path resolution"
```

### Task 2: Implement get_config_path()

**Files:**
- Create: `src/talk_it_out/framework/config.py`

**Step 1: Write minimal implementation**

Create `src/talk_it_out/framework/config.py`:
```python
# pattern: Functional Core
# Pure functions for configuration management

from pathlib import Path


def get_config_path() -> Path:
    """Get path to configuration file.

    Returns:
        Path to ~/.config/talk-it-out/config.toml
    """
    return Path.home() / ".config" / "talk-it-out" / "config.toml"
```

**Step 2: Run test to verify it passes**

Run:
```bash
pytest tests/framework/test_config.py::test_get_config_path_returns_xdg_config_location -v
```

Expected: PASS

**Step 3: Commit**

```bash
git add src/talk_it_out/framework/config.py
git commit -m "feat: implement config path resolution

Returns ~/.config/talk-it-out/config.toml"
```

### Task 3: Write Tests for Default Configuration

**Files:**
- Modify: `tests/framework/test_config.py`

**Step 1: Add test for default_config()**

Append to `tests/framework/test_config.py`:
```python


def test_default_config_returns_valid_structure():
    """Default config should have all required sections"""
    cfg = config.default_config()

    assert isinstance(cfg, dict)
    assert "keys" in cfg
    assert "audio" in cfg
    assert "whisper" in cfg
    assert "paste" in cfg
    assert "logging" in cfg


def test_default_config_keys_section():
    """Keys section should have valid combination"""
    cfg = config.default_config()

    assert cfg["keys"]["combination"] == ["super", "alt"]
    assert isinstance(cfg["keys"]["combination"], list)


def test_default_config_audio_section():
    """Audio section should have sensible defaults"""
    cfg = config.default_config()

    assert cfg["audio"]["sample_rate"] == 16000
    assert cfg["audio"]["channels"] == 1
    assert cfg["audio"]["device"] == ""


def test_default_config_whisper_section():
    """Whisper section should use base model"""
    cfg = config.default_config()

    assert cfg["whisper"]["model"] == "base"
    assert cfg["whisper"]["language"] == ""


def test_default_config_logging_section():
    """Logging should default to INFO level"""
    cfg = config.default_config()

    assert cfg["logging"]["level"] == "INFO"
```

**Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/framework/test_config.py -v -k default_config
```

Expected: FAIL with "AttributeError: module 'talk_it_out.framework.config' has no attribute 'default_config'"

**Step 3: Commit**

```bash
git add tests/framework/test_config.py
git commit -m "test: add tests for default configuration structure"
```

### Task 4: Implement default_config()

**Files:**
- Modify: `src/talk_it_out/framework/config.py`

**Step 1: Add default_config() function**

Append to `src/talk_it_out/framework/config.py`:
```python


def default_config() -> dict:
    """Get default configuration.

    Returns:
        Dictionary with default configuration values
    """
    return {
        "keys": {
            "combination": ["super", "alt"],
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "device": "",
        },
        "whisper": {
            "model": "base",
            "language": "",
        },
        "paste": {
            "method": "clipboard",
        },
        "logging": {
            "level": "INFO",
        },
    }
```

**Step 2: Run tests to verify they pass**

Run:
```bash
pytest tests/framework/test_config.py -v -k default_config
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add src/talk_it_out/framework/config.py
git commit -m "feat: implement default configuration

Provides sensible defaults for all config sections:
- keys: super+alt combination
- audio: 16kHz mono
- whisper: base model
- logging: INFO level"
```

### Task 5: Write Tests for Configuration Validation

**Files:**
- Modify: `tests/framework/test_config.py`

**Step 1: Add imports for evdev**

Add to top of `tests/framework/test_config.py` after existing imports:
```python
from evdev import ecodes
```

**Step 2: Add validation tests**

Append to `tests/framework/test_config.py`:
```python


def test_validate_config_accepts_valid_config():
    """Valid configuration should pass validation"""
    cfg = config.default_config()
    errors = config.validate_config(cfg)

    assert errors == []


def test_validate_config_rejects_empty_key_combination():
    """Empty key combination should fail validation"""
    cfg = config.default_config()
    cfg["keys"]["combination"] = []
    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("combination" in err.lower() for err in errors)


def test_validate_config_rejects_invalid_key_names():
    """Invalid key names should fail validation"""
    cfg = config.default_config()
    cfg["keys"]["combination"] = ["invalid_key"]
    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("invalid" in err.lower() or "key" in err.lower() for err in errors)


def test_validate_config_rejects_invalid_audio_sample_rate():
    """Zero or negative sample rate should fail"""
    cfg = config.default_config()
    cfg["audio"]["sample_rate"] = -1
    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("sample_rate" in err.lower() for err in errors)


def test_validate_config_rejects_invalid_channels():
    """Channels must be 1 or 2"""
    cfg = config.default_config()
    cfg["audio"]["channels"] = 3
    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("channel" in err.lower() for err in errors)


def test_validate_config_rejects_invalid_whisper_model():
    """Unknown whisper model should fail"""
    cfg = config.default_config()
    cfg["whisper"]["model"] = "ultra-mega"
    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("model" in err.lower() for err in errors)


def test_validate_config_rejects_invalid_log_level():
    """Invalid log level should fail"""
    cfg = config.default_config()
    cfg["logging"]["level"] = "TRACE"
    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("level" in err.lower() or "logging" in err.lower() for err in errors)
```

**Step 3: Run tests to verify they fail**

Run:
```bash
pytest tests/framework/test_config.py -v -k validate_config
```

Expected: FAIL with "AttributeError: module has no attribute 'validate_config'"

**Step 4: Commit**

```bash
git add tests/framework/test_config.py
git commit -m "test: add configuration validation tests

Tests cover:
- Valid config acceptance
- Empty/invalid key combinations
- Audio parameters (sample rate, channels)
- Whisper model validation
- Log level validation"
```

### Task 6: Implement validate_config()

**Files:**
- Modify: `src/talk_it_out/framework/config.py`

**Step 1: Add imports**

Add to top of `src/talk_it_out/framework/config.py`:
```python
from evdev import ecodes
```

**Step 2: Add VALID_KEYS constant and validate_config()**

Append to `src/talk_it_out/framework/config.py`:
```python


# Valid key names mapped to evdev constants
VALID_KEYS = {
    "super": (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA),
    "alt": (ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT),
    "ctrl": (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL),
    "shift": (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT),
}

VALID_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]


def validate_config(cfg: dict) -> list[str]:
    """Validate configuration dictionary.

    Args:
        cfg: Configuration dictionary to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate keys.combination
    if "keys" not in cfg or "combination" not in cfg["keys"]:
        errors.append("Missing keys.combination")
    elif not cfg["keys"]["combination"]:
        errors.append("keys.combination cannot be empty")
    else:
        for key in cfg["keys"]["combination"]:
            if key not in VALID_KEYS:
                errors.append(f"Invalid key name: {key}. Must be one of: {list(VALID_KEYS.keys())}")

    # Validate audio.sample_rate
    if "audio" not in cfg or "sample_rate" not in cfg["audio"]:
        errors.append("Missing audio.sample_rate")
    elif cfg["audio"]["sample_rate"] <= 0:
        errors.append("audio.sample_rate must be positive")

    # Validate audio.channels
    if "audio" not in cfg or "channels" not in cfg["audio"]:
        errors.append("Missing audio.channels")
    elif cfg["audio"]["channels"] not in (1, 2):
        errors.append("audio.channels must be 1 or 2")

    # Validate whisper.model
    if "whisper" not in cfg or "model" not in cfg["whisper"]:
        errors.append("Missing whisper.model")
    elif cfg["whisper"]["model"] not in VALID_WHISPER_MODELS:
        errors.append(f"Invalid whisper.model: {cfg['whisper']['model']}. Must be one of: {VALID_WHISPER_MODELS}")

    # Validate logging.level
    if "logging" not in cfg or "level" not in cfg["logging"]:
        errors.append("Missing logging.level")
    elif cfg["logging"]["level"] not in VALID_LOG_LEVELS:
        errors.append(f"Invalid logging.level: {cfg['logging']['level']}. Must be one of: {VALID_LOG_LEVELS}")

    return errors
```

**Step 3: Run tests to verify they pass**

Run:
```bash
pytest tests/framework/test_config.py -v -k validate_config
```

Expected: All tests PASS

**Step 4: Commit**

```bash
git add src/talk_it_out/framework/config.py
git commit -m "feat: implement configuration validation

Validates:
- Key combinations (super/alt/ctrl/shift)
- Audio parameters (sample rate, channels)
- Whisper model selection
- Log levels

Returns list of error messages for invalid configs"
```

### Task 7: Write Tests for save_config() and load_config()

**Files:**
- Modify: `tests/framework/test_config.py`

**Step 1: Add test imports**

Add to top of `tests/framework/test_config.py` after existing imports:
```python
import tempfile
import tomllib
```

**Step 2: Add save_config() tests**

Append to `tests/framework/test_config.py`:
```python


def test_save_config_creates_toml_file(tmp_path):
    """save_config should write TOML file"""
    config_path = tmp_path / "config.toml"
    cfg = config.default_config()

    config.save_config(config_path, cfg)

    assert config_path.exists()


def test_save_config_creates_parent_directory(tmp_path):
    """save_config should create parent dirs if needed"""
    config_path = tmp_path / "nested" / "dir" / "config.toml"
    cfg = config.default_config()

    config.save_config(config_path, cfg)

    assert config_path.exists()
    assert config_path.parent.exists()


def test_save_config_writes_valid_toml(tmp_path):
    """Saved config should be valid TOML"""
    config_path = tmp_path / "config.toml"
    cfg = config.default_config()

    config.save_config(config_path, cfg)

    # Read back and parse
    with open(config_path, "rb") as f:
        loaded = tomllib.load(f)

    assert loaded == cfg


def test_load_config_reads_existing_file(tmp_path):
    """load_config should read and parse existing TOML"""
    config_path = tmp_path / "config.toml"
    original = config.default_config()
    config.save_config(config_path, original)

    loaded = config.load_config(config_path)

    assert loaded == original


def test_load_config_creates_default_if_missing(tmp_path):
    """load_config should create default config if file doesn't exist"""
    config_path = tmp_path / "config.toml"

    loaded = config.load_config(config_path)

    assert loaded == config.default_config()
    assert config_path.exists()


def test_load_config_validates_loaded_config(tmp_path):
    """load_config should raise if loaded config is invalid"""
    config_path = tmp_path / "config.toml"
    invalid_cfg = config.default_config()
    invalid_cfg["whisper"]["model"] = "invalid"
    config.save_config(config_path, invalid_cfg)

    try:
        config.load_config(config_path)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "model" in str(e).lower()
```

**Step 3: Run tests to verify they fail**

Run:
```bash
pytest tests/framework/test_config.py -v -k "save_config or load_config"
```

Expected: FAIL with "AttributeError: module has no attribute 'save_config'"

**Step 4: Commit**

```bash
git add tests/framework/test_config.py
git commit -m "test: add save/load config tests

Tests cover:
- TOML file creation
- Parent directory creation
- Valid TOML writing
- Config loading
- Default config creation
- Validation on load"
```

### Task 8: Implement save_config() and load_config()

**Files:**
- Modify: `src/talk_it_out/framework/config.py`

**Step 1: Add imports**

Replace import section at top of `src/talk_it_out/framework/config.py`:
```python
from pathlib import Path
import tomllib

try:
    import tomli_w
except ImportError:
    # For writing TOML, we need tomli_w (tomllib is read-only)
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tomli-w"])
    import tomli_w

from evdev import ecodes
```

**Step 2: Implement save_config()**

Append to `src/talk_it_out/framework/config.py`:
```python


def save_config(path: Path, cfg: dict) -> None:
    """Save configuration to TOML file.

    Args:
        path: Path to config file
        cfg: Configuration dictionary to save
    """
    # Create parent directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write TOML
    with open(path, "wb") as f:
        tomli_w.dump(cfg, f)


def load_config(path: Path) -> dict:
    """Load configuration from TOML file.

    Creates default config if file doesn't exist.
    Validates loaded config.

    Args:
        path: Path to config file

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If loaded config is invalid
    """
    # Create default if doesn't exist
    if not path.exists():
        default = default_config()
        save_config(path, default)
        return default

    # Load TOML
    with open(path, "rb") as f:
        cfg = tomllib.load(f)

    # Validate
    errors = validate_config(cfg)
    if errors:
        raise ValueError(f"Invalid configuration: {'; '.join(errors)}")

    return cfg
```

**Step 3: Add tomli-w to dependencies**

Modify `pyproject.toml` dependencies:
```toml
dependencies = [
    "typer>=0.9.0",
    "structlog>=24.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
    "tomli-w>=1.0.0",
    "evdev>=1.6.0",
]
```

**Step 4: Install dependency**

Run:
```bash
uv pip install tomli-w
```

**Step 5: Run tests to verify they pass**

Run:
```bash
pytest tests/framework/test_config.py -v -k "save_config or load_config"
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/talk_it_out/framework/config.py pyproject.toml
git commit -m "feat: implement config save/load with TOML

- save_config() writes TOML with parent dir creation
- load_config() reads TOML, creates default if missing
- Validates config on load
- Add tomli-w dependency for TOML writing"
```

---

## Phase 3: Logging System

### Task 1: Write Tests for Logging Configuration

**Files:**
- Create: `tests/framework/test_logging_setup.py`

**Step 1: Create test file**

Create `tests/framework/test_logging_setup.py`:
```python
# pattern: Functional Core tests
# Tests for logging configuration

import sys
import structlog
from talk_it_out.framework import logging_setup


def test_configure_logging_returns_logger():
    """configure_logging should return a logger instance"""
    logger = logging_setup.configure_logging("INFO")

    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "debug")


def test_configure_logging_respects_log_level():
    """Log level filtering should work"""
    # This test verifies the function configures properly
    # Actual filtering behavior is tested by structlog itself
    logger = logging_setup.configure_logging("ERROR")

    # Should not raise
    logger.error("test message")


def test_get_log_level_extracts_from_config():
    """get_log_level should extract level from config dict"""
    cfg = {"logging": {"level": "DEBUG"}}

    level = logging_setup.get_log_level(cfg)

    assert level == "DEBUG"


def test_get_log_level_returns_default_if_missing():
    """get_log_level should return INFO if not in config"""
    cfg = {}

    level = logging_setup.get_log_level(cfg)

    assert level == "INFO"
```

**Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/framework/test_logging_setup.py -v
```

Expected: FAIL with "No module named 'talk_it_out.framework.logging_setup'"

**Step 3: Commit**

```bash
git add tests/framework/test_logging_setup.py
git commit -m "test: add logging setup tests

Tests cover:
- Logger instance creation
- Log level configuration
- Config extraction"
```

### Task 2: Implement Logging Configuration

**Files:**
- Create: `src/talk_it_out/framework/logging_setup.py`

**Step 1: Write implementation**

Create `src/talk_it_out/framework/logging_setup.py`:
```python
# pattern: Functional Core
# Pure functions for logging configuration

import sys
import logging
import structlog


def get_log_level(cfg: dict) -> str:
    """Extract log level from config.

    Args:
        cfg: Configuration dictionary

    Returns:
        Log level string (DEBUG/INFO/WARNING/ERROR), defaults to INFO
    """
    try:
        return cfg["logging"]["level"]
    except KeyError:
        return "INFO"


def configure_logging(log_level: str = "INFO") -> structlog.BoundLogger:
    """Configure structured logging to stderr.

    Args:
        log_level: Logging level (DEBUG/INFO/WARNING/ERROR)

    Returns:
        Configured structlog logger
    """
    # Map string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = level_map.get(log_level, logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),  # Colored, human-readable output
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=False,
    )

    return structlog.get_logger()
```

**Step 2: Run tests to verify they pass**

Run:
```bash
pytest tests/framework/test_logging_setup.py -v
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add src/talk_it_out/framework/logging_setup.py
git commit -m "feat: implement structured logging with structlog

- configure_logging() sets up stderr output
- Colored console renderer for readability
- ISO timestamps
- Log level filtering
- get_log_level() extracts from config dict"
```

---

## Phase 4: Permission Checks

### Task 1: Write Tests for Permission Checks

**Files:**
- Create: `tests/framework/test_permissions.py`

**Step 1: Create test file**

Create `tests/framework/test_permissions.py`:
```python
# pattern: Functional Core tests
# Tests for permission checking functions

import os
from talk_it_out.framework import permissions


def test_get_user_groups_returns_list():
    """get_user_groups should return list of group names"""
    groups = permissions.get_user_groups()

    assert isinstance(groups, list)
    assert len(groups) > 0
    assert all(isinstance(g, str) for g in groups)


def test_get_user_groups_includes_current_user_group():
    """User's primary group should be in the list"""
    groups = permissions.get_user_groups()

    # User should at least be in their own group
    import grp
    primary_gid = os.getgid()
    primary_group = grp.getgrgid(primary_gid).gr_name

    assert primary_group in groups


def test_check_input_group_returns_tuple():
    """check_input_group should return (bool, str) tuple"""
    result = permissions.check_input_group()

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], str)


def test_check_input_group_error_message_has_instructions():
    """If not in input group, error should have instructions"""
    success, error = permissions.check_input_group()

    if not success:
        # Error message should contain helpful instructions
        assert "input" in error.lower()
        assert "usermod" in error.lower() or "group" in error.lower()
```

**Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/framework/test_permissions.py -v
```

Expected: FAIL with "No module named 'talk_it_out.framework.permissions'"

**Step 3: Commit**

```bash
git add tests/framework/test_permissions.py
git commit -m "test: add permission checking tests

Tests cover:
- Group list retrieval
- Primary group membership
- Input group check
- Error message content"
```

### Task 2: Implement Permission Checks

**Files:**
- Create: `src/talk_it_out/framework/permissions.py`

**Step 1: Write implementation**

Create `src/talk_it_out/framework/permissions.py`:
```python
# pattern: Functional Core
# Pure functions for permission checking

import os
import grp


def get_user_groups() -> list[str]:
    """Get list of groups current user belongs to.

    Returns:
        List of group names
    """
    groups = os.getgroups()
    return [grp.getgrgid(gid).gr_name for gid in groups]


def check_input_group() -> tuple[bool, str]:
    """Check if user is in 'input' group.

    python-evdev requires the user to be in the 'input' group
    to access /dev/input/eventX devices for keyboard monitoring.

    Returns:
        Tuple of (success, error_message)
        - success: True if in input group, False otherwise
        - error_message: Empty string if success, instructions if failure
    """
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

**Step 2: Run tests to verify they pass**

Run:
```bash
pytest tests/framework/test_permissions.py -v
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add src/talk_it_out/framework/permissions.py
git commit -m "feat: implement input group permission check

- get_user_groups() returns list of user's groups
- check_input_group() verifies input group membership
- Returns helpful error with instructions if not in group"
```

---

## Phase 5: Signal Handling and Cleanup

### Task 1: Write Tests for CleanupRegistry

**Files:**
- Create: `tests/framework/test_signals.py`

**Step 1: Create test file**

Create `tests/framework/test_signals.py`:
```python
# pattern: Functional Core tests
# Tests for signal handling and cleanup

import time
from talk_it_out.framework import signals


def test_cleanup_registry_can_register_functions():
    """Should be able to register cleanup functions"""
    registry = signals.CleanupRegistry()

    def cleanup():
        pass

    registry.register(cleanup)

    assert len(registry.cleanup_fns) == 1


def test_cleanup_registry_runs_all_functions():
    """run_all should execute all registered functions"""
    registry = signals.CleanupRegistry()

    counter = {"value": 0}

    def cleanup1():
        counter["value"] += 1

    def cleanup2():
        counter["value"] += 10

    registry.register(cleanup1)
    registry.register(cleanup2)
    registry.run_all(timeout=1.0)

    assert counter["value"] == 11


def test_cleanup_registry_respects_timeout():
    """run_all should timeout if cleanup takes too long"""
    registry = signals.CleanupRegistry()

    def slow_cleanup():
        time.sleep(5)  # Intentionally slow

    registry.register(slow_cleanup)

    # Should not hang - should timeout
    start = time.time()
    registry.run_all(timeout=1.0)
    elapsed = time.time() - start

    # Should have timed out around 1 second, not waited 5
    assert elapsed < 2.0
```

**Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/framework/test_signals.py -v
```

Expected: FAIL with "No module named 'talk_it_out.framework.signals'"

**Step 3: Commit**

```bash
git add tests/framework/test_signals.py
git commit -m "test: add signal handling tests

Tests cover:
- Cleanup function registration
- Running all cleanup functions
- Timeout enforcement"
```

### Task 2: Implement CleanupRegistry

**Files:**
- Create: `src/talk_it_out/framework/signals.py`

**Step 1: Write CleanupRegistry implementation**

Create `src/talk_it_out/framework/signals.py`:
```python
# pattern: Functional Core
# Pure functions and data structures for cleanup management

import signal
import sys
from typing import Callable


class CleanupRegistry:
    """Registry for cleanup functions to run on shutdown.

    Why this exists: Allows components to register cleanup functions
    that will be executed when the application receives SIGINT/SIGTERM.
    Ensures graceful shutdown even if cleanup hangs.
    """

    def __init__(self):
        self.cleanup_fns: list[Callable] = []

    def register(self, fn: Callable) -> None:
        """Register a cleanup function.

        Args:
            fn: Callable with no arguments to run on shutdown
        """
        self.cleanup_fns.append(fn)

    def run_all(self, timeout: float) -> None:
        """Run all cleanup functions with timeout.

        If cleanup takes longer than timeout, force exit to prevent hanging.

        Args:
            timeout: Maximum seconds to wait for all cleanup
        """
        # Setup timeout alarm
        def timeout_handler(signum, frame):
            raise TimeoutError("Cleanup timeout exceeded")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

        try:
            for fn in self.cleanup_fns:
                fn()
        except TimeoutError:
            print("⚠️  Cleanup timeout exceeded, forcing exit", file=sys.stderr)
        finally:
            signal.alarm(0)  # Cancel alarm


def setup_signal_handlers(registry: CleanupRegistry, timeout: float = 3.0) -> None:
    """Install SIGINT/SIGTERM handlers for graceful shutdown.

    Why this exists: Ensures cleanup runs when user presses Ctrl-C or
    system sends termination signal.

    Args:
        registry: CleanupRegistry with registered cleanup functions
        timeout: Maximum seconds to wait for cleanup (default 3.0)
    """
    def handler(signum, frame):
        print("\n🛑 Shutting down...", file=sys.stderr)
        registry.run_all(timeout)

        # Exit with appropriate code
        # 130 = 128 + SIGINT (2) - standard Unix convention
        # 0 = clean shutdown for SIGTERM
        exit_code = 0 if signum == signal.SIGTERM else 130
        sys.exit(exit_code)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
```

**Step 2: Run tests to verify they pass**

Run:
```bash
pytest tests/framework/test_signals.py -v
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add src/talk_it_out/framework/signals.py
git commit -m "feat: implement signal handling with cleanup timeout

- CleanupRegistry manages cleanup functions
- run_all() executes with configurable timeout
- setup_signal_handlers() installs SIGINT/SIGTERM handlers
- Exits with code 130 for SIGINT, 0 for SIGTERM"
```

---

## Phase 6: Main Application Entry Point

### Task 1: Create Typer Application Skeleton

**Files:**
- Create: `src/talk_it_out/main.py`
- Delete: `main.py` (project root stub)

**Step 1: Create main.py with Typer app**

Create `src/talk_it_out/main.py`:
```python
# pattern: Imperative Shell
# Orchestrates framework components and handles I/O

import typer
import sys
from pathlib import Path
from typing import Optional

app = typer.Typer()


@app.command()
def run(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
    log_level: Optional[str] = typer.Option(None, "--log-level", "-l", help="Override log level (DEBUG/INFO/WARNING/ERROR)"),
):
    """Start voice-to-text listener (default command)."""
    print("run command placeholder")


@app.command()
def config_edit():
    """Edit configuration file in $EDITOR and validate."""
    print("config-edit command placeholder")


if __name__ == "__main__":
    app()
```

**Step 2: Delete old stub file**

Run:
```bash
rm main.py
```

**Step 3: Test Typer app works**

Run:
```bash
python -m talk_it_out.main --help
```

Expected output:
```
Usage: python -m talk_it_out.main [OPTIONS] COMMAND [ARGS]...

Commands:
  config-edit  Edit configuration file in $EDITOR and validate.
  run          Start voice-to-text listener (default command).
```

**Step 4: Commit**

```bash
git add src/talk_it_out/main.py
git rm main.py
git commit -m "feat: create Typer application skeleton

- Add run command (placeholder)
- Add config-edit command (placeholder)
- Move from project root to src/talk_it_out/
- Delete old stub file"
```

### Task 2: Implement run Command with Framework Integration

**Files:**
- Modify: `src/talk_it_out/main.py`

**Step 1: Add imports**

Replace import section in `src/talk_it_out/main.py`:
```python
import typer
import sys
import time
from pathlib import Path
from typing import Optional

from talk_it_out.framework import config, logging_setup, permissions, signals
```

**Step 2: Implement run command**

Replace the `run()` function:
```python
@app.command()
def run(
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
    log_level: Optional[str] = typer.Option(None, "--log-level", "-l", help="Override log level (DEBUG/INFO/WARNING/ERROR)"),
):
    """Start voice-to-text listener (default command)."""

    # Check permissions first
    ok, error = permissions.check_input_group()
    if not ok:
        print(error, file=sys.stderr)
        sys.exit(1)

    # Load configuration
    path = config_path or config.get_config_path()
    try:
        cfg = config.load_config(path)
    except ValueError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Override log level if specified via CLI
    if log_level:
        cfg["logging"]["level"] = log_level

    # Setup logging
    log = logging_setup.configure_logging(cfg["logging"]["level"])
    log.info("application_started", config_path=str(path))

    # Setup cleanup handlers
    registry = signals.CleanupRegistry()
    registry.register(lambda: log.info("shutdown_complete"))
    signals.setup_signal_handlers(registry, timeout=3.0)

    # TODO: Start keyboard monitoring, audio recording, etc.
    # For now, just log that framework is ready
    log.info("framework_ready", message="CLI framework initialized successfully")
    log.info("waiting_for_implementation", message="Keyboard monitoring will be added in future phase")

    # Keep alive loop (will be replaced with actual event loop in future phases)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Signal handler will take care of cleanup
        pass
```

**Step 3: Test run command**

Run:
```bash
python -m talk_it_out.main run
```

Expected: Application starts, shows log messages, responds to Ctrl-C

**Step 4: Test with CLI options**

Run:
```bash
python -m talk_it_out.main run --log-level DEBUG
```

Expected: Debug-level messages appear

**Step 5: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: implement run command with framework integration

- Check input group permissions on startup
- Load configuration with error handling
- Support --config and --log-level CLI options
- Setup structured logging
- Register cleanup handlers for graceful shutdown
- Add keep-alive loop (placeholder for future event loop)"
```

### Task 3: Test Application Without Installing

**Files:**
None (testing only)

**Step 1: Test running via python -m**

Run:
```bash
python -m talk_it_out.main --help
```

Expected output shows commands

**Step 2: Test run command**

Run:
```bash
python -m talk_it_out.main run --log-level INFO &
PID=$!
sleep 2
kill -INT $PID
wait $PID
```

Expected: Starts, shows logs, shuts down gracefully

**Step 3: Test config path override**

Run:
```bash
python -m talk_it_out.main run --config /tmp/test-config.toml --log-level DEBUG
```

Expected: Creates config at /tmp/test-config.toml, shows debug logs

Press Ctrl-C to stop.

**Note:** Entry point installation via `uv pip install -e .` will be tested in Phase 8 integration testing.

---

## Phase 7: Config Edit Command

### Task 1: Implement config_edit Module

**Files:**
- Create: `src/talk_it_out/commands/config_edit.py`

**Step 1: Create implementation**

Create `src/talk_it_out/commands/config_edit.py`:
```python
# pattern: Imperative Shell
# Handles config editing with external editor and validation

import os
import sys
import subprocess
import typer

from talk_it_out.framework import config


def edit_config() -> int:
    """Edit config in $EDITOR, validate on exit.

    Why this exists: Provides interactive config editing with validation.
    Creates default config if it doesn't exist, then opens in user's
    preferred editor.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    config_path = config.get_config_path()

    # Create default config if doesn't exist
    if not config_path.exists():
        cfg = config.default_config()
        config.save_config(config_path, cfg)
        print(f"✅ Created default config at {config_path}")

    # Get editor from environment
    editor = os.environ.get("EDITOR", "nano")

    # Launch editor
    result = subprocess.run([editor, str(config_path)])
    if result.returncode != 0:
        print(f"❌ Editor exited with error code {result.returncode}", file=sys.stderr)
        return result.returncode

    # Validate edited config
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

    except ValueError as e:
        print(f"❌ Error loading config: {e}", file=sys.stderr)
        if typer.confirm("Edit again?"):
            return edit_config()
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1
```

**Step 2: Update main.py to use config_edit**

Modify `src/talk_it_out/main.py` - replace the `config_edit()` function:
```python
@app.command()
def config_edit():
    """Edit configuration file in $EDITOR and validate."""
    from talk_it_out.commands.config_edit import edit_config
    sys.exit(edit_config())
```

**Step 3: Test config-edit command**

Run:
```bash
python -m talk_it_out.main config-edit
```

Expected:
1. Creates config if doesn't exist
2. Opens in editor (nano by default)
3. Validates after saving
4. Shows success or validation errors

**Step 4: Test validation error handling**

Edit config to have invalid value, save and exit editor.

Expected: Shows validation errors, offers to re-edit

**Step 5: Commit**

```bash
git add src/talk_it_out/commands/config_edit.py src/talk_it_out/main.py
git commit -m "feat: implement config-edit command

- Opens config in $EDITOR (defaults to nano)
- Creates default config if doesn't exist
- Validates after editing
- Offers to re-edit on validation errors
- Recursive retry support"
```

### Task 2: Manual Test of Config Edit Workflow

**Files:**
None (manual testing by user)

**After implementing the code in Task 1, manually test these scenarios:**

**Test 1: Fresh config creation**
```bash
rm -rf ~/.config/talk-it-out
python -m talk_it_out.main config-edit
```
Expected: Creates config, opens in editor, validates on save

**Test 2: Invalid config handling**
- Edit config to set `model = "invalid"` in `[whisper]` section
- Save and exit
- Should show validation errors
- Decline re-edit option

**Test 3: EDITOR environment variable**
```bash
EDITOR=vi python -m talk_it_out.main config-edit
```
Expected: Opens in vi instead of nano

**Test 4: Valid edit**
- Run config-edit
- Change log level to "DEBUG"
- Save and exit
- Should show "✅ Config validated successfully"

---

## Phase 8: Integration Testing

### Task 1: Create Integration Test Script

**Files:**
- Create: `tests/integration/test_cli_framework.sh`

**Step 1: Create test directory**

Run:
```bash
mkdir -p tests/integration
```

**Step 2: Create integration test script**

Create `tests/integration/test_cli_framework.sh`:
```bash
#!/bin/bash
# Integration tests for CLI framework
# Tests end-to-end scenarios with real config, logging, and signal handling

set -e  # Exit on error

echo "=== CLI Framework Integration Tests ==="
echo ""

# Cleanup function
cleanup() {
    echo "Cleaning up test artifacts..."
    rm -rf ~/.config/talk-it-out-test
    rm -f /tmp/test-config.toml
}

# Run cleanup on exit
trap cleanup EXIT

echo "Test 1: Fresh install - default config creation"
rm -rf ~/.config/talk-it-out
python -m talk_it_out.main run --log-level INFO &
PID=$!
sleep 2
kill -INT $PID
wait $PID
EXIT_CODE=$?

if [ -f ~/.config/talk-it-out/config.toml ]; then
    echo "✅ Test 1 passed: Default config created"
else
    echo "❌ Test 1 failed: Default config not created"
    exit 1
fi

if [ $EXIT_CODE -eq 130 ]; then
    echo "✅ Test 1 passed: Correct exit code (130) on SIGINT"
else
    echo "❌ Test 1 failed: Expected exit code 130, got $EXIT_CODE"
    exit 1
fi

echo ""
echo "Test 2: Invalid config - validation error"
echo "[whisper]" >> ~/.config/talk-it-out/config.toml
echo 'model = "invalid"' >> ~/.config/talk-it-out/config.toml

if python -m talk_it_out.main run 2>&1 | grep -q "invalid"; then
    echo "✅ Test 2 passed: Invalid config detected"
else
    echo "❌ Test 2 failed: Invalid config not detected"
    exit 1
fi

echo ""
echo "Test 3: Custom config path"
rm -f /tmp/test-config.toml
python -m talk_it_out.main run --config /tmp/test-config.toml --log-level DEBUG &
PID=$!
sleep 2
kill -INT $PID
wait $PID

if [ -f /tmp/test-config.toml ]; then
    echo "✅ Test 3 passed: Custom config path works"
else
    echo "❌ Test 3 failed: Custom config not created"
    exit 1
fi

echo ""
echo "Test 4: Log level override"
rm -rf ~/.config/talk-it-out
if python -m talk_it_out.main run --log-level DEBUG 2>&1 | grep -q "DEBUG"; then
    echo "✅ Test 4 passed: Log level override works"
    # Kill the background process
    pkill -f "talk_it_out.main run" || true
else
    echo "❌ Test 4 failed: Debug logs not shown"
    pkill -f "talk_it_out.main run" || true
    exit 1
fi

echo ""
echo "Test 5: SIGTERM handling"
rm -rf ~/.config/talk-it-out
python -m talk_it_out.main run &
PID=$!
sleep 2
kill -TERM $PID
wait $PID
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test 5 passed: Correct exit code (0) on SIGTERM"
else
    echo "❌ Test 5 failed: Expected exit code 0, got $EXIT_CODE"
    exit 1
fi

echo ""
echo "=== All integration tests passed! ==="
```

**Step 3: Make script executable**

Run:
```bash
chmod +x tests/integration/test_cli_framework.sh
```

**Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test: add integration test script

Tests cover:
- Fresh install with default config
- Invalid config validation
- Custom config path
- Log level override
- SIGINT/SIGTERM handling
- Exit codes"
```

### Task 2: Run Integration Tests

**Files:**
None (testing only)

**Step 1: Run full integration test suite**

Run:
```bash
./tests/integration/test_cli_framework.sh
```

Expected: All tests pass

**Step 2: If any tests fail, fix the issues**

Review error output, fix code, rerun tests.

**Step 3: Run all unit tests**

Run:
```bash
pytest tests/framework/ -v
```

Expected: All unit tests pass

**Step 4: Commit any fixes**

If fixes were needed:
```bash
git add [fixed files]
git commit -m "fix: address integration test failures

[description of what was fixed]"
```

### Task 3: Test Entry Point Installation (Optional)

**Files:**
None (testing only)

**This task is optional - only run if you want to test the installed command.**

**Step 1: Install package in development mode**

Run:
```bash
uv pip install -e .
```

**Step 2: Test installed command**

Run:
```bash
talk-it-out --help
```

Expected: Shows help for both commands

**Step 3: Test run command via entry point**

Run:
```bash
talk-it-out run --log-level INFO &
PID=$!
sleep 2
kill -INT $PID
wait $PID
```

Expected: Works identically to `python -m talk_it_out.main run`

**Step 4: Test config-edit via entry point**

Run:
```bash
talk-it-out config-edit
```

Expected: Opens config in editor

### Task 4: Final Documentation Check

**Files:**
- Modify: `README.md`

**Step 1: Update README with usage instructions**

Replace contents of `README.md`:
```markdown
# talk-it-out

Voice-to-text utility for Linux/KDE Plasma using Whisper.

## Status

**Phase 1 (CLI Framework): Complete**

The CLI application framework is implemented with:
- Configuration management (TOML)
- Structured logging (structlog)
- Signal handling with cleanup timeout
- Permission checks for input group
- Subcommands: `run`, `config-edit`

**Next:** Phase 1.5 will add keyboard monitoring with python-evdev.

## Installation

### Prerequisites

```bash
# Add user to input group (required for keyboard monitoring)
sudo usermod -a -G input $USER
# Log out and log back in for group membership to take effect
```

### Development Setup

```bash
# Install dependencies
uv pip install -e .

# Run application
python -m talk_it_out.main run

# Or use installed command
talk-it-out run
```

## Usage

### Start Listener

```bash
# Run with default config
talk-it-out run

# Override log level
talk-it-out run --log-level DEBUG

# Use custom config
talk-it-out run --config /path/to/config.toml
```

### Edit Configuration

```bash
# Opens ~/.config/talk-it-out/config.toml in $EDITOR
talk-it-out config-edit
```

## Configuration

Config location: `~/.config/talk-it-out/config.toml`

```toml
[keys]
combination = ["super", "alt"]

[audio]
sample_rate = 16000
channels = 1
device = ""

[whisper]
model = "base"  # tiny, base, small, medium, large
language = ""

[paste]
method = "clipboard"

[logging]
level = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

## Development

### Run Tests

```bash
# Unit tests
pytest tests/framework/ -v

# Integration tests
./tests/integration/test_cli_framework.sh
```

### Project Structure

```
src/talk_it_out/
├── main.py                    # Typer CLI app
├── framework/
│   ├── config.py              # Configuration management
│   ├── logging_setup.py       # Logging configuration
│   ├── permissions.py         # Permission checks
│   └── signals.py             # Signal handling
└── commands/
    └── config_edit.py         # Config edit command
```

## License

[To be determined]
```

**Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: update README with Phase 1 completion status

Documents:
- Installation prerequisites
- Usage examples
- Configuration format
- Development setup
- Testing"
```

### Task 5: Final Verification

**Files:**
None (verification only)

**Run through this checklist manually:**

- [ ] `python -m talk_it_out.main --help` shows both commands
- [ ] `python -m talk_it_out.main run` starts and responds to Ctrl-C
- [ ] Default config is created at `~/.config/talk-it-out/config.toml`
- [ ] Invalid config shows validation errors
- [ ] `--log-level DEBUG` shows debug messages
- [ ] `python -m talk_it_out.main config-edit` opens editor
- [ ] All unit tests pass: `pytest tests/framework/ -v`
- [ ] Integration tests pass: `./tests/integration/test_cli_framework.sh`
- [ ] User is prompted about input group if not a member

**If all checks pass, Phase 1 (CLI Framework) is complete!**
