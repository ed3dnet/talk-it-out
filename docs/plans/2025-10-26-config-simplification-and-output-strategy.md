# Config Simplification and Output Strategy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify user config with override system and implement clipboard-based paste output

**Architecture:** Two-layer config (internal defaults + user overrides), pluggable output strategy framework with WlClipSimplePaste (wl-clipboard + ydotool)

**Tech Stack:** Python, wl-clipboard, ydotool, pytest, structlog

**Scope:** 6 phases from original design

**Codebase verified:** 2025-10-26

---

## Phase 1: Config Merge Infrastructure

### Task 1: Add merge_configs() pure function

**Files:**
- Modify: `src/talk_it_out/framework/config.py` (add after line 72, before `validate_config()`)
- Test: `tests/framework/test_config_merge.py` (create new)

**Step 1: Write the failing test**

Create `tests/framework/test_config_merge.py`:

```python
# pattern: Mixed (test file)
# Tests require I/O for validation but test pure merge logic

import pytest
from talk_it_out.framework.config import merge_configs, default_config


def test_merge_empty_user_config_returns_defaults():
    """Empty user config should return all defaults."""
    defaults = default_config()
    user = {}

    result = merge_configs(defaults, user)

    assert result == defaults


def test_merge_user_overrides_top_level_value():
    """User can override top-level values."""
    defaults = {"logging": {"level": "INFO"}}
    user = {"logging": {"level": "DEBUG"}}

    result = merge_configs(defaults, user)

    assert result["logging"]["level"] == "DEBUG"


def test_merge_partial_section_preserves_defaults():
    """User can override one value in section, others stay default."""
    defaults = {
        "whisper": {
            "model": "turbo",
            "language": "en",
            "beam_size": 5,
        }
    }
    user = {
        "whisper": {
            "model": "base",
        }
    }

    result = merge_configs(defaults, user)

    assert result["whisper"]["model"] == "base"
    assert result["whisper"]["language"] == "en"
    assert result["whisper"]["beam_size"] == 5


def test_merge_replaces_arrays_not_merges():
    """Arrays are replaced entirely, not merged."""
    defaults = {
        "keys": {
            "combos": {
                "record_for_paste": [["KEY_A"], ["KEY_B"]],
            }
        }
    }
    user = {
        "keys": {
            "combos": {
                "record_for_paste": [["KEY_C"]],
            }
        }
    }

    result = merge_configs(defaults, user)

    assert result["keys"]["combos"]["record_for_paste"] == [["KEY_C"]]


def test_merge_adds_user_only_section():
    """User can add sections not in defaults (though unusual)."""
    defaults = {"logging": {"level": "INFO"}}
    user = {"custom": {"value": "test"}}

    result = merge_configs(defaults, user)

    assert result["logging"]["level"] == "INFO"
    assert result["custom"]["value"] == "test"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_config_merge.py -v`

Expected: FAIL with "cannot import name 'merge_configs'"

**Step 3: Write minimal implementation**

Add to `src/talk_it_out/framework/config.py` after line 72 (after `get_config_path()`):

```python
def merge_configs(defaults: dict, user: dict) -> dict:
    """Deep merge user config over defaults.

    Args:
        defaults: Complete config with all defaults
        user: User overrides (can be partial)

    Returns:
        Merged config dict

    Notes:
        - Deep merge at section level
        - User values override defaults
        - Arrays are replaced entirely, not merged
        - Preserves defaults for omitted user values
    """
    result = defaults.copy()

    for key, user_value in user.items():
        if key in result and isinstance(result[key], dict) and isinstance(user_value, dict):
            # Deep merge dictionaries
            result[key] = _merge_dicts(result[key], user_value)
        else:
            # Replace value (including arrays)
            result[key] = user_value

    return result


def _merge_dicts(default_dict: dict, user_dict: dict) -> dict:
    """Recursively merge two dictionaries.

    Args:
        default_dict: Default values
        user_dict: User override values

    Returns:
        Merged dictionary
    """
    result = default_dict.copy()

    for key, user_value in user_dict.items():
        if key in result and isinstance(result[key], dict) and isinstance(user_value, dict):
            # Recursively merge nested dicts
            result[key] = _merge_dicts(result[key], user_value)
        else:
            # Replace value
            result[key] = user_value

    return result
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_config_merge.py -v`

Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/config.py tests/framework/test_config_merge.py
git commit -m "feat: add config merge functionality

Add merge_configs() pure function to support user config overrides.
Deep merges user values over defaults while preserving unspecified
defaults. Arrays are replaced entirely, not merged."
```

### Task 2: Update default_config() to include [output] section

**Files:**
- Modify: `src/talk_it_out/framework/config.py:18-52`
- Test: `tests/framework/test_config.py` (update existing tests)

**Step 1: Write the failing test**

Add to `tests/framework/test_config.py` after line 75 (in test validation section):

```python
def test_validate_config_requires_output_section():
    """Config must have [output] section."""
    cfg = default_config()
    del cfg["output"]

    with pytest.raises(ValueError, match="output"):
        validate_config(cfg)


def test_validate_config_requires_output_strategy():
    """Config must specify output strategy."""
    cfg = default_config()
    del cfg["output"]["strategy"]

    with pytest.raises(ValueError, match="strategy"):
        validate_config(cfg)


def test_validate_config_accepts_wl_clip_simplepaste_strategy():
    """wl-clip-simplepaste is valid strategy."""
    cfg = default_config()
    cfg["output"]["strategy"] = "wl-clip-simplepaste"

    validate_config(cfg)  # Should not raise


def test_validate_config_rejects_unknown_strategy():
    """Unknown strategies are rejected."""
    cfg = default_config()
    cfg["output"]["strategy"] = "invalid-strategy"

    with pytest.raises(ValueError, match="strategy"):
        validate_config(cfg)


def test_validate_config_accepts_wl_clip_targets():
    """wl-clip targets can be clipboard and/or primary."""
    cfg = default_config()
    cfg["output"]["wl-clip"] = {"targets": ["clipboard"]}
    validate_config(cfg)

    cfg["output"]["wl-clip"] = {"targets": ["primary"]}
    validate_config(cfg)

    cfg["output"]["wl-clip"] = {"targets": ["clipboard", "primary"]}
    validate_config(cfg)


def test_validate_config_rejects_invalid_wl_clip_targets():
    """Invalid clipboard targets are rejected."""
    cfg = default_config()
    cfg["output"]["wl-clip"] = {"targets": ["invalid"]}

    with pytest.raises(ValueError, match="target"):
        validate_config(cfg)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_config.py::test_validate_config_requires_output_section -v`

Expected: FAIL with "KeyError: 'output'" (because default_config doesn't have it yet)

**Step 3: Update default_config() and add validation**

Modify `src/talk_it_out/framework/config.py`:

Replace lines 46-48 (`"paste": {"method": "clipboard"}`) with:

```python
        "output": {
            "strategy": "wl-clip-simplepaste",
            "wl-clip": {
                "targets": ["clipboard", "primary"],
                "ydotool_socket": "",  # Empty = use YDOTOOL_SOCKET env var or ydotool default
            },
        },
```

Add validation logic in `validate_config()` after line 175 (after whisper validation, before logging):

```python
    # Validate output section
    if "output" not in cfg:
        raise ValueError("Missing [output] section in config")

    output = cfg["output"]

    if "strategy" not in output:
        raise ValueError("Missing 'strategy' in [output] section")

    valid_strategies = {"wl-clip-simplepaste"}
    if output["strategy"] not in valid_strategies:
        raise ValueError(
            f"Invalid output strategy: '{output['strategy']}'. "
            f"Valid: {', '.join(valid_strategies)}"
        )

    # Validate strategy-specific config
    if output["strategy"] == "wl-clip-simplepaste":
        if "wl-clip" in output:
            wl_clip = output["wl-clip"]
            if "targets" in wl_clip:
                valid_targets = {"clipboard", "primary"}
                for target in wl_clip["targets"]:
                    if target not in valid_targets:
                        raise ValueError(
                            f"Invalid clipboard target: '{target}'. "
                            f"Valid: {', '.join(valid_targets)}"
                        )

            # ydotool_socket is optional - if provided, must be string
            if "ydotool_socket" in wl_clip:
                if not isinstance(wl_clip["ydotool_socket"], str):
                    raise ValueError("ydotool_socket must be a string path")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_config.py -v -k "output or wl_clip"`

Expected: PASS (all new output tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/config.py tests/framework/test_config.py
git commit -m "feat: add [output] section to config schema

Replace [paste] section with [output] section supporting pluggable
strategies. Add validation for output.strategy and wl-clip.targets.
Default strategy is wl-clip-simplepaste."
```

### Task 3: Modify load_config() to merge before validating

**Files:**
- Modify: `src/talk_it_out/framework/config_io.py:27-57`
- Test: `tests/framework/test_config.py` (integration test)

**Step 1: Write the failing test**

Add to `tests/framework/test_config.py` after validation tests:

```python
def test_load_config_merges_user_overrides_with_defaults(tmp_path):
    """load_config merges user config over defaults before validating."""
    from talk_it_out.framework.config_io import load_config
    import tomli_w

    # Create minimal user config (only overrides)
    user_config = {
        "keys": {
            "combos": {
                "record_for_paste": [["KEY_A"]],
            }
        },
        "whisper": {
            "model": "base",  # Override default "turbo"
        },
    }

    config_path = tmp_path / "config.toml"
    with open(config_path, "wb") as f:
        tomli_w.dump(user_config, f)

    result = load_config(config_path)

    # User override should be present
    assert result["whisper"]["model"] == "base"

    # Defaults should fill in missing values
    assert result["whisper"]["language"] == "en"
    assert result["whisper"]["beam_size"] == 5
    assert result["audio"]["sample_rate"] == 16000
    assert result["output"]["strategy"] == "wl-clip-simplepaste"


def test_load_config_creates_default_if_missing(tmp_path):
    """load_config creates default config if file doesn't exist."""
    from talk_it_out.framework.config_io import load_config

    config_path = tmp_path / "missing.toml"

    result = load_config(config_path)

    # Should return complete default config
    assert result == default_config()
    # File should be created
    assert config_path.exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_config.py::test_load_config_merges_user_overrides_with_defaults -v`

Expected: FAIL - merged config not validated or values not merged

**Step 3: Modify load_config() to merge**

Modify `src/talk_it_out/framework/config_io.py`:

Update imports at top (after line 4):

```python
from .config import default_config, validate_config, merge_configs
```

Replace `load_config()` function (lines 27-57) with:

```python
def load_config(config_path: Path | str) -> dict:
    """Load and validate configuration from TOML file.

    Args:
        config_path: Path to config file

    Returns:
        Complete, validated config dict

    Notes:
        - Merges user config over internal defaults
        - Creates default config file if missing
        - Validates merged config before returning
    """
    path = Path(config_path)

    if not path.exists():
        # Create default config file
        defaults = default_config()
        save_config(defaults, path)
        return defaults

    # Load user config
    with open(path, "rb") as f:
        user_config = tomllib.load(f)

    # Merge user overrides over defaults
    defaults = default_config()
    merged = merge_configs(defaults, user_config)

    # Validate merged config
    validate_config(merged)

    return merged
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_config.py -v -k "load_config"`

Expected: PASS (both load_config tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/config_io.py tests/framework/test_config.py
git commit -m "feat: merge user config over defaults in load_config

load_config now merges user TOML over internal defaults before
validation. Users only need to specify overrides in their config file.
Validates merged result to ensure completeness."
```

### Task 4: Create initialize_config() for minimal starter config

**Files:**
- Modify: `src/talk_it_out/framework/config_io.py` (add new function after `save_config()`)
- Test: `tests/framework/test_config.py` (add test)

**Step 1: Write the failing test**

Add to `tests/framework/test_config.py`:

```python
def test_initialize_config_creates_minimal_user_config(tmp_path):
    """initialize_config creates guided minimal config."""
    from talk_it_out.framework.config_io import initialize_config
    import tomli

    config_path = tmp_path / "config.toml"

    initialize_config(config_path)

    # File should exist
    assert config_path.exists()

    # Load and verify contents
    with open(config_path, "rb") as f:
        config = tomli.load(f)

    # Should have keyboard combo (required)
    assert "keys" in config
    assert "combos" in config["keys"]
    assert "record_for_paste" in config["keys"]["combos"]

    # Should have essential whisper settings
    assert "whisper" in config
    assert "model" in config["whisper"]
    assert "language" in config["whisper"]

    # Should have output strategy
    assert "output" in config
    assert "strategy" in config["output"]
    assert config["output"]["strategy"] == "wl-clip-simplepaste"

    # Should NOT have all the advanced whisper settings
    assert "beam_size" not in config["whisper"]
    assert "vad_filter" not in config["whisper"]

    # Should NOT have audio section (uses defaults)
    assert "audio" not in config


def test_initialize_config_does_not_overwrite_existing(tmp_path):
    """initialize_config doesn't overwrite existing config."""
    from talk_it_out.framework.config_io import initialize_config
    import tomli_w

    config_path = tmp_path / "config.toml"

    # Create existing config
    existing = {"custom": "value"}
    with open(config_path, "wb") as f:
        tomli_w.dump(existing, f)

    initialize_config(config_path)

    # Should preserve existing content
    with open(config_path, "rb") as f:
        config = tomli.load(f)

    assert config == existing
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_config.py::test_initialize_config_creates_minimal_user_config -v`

Expected: FAIL with "cannot import name 'initialize_config'"

**Step 3: Write minimal implementation**

Add to `src/talk_it_out/framework/config_io.py` after `save_config()` (around line 25):

```python
def initialize_config(config_path: Path | str) -> None:
    """Create minimal starter config file with guided defaults.

    Creates config with only settings users commonly change:
    - Keyboard combo (required)
    - Whisper model and language (commonly tuned)
    - Output strategy (shows what's configurable)

    Advanced settings use internal defaults via merge.

    Args:
        config_path: Where to create config file

    Notes:
        - Does not overwrite existing config
        - Creates parent directories if needed
    """
    path = Path(config_path)

    if path.exists():
        return  # Don't overwrite

    # Minimal starter config (guided defaults)
    minimal_config = {
        "keys": {
            "combos": {
                "record_for_paste": [
                    ["KEY_LEFTMETA", "KEY_LEFTALT"],
                ],
            },
        },
        "whisper": {
            "model": "turbo",
            "language": "en",
        },
        "output": {
            "strategy": "wl-clip-simplepaste",
        },
    }

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save minimal config
    save_config(minimal_config, path)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/framework/test_config.py -v -k "initialize_config"`

Expected: PASS (both initialize_config tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/config_io.py tests/framework/test_config.py
git commit -m "feat: add initialize_config for minimal starter config

Add initialize_config() to create guided minimal user config with only
essential settings (keyboard combo, whisper model/language, output
strategy). Advanced settings use internal defaults via merge."
```

### Task 5: Update config-edit command to use initialize_config

**Files:**
- Modify: `src/talk_it_out/commands/config_edit.py` (find and update initialization logic)
- Test: Manual testing (verify config-edit creates minimal config)

**Step 1: Identify current initialization**

Read current `config_edit.py` to see how it creates config:

Run: `uv run python -c "from pathlib import Path; print(Path('src/talk_it_out/commands/config_edit.py').read_text())"`

**Step 2: Update to use initialize_config**

Modify `src/talk_it_out/commands/config_edit.py`:

Update imports (top of file):

```python
from talk_it_out.framework.config_io import initialize_config
from talk_it_out.framework.config import get_config_path
```

Find the logic that creates config if missing (likely checking `if not config_path.exists()`) and replace with:

```python
    # Create minimal starter config if doesn't exist
    initialize_config(config_path)
```

**Step 3: Manually test config-edit command**

Run: `rm ~/.config/talk-it-out/config.toml` (if exists)
Run: `uv run python -m talk_it_out.main config-edit`

Expected: Opens editor with minimal config (keys.combos, whisper model/language, output.strategy only)

**Step 4: Verify minimal config loads correctly**

Run: `uv run python -c "from talk_it_out.framework.config_io import load_config; from talk_it_out.framework.config import get_config_path; cfg = load_config(get_config_path()); print('whisper.beam_size:', cfg['whisper']['beam_size'])"`

Expected: Output shows `whisper.beam_size: 5` (from defaults, not in user file)

**Step 5: Commit**

```bash
git add src/talk_it_out/commands/config_edit.py
git commit -m "refactor: use initialize_config in config-edit command

Update config-edit to use initialize_config() for creating minimal
starter config instead of full default_config()."
```

---

## Phase 2: Output Strategy Framework

### Task 1: Create output package structure

**Files:**
- Create: `src/talk_it_out/output/__init__.py`
- Create: `src/talk_it_out/output/base.py`
- Create: `src/talk_it_out/output/factory.py`
- Create: `src/talk_it_out/output/strategies/__init__.py`

**Step 1: Create base.py with abstract interface**

Create `src/talk_it_out/output/base.py`:

```python
# pattern: Functional Core
# Pure abstract interface definition

from abc import ABC, abstractmethod


class OutputStrategy(ABC):
    """Base class for output strategies.

    Output strategies handle getting transcribed text into the target
    application after speech recognition completes.
    """

    @abstractmethod
    def paste_text(self, text: str) -> None:
        """Paste text into current application.

        Args:
            text: Transcribed text to paste

        Raises:
            OutputError: If paste operation fails
        """
        pass

    @abstractmethod
    def verify_dependencies(self) -> None:
        """Check required tools/dependencies are available.

        Called once at application startup to fail fast if dependencies
        are missing.

        Raises:
            OutputError: If dependencies missing, with helpful install message
        """
        pass


class OutputError(Exception):
    """Raised when output operation fails.

    This includes:
    - Missing dependencies (tools not installed, daemon not running)
    - Runtime failures (clipboard timeout, keystroke injection failed)
    - Configuration errors (invalid strategy settings)
    """
    pass
```

**Step 2: Create factory.py**

Create `src/talk_it_out/output/factory.py`:

```python
# pattern: Functional Core
# Pure factory function for strategy selection

from .base import OutputStrategy


def create_output_strategy(config: dict) -> OutputStrategy:
    """Create output strategy from config.

    Args:
        config: Full config dict with [output] section

    Returns:
        OutputStrategy instance configured from config

    Raises:
        ValueError: If strategy name unknown
    """
    strategy_name = config["output"]["strategy"]

    if strategy_name == "wl-clip-simplepaste":
        # Lazy import to avoid loading strategies not in use
        from .strategies.wl_clip import WlClipSimplePaste
        wl_clip_config = config["output"].get("wl-clip", {})
        return WlClipSimplePaste(wl_clip_config)
    else:
        valid_strategies = ["wl-clip-simplepaste"]
        raise ValueError(
            f"Unknown output strategy: '{strategy_name}'. "
            f"Valid strategies: {', '.join(valid_strategies)}"
        )
```

**Step 3: Create package __init__.py with exports**

Create `src/talk_it_out/output/__init__.py`:

```python
# pattern: Functional Core
# Public API exports for output package

from .base import OutputStrategy, OutputError
from .factory import create_output_strategy

__all__ = [
    "OutputStrategy",
    "OutputError",
    "create_output_strategy",
]
```

**Step 4: Create strategies package**

Create `src/talk_it_out/output/strategies/__init__.py`:

```python
# pattern: Functional Core
# Empty init for strategies subpackage
```

**Step 5: Verify imports work**

Run: `uv run python -c "from talk_it_out.output import OutputStrategy, OutputError, create_output_strategy; print('Imports successful')"`

Expected: Output "Imports successful"

**Step 6: Commit**

```bash
git add src/talk_it_out/output/
git commit -m "feat: add output strategy framework

Create pluggable output strategy architecture:
- OutputStrategy abstract base class
- OutputError exception
- create_output_strategy() factory function
- Strategies subpackage for implementations

Follows Functional Core pattern with lazy loading."
```

### Task 2: Add factory tests

**Files:**
- Create: `tests/output/test_factory.py`

**Step 1: Write tests for factory**

Create `tests/output/test_factory.py`:

```python
# pattern: Mixed (test file)
# Tests factory function (pure) but may need imports (I/O)

import pytest
from talk_it_out.output import create_output_strategy, OutputError


def test_create_output_strategy_unknown_strategy():
    """Factory raises ValueError for unknown strategy."""
    config = {
        "output": {
            "strategy": "invalid-strategy",
        }
    }

    with pytest.raises(ValueError, match="Unknown output strategy"):
        create_output_strategy(config)


def test_create_output_strategy_error_message_lists_valid():
    """Error message shows valid strategy names."""
    config = {
        "output": {
            "strategy": "invalid",
        }
    }

    with pytest.raises(ValueError, match="wl-clip-simplepaste"):
        create_output_strategy(config)


@pytest.mark.xfail(reason="WlClipSimplePaste not implemented yet (Phase 3)")
def test_create_wl_clip_simplepaste_strategy():
    """Factory creates WlClipSimplePaste for wl-clip-simplepaste strategy."""
    config = {
        "output": {
            "strategy": "wl-clip-simplepaste",
            "wl-clip": {
                "targets": ["clipboard"],
            },
        }
    }

    strategy = create_output_strategy(config)

    # Should be WlClipSimplePaste instance (once implemented in Phase 3)
    # For now, just verify it doesn't raise
    assert strategy is not None


@pytest.mark.xfail(reason="WlClipSimplePaste not implemented yet (Phase 3)")
def test_create_wl_clip_simplepaste_without_config():
    """Factory creates WlClipSimplePaste with empty config if not specified."""
    config = {
        "output": {
            "strategy": "wl-clip-simplepaste",
            # No wl-clip section
        }
    }

    strategy = create_output_strategy(config)

    # Should use defaults
    assert strategy is not None
```

**Step 2: Run tests (will fail - WlClipSimplePaste doesn't exist yet)**

Run: `uv run pytest tests/output/test_factory.py -v`

Expected: 2 PASSED, 2 XFAIL

**Step 3: Commit**

```bash
git add tests/output/test_factory.py
git commit -m "test: add factory tests for output strategies

Test create_output_strategy() with unknown strategies and valid
wl-clip-simplepaste strategy. Mark WlClipSimplePaste tests as xfail
until Phase 3 implementation."
```

---

## Phase 3: WlClipSimplePaste Implementation

### Task 1: Functional Core - pure clipboard/command functions

**Files:**
- Create: `src/talk_it_out/output/strategies/wl_clip.py`
- Test: `tests/output/test_wl_clip_core.py`

**Step 1: Write failing tests for pure functions**

Create `tests/output/test_wl_clip_core.py`:

```python
# pattern: Mixed (test file)
# Tests pure functions (Functional Core)

import pytest
from talk_it_out.output.strategies.wl_clip import (
    verify_clipboard_content,
    build_wl_copy_commands,
    build_shift_insert_command,
)


def test_verify_clipboard_content_exact_match():
    """Returns True when content matches exactly."""
    expected = "Hello, world!"
    actual = "Hello, world!"

    assert verify_clipboard_content(expected, actual) is True


def test_verify_clipboard_content_mismatch():
    """Returns False when content differs."""
    expected = "Hello"
    actual = "Goodbye"

    assert verify_clipboard_content(expected, actual) is False


def test_verify_clipboard_content_whitespace_sensitive():
    """Whitespace differences cause mismatch."""
    expected = "Hello"
    actual = "Hello\n"

    assert verify_clipboard_content(expected, actual) is False


def test_build_wl_copy_commands_clipboard_target():
    """Builds wl-copy command for clipboard target."""
    text = "test content"
    targets = ["clipboard"]

    commands = build_wl_copy_commands(text, targets)

    assert len(commands) == 1
    cmd, input_text = commands[0]
    assert cmd == ["wl-copy", "--type", "text/plain"]
    assert input_text == text


def test_build_wl_copy_commands_primary_target():
    """Builds wl-copy command for primary selection."""
    text = "test content"
    targets = ["primary"]

    commands = build_wl_copy_commands(text, targets)

    assert len(commands) == 1
    cmd, input_text = commands[0]
    assert cmd == ["wl-copy", "--primary", "--type", "text/plain"]
    assert input_text == text


def test_build_wl_copy_commands_both_targets():
    """Builds commands for both clipboard and primary."""
    text = "test content"
    targets = ["clipboard", "primary"]

    commands = build_wl_copy_commands(text, targets)

    assert len(commands) == 2
    assert commands[0][0] == ["wl-copy", "--type", "text/plain"]
    assert commands[1][0] == ["wl-copy", "--primary", "--type", "text/plain"]
    assert all(cmd[1] == text for cmd in commands)


def test_build_shift_insert_command():
    """Builds ydotool command for Shift+Insert."""
    cmd = build_shift_insert_command()

    # Left shift (42) press, Insert (110) press, Insert release, shift release
    assert cmd == ["ydotool", "key", "42:1", "110:1", "110:0", "42:0"]


def test_get_ydotool_env_with_socket():
    """Custom socket path sets YDOTOOL_SOCKET env var."""
    from talk_it_out.output.strategies.wl_clip import get_ydotool_env

    env = get_ydotool_env("/tmp/custom-socket")

    assert env == {"YDOTOOL_SOCKET": "/tmp/custom-socket"}


def test_get_ydotool_env_empty_socket():
    """Empty socket path returns empty env (uses default)."""
    from talk_it_out.output.strategies.wl_clip import get_ydotool_env

    env = get_ydotool_env("")

    assert env == {}
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/output/test_wl_clip_core.py -v`

Expected: FAIL with "cannot import name 'verify_clipboard_content'"

**Step 3: Write minimal implementation - Functional Core only**

Create `src/talk_it_out/output/strategies/wl_clip.py`:

```python
# pattern: Mixed (unavoidable)
# Functional Core (pure functions) + Imperative Shell (WlClipSimplePaste class)
# Mixed because both business logic and I/O live in same module, but separated
# into different functions/methods for testability

from ..base import OutputStrategy, OutputError


# ============================================================================
# Functional Core - Pure Functions
# ============================================================================


def verify_clipboard_content(expected: str, actual: str) -> bool:
    """Exact text comparison for clipboard verification.

    Args:
        expected: Text that should be in clipboard
        actual: Text retrieved from clipboard

    Returns:
        True if content matches exactly, False otherwise
    """
    return expected == actual


def build_wl_copy_commands(text: str, targets: list[str]) -> list[tuple[list[str], str]]:
    """Build wl-copy command lists for each target.

    Args:
        text: Text to copy to clipboard
        targets: List of clipboard targets ("clipboard", "primary")

    Returns:
        List of (command_args, input_text) tuples
    """
    commands = []
    for target in targets:
        if target == "clipboard":
            commands.append((["wl-copy", "--type", "text/plain"], text))
        elif target == "primary":
            commands.append((["wl-copy", "--primary", "--type", "text/plain"], text))
    return commands


def build_shift_insert_command() -> list[str]:
    """Build ydotool command for Shift+Insert keystroke.

    Key codes from Linux input-event-codes.h:
        42 = KEY_LEFTSHIFT
        110 = KEY_INSERT

    Format: KEYCODE:STATE where 1=press, 0=release

    Returns:
        Command args for ydotool
    """
    return ["ydotool", "key", "42:1", "110:1", "110:0", "42:0"]


def get_ydotool_env(socket_path: str) -> dict[str, str]:
    """Build environment dict for ydotool subprocess.

    Args:
        socket_path: Path to ydotool socket, or empty string to use default

    Returns:
        Environment dict with YDOTOOL_SOCKET if needed
    """
    if socket_path:
        return {"YDOTOOL_SOCKET": socket_path}
    return {}


# ============================================================================
# Imperative Shell - I/O Operations (to be implemented next)
# ============================================================================

class WlClipSimplePaste(OutputStrategy):
    """Output strategy using wl-clipboard + ydotool.

    Workflow:
        1. Copy text to clipboard(s) via wl-copy
        2. Poll wl-paste to verify clipboard ready
        3. Delay for ydotool virtual device recognition
        4. Send Shift+Insert keystroke via ydotool
    """

    def __init__(self, config: dict):
        """Initialize from [output.wl-clip] config section."""
        self.targets = config.get("targets", ["clipboard", "primary"])
        self.ydotool_socket = config.get("ydotool_socket", "")

    def verify_dependencies(self) -> None:
        """Check wl-copy, wl-paste, ydotool, ydotoold."""
        raise NotImplementedError("To be implemented in next task")

    def paste_text(self, text: str) -> None:
        """Copy to clipboard, verify, then paste."""
        raise NotImplementedError("To be implemented in next task")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/output/test_wl_clip_core.py -v`

Expected: PASS (all 8 tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/output/strategies/wl_clip.py tests/output/test_wl_clip_core.py
git commit -m "feat: add WlClipSimplePaste functional core

Add pure functions for clipboard operations:
- verify_clipboard_content() for exact matching
- build_wl_copy_commands() for command construction
- build_shift_insert_command() for ydotool keystroke

Stub out WlClipSimplePaste class (shell implementation next)."
```

### Task 2: Imperative Shell - dependency verification

**Files:**
- Modify: `src/talk_it_out/output/strategies/wl_clip.py`
- Test: `tests/output/test_wl_clip_integration.py`

**Step 1: Write failing test**

Create `tests/output/test_wl_clip_integration.py`:

```python
# pattern: Mixed (test file)
# Tests I/O operations with mocking

import pytest
from unittest.mock import patch, MagicMock
from talk_it_out.output.strategies.wl_clip import WlClipSimplePaste
from talk_it_out.output import OutputError


class TestDependencyVerification:
    """Tests for verify_dependencies() with mocked subprocess."""

    @patch('subprocess.run')
    def test_verify_dependencies_all_present(self, mock_run):
        """All tools present and ydotoold running - should not raise."""
        # Mock successful tool checks
        mock_run.return_value = MagicMock(returncode=0)

        strategy = WlClipSimplePaste({})

        strategy.verify_dependencies()  # Should not raise

        # Should check wl-copy, wl-paste, ydotool
        assert mock_run.call_count >= 3

    @patch('subprocess.run')
    def test_verify_dependencies_missing_wl_copy(self, mock_run):
        """Missing wl-copy raises OutputError with install instructions."""
        # wl-copy --help fails (not installed)
        def side_effect(cmd, *args, **kwargs):
            if 'wl-copy' in cmd:
                raise FileNotFoundError()
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="wl-copy"):
            strategy.verify_dependencies()

    @patch('subprocess.run')
    def test_verify_dependencies_missing_ydotool(self, mock_run):
        """Missing ydotool raises OutputError with install instructions."""
        def side_effect(cmd, *args, **kwargs):
            if 'ydotool' in cmd:
                raise FileNotFoundError()
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="ydotool"):
            strategy.verify_dependencies()

    @patch('subprocess.run')
    def test_verify_dependencies_daemon_not_running(self, mock_run):
        """ydotoold daemon not running raises OutputError."""
        # Tools present but pgrep ydotoold fails
        def side_effect(cmd, *args, **kwargs):
            if 'pgrep' in cmd and 'ydotoold' in cmd:
                return MagicMock(returncode=1)  # Not found
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="ydotoold"):
            strategy.verify_dependencies()

    @patch('subprocess.run')
    def test_verify_dependencies_error_includes_install_instructions(self, mock_run):
        """Error message includes distro-specific install commands."""
        mock_run.side_effect = FileNotFoundError()

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError) as exc_info:
            strategy.verify_dependencies()

        error_msg = str(exc_info.value)
        # Should mention at least one distro's install command
        assert any(pkg_mgr in error_msg for pkg_mgr in ["dnf", "apt", "pacman"])

    @patch('subprocess.run')
    @patch('os.access')
    @patch('pathlib.Path.exists')
    def test_verify_dependencies_socket_missing(self, mock_exists, mock_access, mock_run):
        """Custom socket path that doesn't exist raises OutputError."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = False

        strategy = WlClipSimplePaste({"ydotool_socket": "/tmp/missing-socket"})

        with pytest.raises(OutputError, match="socket not found"):
            strategy.verify_dependencies()

    @patch('subprocess.run')
    @patch('os.access')
    @patch('pathlib.Path.exists')
    def test_verify_dependencies_socket_not_writable(self, mock_exists, mock_access, mock_run):
        """Socket without write permissions raises OutputError."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True
        mock_access.return_value = False  # No read/write

        strategy = WlClipSimplePaste({"ydotool_socket": "/tmp/readonly-socket"})

        with pytest.raises(OutputError, match="not readable/writable"):
            strategy.verify_dependencies()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/output/test_wl_clip_integration.py::TestDependencyVerification -v`

Expected: FAIL with "NotImplementedError: To be implemented"

**Step 3: Implement verify_dependencies()**

Modify `src/talk_it_out/output/strategies/wl_clip.py`:

Add imports at top:

```python
import os
import subprocess
from pathlib import Path
import structlog

log = structlog.get_logger()
```

Replace `verify_dependencies()` stub in `WlClipSimplePaste` class:

```python
    def verify_dependencies(self) -> None:
        """Check wl-copy, wl-paste, ydotool, ydotoold.

        Raises:
            OutputError: With install instructions if missing
        """
        missing_tools = []

        # Check wl-copy
        try:
            subprocess.run(
                ["wl-copy", "--help"],
                capture_output=True,
                check=True,
            )
            log.debug("dependency_check", tool="wl-copy", status="found")
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing_tools.append("wl-copy")
            log.debug("dependency_check", tool="wl-copy", status="missing")

        # Check wl-paste
        try:
            subprocess.run(
                ["wl-paste", "--help"],
                capture_output=True,
                check=True,
            )
            log.debug("dependency_check", tool="wl-paste", status="found")
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing_tools.append("wl-paste")
            log.debug("dependency_check", tool="wl-paste", status="missing")

        # Check ydotool
        try:
            subprocess.run(
                ["ydotool", "help"],
                capture_output=True,
                check=True,
            )
            log.debug("dependency_check", tool="ydotool", status="found")
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing_tools.append("ydotool")
            log.debug("dependency_check", tool="ydotool", status="missing")

        # Check ydotoold daemon
        daemon_running = False
        try:
            result = subprocess.run(
                ["pgrep", "-x", "ydotoold"],
                capture_output=True,
            )
            daemon_running = result.returncode == 0
            log.debug("dependency_check", daemon="ydotoold", running=daemon_running)
        except FileNotFoundError:
            log.debug("dependency_check", daemon="ydotoold", status="pgrep_missing")

        # Build error message if any dependencies missing
        if missing_tools or not daemon_running:
            error_parts = [
                "Required tools not found for output strategy 'wl-clip-simplepaste'\n"
            ]

            if "wl-copy" in missing_tools or "wl-paste" in missing_tools:
                error_parts.append("Missing: wl-copy, wl-paste")
                error_parts.append("Install: sudo dnf install wl-clipboard    # Fedora/RHEL")
                error_parts.append("         sudo apt install wl-clipboard    # Debian/Ubuntu")
                error_parts.append("         sudo pacman -S wl-clipboard      # Arch\n")

            if "ydotool" in missing_tools:
                error_parts.append("Missing: ydotool")
                error_parts.append("Install: sudo dnf install ydotool         # Fedora/RHEL")
                error_parts.append("         sudo apt install ydotool         # Debian/Ubuntu")
                error_parts.append("         yay -S ydotool-git               # Arch (AUR)\n")

            if not daemon_running and "ydotool" not in missing_tools:
                error_parts.append("ydotoold daemon not running:")
                error_parts.append("Start: sudo systemctl start ydotoold")
                error_parts.append("Enable: sudo systemctl enable ydotoold\n")

            error_parts.append("See: https://github.com/ReimuNotMoe/ydotool")

            raise OutputError("\n".join(error_parts))

        # Check ydotool socket if configured
        if self.ydotool_socket:
            socket_path = Path(self.ydotool_socket)

            if not socket_path.exists():
                raise OutputError(
                    f"ydotool socket not found: {self.ydotool_socket}\n"
                    f"Check YDOTOOL_SOCKET path or start ydotoold daemon"
                )

            # Check read/write permissions
            if not os.access(socket_path, os.R_OK | os.W_OK):
                raise OutputError(
                    f"ydotool socket not readable/writable: {self.ydotool_socket}\n"
                    f"Current user: {os.getenv('USER')}\n"
                    f"Socket permissions: {oct(socket_path.stat().st_mode)[-3:]}\n"
                    f"Fix: sudo chmod 666 {self.ydotool_socket}  # or add user to ydotool group"
                )

            log.debug("ydotool_socket_verified", path=self.ydotool_socket)

        log.info("output_dependencies_verified", strategy="wl-clip-simplepaste")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/output/test_wl_clip_integration.py::TestDependencyVerification -v`

Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/output/strategies/wl_clip.py tests/output/test_wl_clip_integration.py
git commit -m "feat: implement dependency verification for wl-clip

Add verify_dependencies() checking for wl-copy, wl-paste, ydotool,
and ydotoold daemon. Raises OutputError with distro-specific install
instructions if any missing."
```

### Task 3: Imperative Shell - clipboard copy and verify

**Files:**
- Modify: `src/talk_it_out/output/strategies/wl_clip.py`
- Test: `tests/output/test_wl_clip_integration.py`

**Step 1: Write failing tests with real clipboard**

Add to `tests/output/test_wl_clip_integration.py`:

```python
import subprocess
import shutil


def has_wl_clipboard() -> bool:
    """Check if wl-copy and wl-paste are available."""
    return shutil.which("wl-copy") is not None and shutil.which("wl-paste") is not None


@pytest.mark.skipif(not has_wl_clipboard(), reason="wl-clipboard not installed")
@pytest.mark.clipboard
class TestClipboardOperations:
    """Tests with real wl-copy/wl-paste (run single-threaded)."""

    def test_copy_to_clipboard_single_target(self):
        """Copying to clipboard target works."""
        strategy = WlClipSimplePaste({"targets": ["clipboard"]})
        text = "test content for clipboard"

        strategy._copy_to_clipboard(text)

        # Verify with wl-paste
        result = subprocess.run(
            ["wl-paste"],
            capture_output=True,
            text=True,
        )
        assert result.stdout == text

    def test_copy_to_primary_target(self):
        """Copying to primary selection works."""
        strategy = WlClipSimplePaste({"targets": ["primary"]})
        text = "test content for primary"

        strategy._copy_to_clipboard(text)

        # Verify with wl-paste --primary
        result = subprocess.run(
            ["wl-paste", "--primary"],
            capture_output=True,
            text=True,
        )
        assert result.stdout == text

    def test_copy_to_both_targets(self):
        """Copying to both clipboard and primary works."""
        strategy = WlClipSimplePaste({"targets": ["clipboard", "primary"]})
        text = "test content for both"

        strategy._copy_to_clipboard(text)

        # Verify both
        clipboard_result = subprocess.run(
            ["wl-paste"],
            capture_output=True,
            text=True,
        )
        primary_result = subprocess.run(
            ["wl-paste", "--primary"],
            capture_output=True,
            text=True,
        )

        assert clipboard_result.stdout == text
        assert primary_result.stdout == text

    def test_verify_clipboard_ready_succeeds(self):
        """verify_clipboard_ready succeeds when content matches."""
        strategy = WlClipSimplePaste({"targets": ["clipboard"]})
        text = "test verification content"

        # Set clipboard
        subprocess.run(
            ["wl-copy"],
            input=text.encode(),
            check=True,
        )

        # Should not raise
        strategy._verify_clipboard_ready(text)

    def test_verify_clipboard_ready_timeout(self):
        """verify_clipboard_ready times out if content doesn't match."""
        strategy = WlClipSimplePaste({"targets": ["clipboard"]})
        strategy.clipboard_timeout = 0.3  # Short timeout for test

        # Set different content
        subprocess.run(
            ["wl-copy"],
            input=b"wrong content",
            check=True,
        )

        # Should timeout
        with pytest.raises(OutputError, match="timeout"):
            strategy._verify_clipboard_ready("expected content")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/output/test_wl_clip_integration.py::TestClipboardOperations -v -m clipboard`

Expected: FAIL with "AttributeError: '_copy_to_clipboard'" or similar

**Step 3: Implement clipboard operations**

Modify `src/talk_it_out/output/strategies/wl_clip.py`:

Update `__init__` to add timing constants:

```python
    def __init__(self, config: dict):
        """Initialize from [output.wl-clip] config section."""
        self.targets = config.get("targets", ["clipboard", "primary"])
        self.clipboard_timeout = 2.0  # seconds
        self.poll_interval = 0.1  # seconds
        self.virtual_device_delay = 0.5  # seconds
```

Add import at top:

```python
import time
```

Add `_copy_to_clipboard()` method after `verify_dependencies()`:

```python
    def _copy_to_clipboard(self, text: str) -> None:
        """Run wl-copy for each configured target.

        Args:
            text: Text to copy

        Raises:
            OutputError: If wl-copy fails
        """
        commands = build_wl_copy_commands(text, self.targets)

        for cmd, input_text in commands:
            log.debug("running_wl_copy", command=cmd)
            try:
                result = subprocess.run(
                    cmd,
                    input=input_text.encode(),
                    capture_output=True,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode() if e.stderr else ""
                raise OutputError(f"wl-copy failed: {stderr}")
            except FileNotFoundError:
                raise OutputError("wl-copy not found - run verify_dependencies() first")
```

Add `_verify_clipboard_ready()` method:

```python
    def _verify_clipboard_ready(self, expected_text: str) -> None:
        """Poll wl-paste until content matches or timeout.

        Args:
            expected_text: Text that should be in clipboard

        Raises:
            OutputError: If verification times out
        """
        log.debug("verifying_clipboard")
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.clipboard_timeout:
                raise OutputError(
                    f"Clipboard verification timeout after {self.clipboard_timeout}s"
                )

            try:
                result = subprocess.run(
                    ["wl-paste"],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    actual = result.stdout
                    if verify_clipboard_content(expected_text, actual):
                        log.debug("clipboard_verified", elapsed_ms=int(elapsed * 1000))
                        return
            except FileNotFoundError:
                raise OutputError("wl-paste not found")

            time.sleep(self.poll_interval)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/output/test_wl_clip_integration.py::TestClipboardOperations -v -m clipboard -n 0`

Expected: PASS (all 5 clipboard tests) - Note the `-n 0` for single-threaded execution

**Step 5: Commit**

```bash
git add src/talk_it_out/output/strategies/wl_clip.py tests/output/test_wl_clip_integration.py
git commit -m "feat: implement clipboard copy and verification

Add _copy_to_clipboard() using wl-copy for each target.
Add _verify_clipboard_ready() with polling and timeout.
Tests use real wl-clipboard, marked for single-threaded execution."
```

### Task 4: Imperative Shell - keystroke injection

**Files:**
- Modify: `src/talk_it_out/output/strategies/wl_clip.py`
- Test: `tests/output/test_wl_clip_integration.py`

**Step 1: Write failing test with mocked ydotool**

Add to `tests/output/test_wl_clip_integration.py`:

```python
class TestKeystrokeInjection:
    """Tests for _send_shift_insert() with mocked ydotool."""

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_send_shift_insert_success(self, mock_run):
        """Successful ydotool call logs and returns."""
        mock_run.return_value = MagicMock(returncode=0)

        strategy = WlClipSimplePaste({})

        strategy._send_shift_insert()  # Should not raise

        # Verify ydotool called with correct key sequence
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["ydotool", "key", "42:1", "110:1", "110:0", "42:0"]

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_send_shift_insert_failure(self, mock_run):
        """ydotool failure raises OutputError."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr=b"ydotool error message"
        )

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="ydotool failed"):
            strategy._send_shift_insert()

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_send_shift_insert_not_found(self, mock_run):
        """Missing ydotool raises OutputError."""
        mock_run.side_effect = FileNotFoundError()

        strategy = WlClipSimplePaste({})

        with pytest.raises(OutputError, match="ydotool not found"):
            strategy._send_shift_insert()

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_send_shift_insert_with_custom_socket(self, mock_run):
        """Custom socket sets YDOTOOL_SOCKET env var."""
        mock_run.return_value = MagicMock(returncode=0)

        strategy = WlClipSimplePaste({"ydotool_socket": "/tmp/custom"})

        strategy._send_shift_insert()

        # Verify env passed to subprocess
        call_kwargs = mock_run.call_args[1]
        assert "env" in call_kwargs
        assert "YDOTOOL_SOCKET" in call_kwargs["env"]
        assert call_kwargs["env"]["YDOTOOL_SOCKET"] == "/tmp/custom"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/output/test_wl_clip_integration.py::TestKeystrokeInjection -v`

Expected: FAIL with "AttributeError: '_send_shift_insert'"

**Step 3: Implement _send_shift_insert()**

Add to `src/talk_it_out/output/strategies/wl_clip.py` after `_verify_clipboard_ready()`:

```python
    def _send_shift_insert(self) -> None:
        """Send Shift+Insert keystroke via ydotool.

        Raises:
            OutputError: If ydotool fails
        """
        cmd = build_shift_insert_command()
        env = get_ydotool_env(self.ydotool_socket)

        log.info("sending_shift_insert")
        log.debug("running_ydotool", command=cmd, env=env)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                env={**os.environ, **env} if env else None,
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            raise OutputError(f"ydotool failed: {stderr}")
        except FileNotFoundError:
            raise OutputError("ydotool not found - run verify_dependencies() first")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/output/test_wl_clip_integration.py::TestKeystrokeInjection -v`

Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add src/talk_it_out/output/strategies/wl_clip.py tests/output/test_wl_clip_integration.py
git commit -m "feat: implement Shift+Insert keystroke injection

Add _send_shift_insert() using ydotool to send Shift+Insert.
Tests mock subprocess to verify command and error handling."
```

### Task 5: Complete paste_text() integration

**Files:**
- Modify: `src/talk_it_out/output/strategies/wl_clip.py`
- Test: `tests/output/test_wl_clip_integration.py`

**Step 1: Write failing integration test**

Add to `tests/output/test_wl_clip_integration.py`:

```python
@pytest.mark.skipif(not has_wl_clipboard(), reason="wl-clipboard not installed")
@pytest.mark.clipboard
class TestPasteTextFullFlow:
    """Full paste_text() with real clipboard, mocked ydotool."""

    @patch('talk_it_out.output.strategies.wl_clip.subprocess.run')
    def test_paste_text_success(self, mock_run):
        """Full paste workflow: copy → verify → delay → paste."""
        # Mock only ydotool calls (let wl-copy/wl-paste run real)
        def selective_mock(cmd, *args, **kwargs):
            if cmd[0] == "ydotool":
                return MagicMock(returncode=0)
            # Actually run wl-copy/wl-paste
            import subprocess as real_subprocess
            return real_subprocess.run(cmd, *args, **kwargs)

        mock_run.side_effect = selective_mock

        strategy = WlClipSimplePaste({"targets": ["clipboard"]})
        strategy.virtual_device_delay = 0.1  # Short delay for test
        text = "Full workflow test content"

        strategy.paste_text(text)

        # Verify clipboard has content (real wl-paste check)
        import subprocess as real_subprocess
        result = real_subprocess.run(
            ["wl-paste"],
            capture_output=True,
            text=True,
        )
        assert result.stdout == text

        # Verify ydotool was called
        ydotool_calls = [c for c in mock_run.call_args_list if c[0][0][0] == "ydotool"]
        assert len(ydotool_calls) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/output/test_wl_clip_integration.py::TestPasteTextFullFlow -v -m clipboard -n 0`

Expected: FAIL with "NotImplementedError: To be implemented"

**Step 3: Implement paste_text()**

Replace `paste_text()` stub in `src/talk_it_out/output/strategies/wl_clip.py`:

```python
    def paste_text(self, text: str) -> None:
        """Copy to clipboard, verify, then paste.

        Args:
            text: Transcribed text to paste

        Raises:
            OutputError: If any step fails
        """
        log.info("paste_operation_started", text_length=len(text))

        # Step 1: Copy to clipboard(s)
        self._copy_to_clipboard(text)

        # Step 2: Poll-verify clipboard ready
        self._verify_clipboard_ready(text)

        # Step 3: Delay for ydotool virtual device recognition
        log.debug("waiting_for_virtual_device", delay_ms=int(self.virtual_device_delay * 1000))
        time.sleep(self.virtual_device_delay)

        # Step 4: Send Shift+Insert
        self._send_shift_insert()

        log.info("paste_operation_completed")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/output/test_wl_clip_integration.py::TestPasteTextFullFlow -v -m clipboard -n 0`

Expected: PASS

**Step 5: Remove xfail markers from factory tests**

Edit `tests/output/test_factory.py` - remove the `@pytest.mark.xfail` decorators from the two WlClipSimplePaste tests.

Run: `uv run pytest tests/output/test_factory.py -v`

Expected: PASS (all 4 tests)

**Step 6: Commit**

```bash
git add src/talk_it_out/output/strategies/wl_clip.py tests/output/test_wl_clip_integration.py tests/output/test_factory.py
git commit -m "feat: complete paste_text() integration

Implement full paste workflow: copy → verify → delay → paste.
Remove xfail markers from factory tests - WlClipSimplePaste now complete."
```

### Task 6: Create pytest.ini with clipboard marker

**Files:**
- Create: `pytest.ini`

**Step 1: Create pytest.ini**

Create `pytest.ini` in project root:

```ini
[pytest]
markers =
    clipboard: tests that use real wl-clipboard (run single-threaded with -n 0)
```

**Step 2: Verify marker works**

Run: `uv run pytest -m clipboard --collect-only`

Expected: Shows only clipboard-marked tests collected

**Step 3: Commit**

```bash
git add pytest.ini
git commit -m "test: add pytest.ini with clipboard marker

Configure clipboard marker for tests using real wl-clipboard.
These tests must run single-threaded to avoid race conditions."
```

---

## Phase 4: Main Application Integration

### Task 1: Integrate output strategy into main.py

**Files:**
- Modify: `src/talk_it_out/main.py`
- Test: Manual testing (no new automated tests - covered by Phase 3)

**Step 1: Add imports**

Add to `src/talk_it_out/main.py` imports section (after line 12, with other framework imports):

```python
from talk_it_out.output import create_output_strategy, OutputError
```

**Step 2: Create output strategy on startup**

In `run()` function, add after transcriber initialization (after line 81):

```python
    # Create and verify output strategy
    try:
        output_strategy = create_output_strategy(cfg)
        output_strategy.verify_dependencies()
        log.info("output_strategy_initialized", strategy=cfg["output"]["strategy"])
    except OutputError as e:
        log.error("output_strategy_init_failed", error=str(e))
        raise typer.Exit(code=1)
```

**Step 3: Replace TODO with paste_text() call**

Find line 137 (the TODO comment) and replace it with:

```python
            # Paste transcribed text
            try:
                output_strategy.paste_text(text)
                log.info("text_pasted_successfully")
            except OutputError as e:
                log.error("paste_failed", error=str(e))
                # Don't crash - log error and continue listening
```

**Step 4: Test manually - dependencies missing**

Run: `uv run python -m talk_it_out.main run --log-level DEBUG`

If wl-clipboard or ydotool not installed, expected:
- Error message with install instructions
- Exit code 1

**Step 5: Test manually - full workflow (if dependencies available)**

Prerequisites: wl-clipboard and ydotool installed, ydotoold running

Run: `uv run python -m talk_it_out.main run --log-level INFO`

Test:
1. Press Meta+Alt
2. Speak into microphone
3. Release Meta+Alt
4. Verify transcribed text appears in active application

Expected logs:
```
output_strategy_initialized strategy=wl-clip-simplepaste
...
paste_operation_started text_length=XX
clipboard_verified elapsed_ms=XXX
sending_shift_insert
paste_operation_completed
text_pasted_successfully
```

**Step 6: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: integrate output strategy into main app

Create output strategy on startup and verify dependencies.
Call paste_text() after transcription completes.
Log errors but continue running if paste fails."
```

---

## Phase 5: Documentation Updates

### Task 1: Update README.md prerequisites

**Files:**
- Modify: `README.md:50-88` (Prerequisites and Installation sections)

**Step 1: Add wl-clipboard and ydotool to prerequisites**

Modify `README.md` - find the "System packages:" section (around line 54) and add before the ffmpeg section:

```markdown
**Output dependencies (wl-clip-simplepaste strategy):**

```bash
# Fedora/RHEL
sudo dnf install wl-clipboard ydotool
sudo systemctl enable --now ydotoold

# Debian/Ubuntu
sudo apt install wl-clipboard ydotool
sudo systemctl enable --now ydotoold

# Arch
sudo pacman -S wl-clipboard
yay -S ydotool-git  # AUR
sudo systemctl enable --now ydotoold
```

Required for clipboard operations and keystroke injection on Wayland.

**Note:** ydotoold daemon must be running. Verify with `systemctl status ydotoold`.

```

**Step 2: Verify formatting**

Run: `cat README.md | grep -A 10 "Output dependencies"`

Expected: Shows the new section with proper formatting

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add wl-clipboard and ydotool prerequisites

Document installation of wl-clipboard and ydotool for output strategy.
Include ydotoold daemon setup instructions for all major distros."
```

### Task 2: Update README.md configuration section

**Files:**
- Modify: `README.md:152-182` (Configuration section)

**Step 1: Update config example and explanation**

Find the configuration example in README.md (around line 156) and update it:

Replace the `[paste]` section with:

```toml
[output]
strategy = "wl-clip-simplepaste"

# Optional: Advanced wl-clip settings (defaults shown)
# [output.wl-clip]
# targets = ["clipboard", "primary"]  # Which clipboards to populate
# ydotool_socket = ""  # Custom socket path (empty = use $YDOTOOL_SOCKET or default)
```

**Step 2: Add config override explanation**

Add after the configuration example (around line 182):

```markdown

### Configuration Overrides

The config file uses a **two-layer system**: your config file contains only overrides, and internal defaults fill in the rest.

**Minimal config (recommended):**
```toml
[keys.combos]
record_for_paste = [["KEY_LEFTMETA", "KEY_LEFTALT"]]

[whisper]
model = "turbo"
language = "en"

[output]
strategy = "wl-clip-simplepaste"
```

**What you can override:**
- `[whisper]`: Only specify `model` and `language` if you want different defaults
- `[output.wl-clip]`: Only needed if you want to customize clipboard targets
- `[audio]`, `[logging]`: Omit entirely to use defaults

Advanced settings (beam_size, vad_filter, compute_type) have working defaults via internal config merge.
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update configuration section for override system

Explain two-layer config system (user overrides + internal defaults).
Replace [paste] with [output] section. Show minimal recommended config."
```

### Task 3: Update README.md troubleshooting section

**Files:**
- Modify: `README.md:219-235` (Troubleshooting section)

**Step 1: Add paste troubleshooting**

Add new subsection to troubleshooting (after existing keyboard troubleshooting):

```markdown

**Paste not working:**
- Verify dependencies installed: `which wl-copy wl-paste ydotool`
- Check ydotoold daemon: `systemctl status ydotoold` (should be active)
- Test clipboard manually:
  ```bash
  echo "test" | wl-copy
  wl-paste  # Should output "test"
  ```
- Test ydotool manually: `ydotool key 28:1 28:0` (should send Enter key)
- Check logs with `--log-level DEBUG` for detailed paste operation info
- Some applications expect different paste shortcuts - Shift+Insert is most compatible

**Clipboard targets:**
- If paste doesn't work in your application, try different targets in config:
  ```toml
  [output.wl-clip]
  targets = ["clipboard"]  # or ["primary"] or both
  ```
- GNOME Terminal and some terminals prefer `primary` selection

**ydotool socket issues:**
- Check socket exists: `ls -l /run/ydotool/socket` (or value of $YDOTOOL_SOCKET)
- Verify permissions: Socket must be readable/writable by your user
- Custom socket in config:
  ```toml
  [output.wl-clip]
  ydotool_socket = "/path/to/custom/socket"
  ```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add paste troubleshooting section

Add troubleshooting steps for paste failures, dependency issues,
ydotoold daemon, and clipboard target configuration."
```

### Task 4: Add note about single-threaded clipboard tests

**Files:**
- Modify: `README.md` (Development section, around line 247-257)

**Step 1: Update test running instructions**

Find the "Run Tests" section in README.md and update:

```markdown
### Run Tests

```bash
# Unit tests
pytest tests/framework/ -v

# Integration tests (CLI framework)
./tests/integration/test_cli_framework.sh

# Output tests (clipboard tests run single-threaded)
pytest tests/output/ -v

# Clipboard tests only (must run single-threaded to avoid race conditions)
pytest -m clipboard -n 0 -v
```

**Note:** Clipboard tests use real wl-clipboard and must run single-threaded (`-n 0`) to avoid race conditions on global clipboard state.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document single-threaded clipboard test requirement

Add note about running clipboard tests with -n 0 to avoid race
conditions. Update test running examples."
```

### Task 5: Create manual testing checklist for output

**Files:**
- Create: `tests/manual/OUTPUT_TESTING.md`

**Step 1: Create comprehensive manual test checklist**

Create `tests/manual/OUTPUT_TESTING.md`:

```markdown
# Manual Testing Checklist - Output Strategy

## Prerequisites

- [ ] wl-clipboard installed (`which wl-copy wl-paste`)
- [ ] ydotool installed (`which ydotool`)
- [ ] ydotoold daemon running (`systemctl status ydotoold`)
- [ ] Wayland session (check `echo $XDG_SESSION_TYPE`)

## Basic Paste Workflow

- [ ] **Terminal application paste**
  - Open terminal (GNOME Terminal, Konsole, etc.)
  - Run `talk-it-out run`
  - Press Meta+Alt, speak "hello world", release
  - Verify "hello world" appears in terminal
  - Note: Should use Shift+Insert, not Ctrl+V

- [ ] **Browser textarea paste**
  - Open browser, navigate to text input field
  - Run `talk-it-out run`
  - Press Meta+Alt, speak "test input", release
  - Verify "test input" appears in textarea

- [ ] **Text editor paste**
  - Open text editor (Kate, gedit, VS Code, etc.)
  - Run `talk-it-out run`
  - Press Meta+Alt, speak "editor test", release
  - Verify text appears at cursor position

## Error Handling

- [ ] **Missing wl-copy**
  - Temporarily rename wl-copy: `sudo mv /usr/bin/wl-copy /usr/bin/wl-copy.bak`
  - Run `talk-it-out run`
  - Verify error message shows install instructions
  - Restore: `sudo mv /usr/bin/wl-copy.bak /usr/bin/wl-copy`

- [ ] **Missing ydotool**
  - Temporarily rename ydotool: `sudo mv /usr/bin/ydotool /usr/bin/ydotool.bak`
  - Run `talk-it-out run`
  - Verify error message shows install instructions
  - Restore: `sudo mv /usr/bin/ydotool.bak /usr/bin/ydotool`

- [ ] **ydotoold not running**
  - Stop daemon: `sudo systemctl stop ydotoold`
  - Run `talk-it-out run`
  - Verify error message mentions starting ydotoold
  - Start daemon: `sudo systemctl start ydotoold`

## Configuration Options

- [ ] **Custom ydotool socket**
  - Find ydotool socket: `ls -l /run/ydotool/`
  - Edit config, add:
    ```toml
    [output.wl-clip]
    ydotool_socket = "/run/ydotool/socket"  # Explicit path
    ```
  - Run test, verify paste works
  - Check logs show socket path verification

- [ ] **Socket permission errors**
  - Create unreadable socket test (requires root):
    ```bash
    sudo touch /tmp/test-socket
    sudo chmod 000 /tmp/test-socket
    ```
  - Edit config to use `/tmp/test-socket`
  - Run `talk-it-out run`
  - Verify error message mentions permissions and suggests fix
  - Cleanup: `sudo rm /tmp/test-socket`

- [ ] **Override clipboard target to clipboard only**
  - Edit config: `talk-it-out config-edit`
  - Add:
    ```toml
    [output.wl-clip]
    targets = ["clipboard"]
    ```
  - Run test, verify paste works
  - Check primary selection NOT set: `wl-paste --primary` (should differ)

- [ ] **Override clipboard target to primary only**
  - Edit config, change to:
    ```toml
    [output.wl-clip]
    targets = ["primary"]
    ```
  - Run test in terminal (terminals often use primary)
  - Verify paste works

- [ ] **Both targets (default)**
  - Remove `[output.wl-clip]` section from config
  - Run test
  - Verify both clipboards set:
    ```bash
    wl-paste          # Should show transcription
    wl-paste --primary  # Should also show transcription
    ```

## Stress Testing

- [ ] **Rapid consecutive pastes**
  - Run `talk-it-out run`
  - Trigger recording 3-4 times quickly (short utterances)
  - Verify all transcriptions paste correctly
  - Check logs for errors

- [ ] **Long transcription**
  - Record a long utterance (30+ seconds)
  - Verify entire transcription pastes correctly
  - Check no truncation or corruption

- [ ] **Special characters**
  - Speak text with punctuation: "Hello, world! How are you?"
  - Verify punctuation appears correctly in paste

## Debug Logging

- [ ] **Verify detailed logs**
  - Run with debug: `talk-it-out run --log-level DEBUG`
  - Trigger recording
  - Verify logs show:
    - `output_strategy_initialized`
    - `paste_operation_started`
    - `running_wl_copy`
    - `verifying_clipboard`
    - `clipboard_verified`
    - `waiting_for_virtual_device`
    - `sending_shift_insert`
    - `paste_operation_completed`

## Cleanup

- [ ] Return config to defaults (remove `[output.wl-clip]` overrides)
- [ ] Verify ydotoold still running: `systemctl status ydotoold`
```

**Step 2: Commit**

```bash
git add tests/manual/OUTPUT_TESTING.md
git commit -m "docs: add manual testing checklist for output strategy

Comprehensive manual test procedures for paste workflow, error
handling, config options, stress testing, and debug logging."
```

---

## Phase 6: Config Migration

### Task 1: Verify backward compatibility

**Files:**
- Test: Manual testing with old and new config formats

**Step 1: Test old-style full config still works**

Create full config:
```bash
cat > /tmp/test-full-config.toml << 'EOF'
[keys.combos]
record_for_paste = [["KEY_LEFTMETA", "KEY_LEFTALT"]]

[audio]
sample_rate = 16000
channels = 1
device = ""

[whisper]
model = "turbo"
language = "en"
device = "auto"
compute_type = "auto"
beam_size = 5
vad_filter = true
save_debug_audio = false

[output]
strategy = "wl-clip-simplepaste"

[logging]
level = "INFO"
EOF
```

Run: `uv run python -m talk_it_out.main run --config /tmp/test-full-config.toml --log-level INFO`

Expected: App starts successfully, config validation passes

**Step 2: Test new-style minimal config works**

Create minimal config:
```bash
cat > /tmp/test-minimal-config.toml << 'EOF'
[keys.combos]
record_for_paste = [["KEY_LEFTMETA", "KEY_LEFTALT"]]

[whisper]
model = "turbo"
language = "en"

[output]
strategy = "wl-clip-simplepaste"
EOF
```

Run: `uv run python -m talk_it_out.main run --config /tmp/test-minimal-config.toml --log-level INFO`

Expected: App starts successfully, all defaults filled in via merge

**Step 3: Test config with partial overrides**

Create partial config:
```bash
cat > /tmp/test-partial-config.toml << 'EOF'
[keys.combos]
record_for_paste = [["KEY_A"]]

[whisper]
model = "base"

[logging]
level = "DEBUG"
EOF
```

Run: `uv run python -c "from talk_it_out.framework.config_io import load_config; cfg = load_config('/tmp/test-partial-config.toml'); print('beam_size:', cfg['whisper']['beam_size'], 'output:', cfg['output']['strategy'])"`

Expected: Output shows `beam_size: 5 output: wl-clip-simplepaste` (from defaults)

**Step 4: Document compatibility**

All three config styles work:
- Full config (all sections, all values)
- Minimal config (only essentials)
- Partial config (some sections, some overrides)

No breaking changes to existing user configs.

**Step 5: Commit verification results**

```bash
git commit --allow-empty -m "test: verify backward compatibility with config formats

Verified all config formats work:
- Full configs (all defaults specified) - work unchanged
- Minimal configs (only overrides) - work with merge
- Partial configs (some overrides) - work with merge
No breaking changes to existing user configs."
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2025-10-26-config-simplification-and-output-strategy.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
