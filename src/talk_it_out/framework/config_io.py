# pattern: Imperative Shell
# I/O operations for configuration management

from pathlib import Path
import tomllib

import tomli_w

from .config import default_config, validate_config, merge_configs


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
    save_config(path, minimal_config)


def load_config(path: Path | str) -> dict:
    """Load and validate configuration from TOML file.

    Args:
        path: Path to config file

    Returns:
        Complete, validated config dict

    Raises:
        ValueError: If merged config is invalid

    Notes:
        - Merges user config over internal defaults
        - Creates default config file if missing
        - Validates merged config before returning
    """
    path = Path(path)

    # Create default if doesn't exist
    if not path.exists():
        default = default_config()
        save_config(path, default)
        return default

    # Load user config
    with open(path, "rb") as f:
        user_config = tomllib.load(f)

    # Merge user overrides over defaults
    defaults = default_config()
    merged = merge_configs(defaults, user_config)

    # Validate merged config
    errors = validate_config(merged)
    if errors:
        raise ValueError(f"Invalid configuration: {'; '.join(errors)}")

    return merged
