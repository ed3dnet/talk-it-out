# pattern: Imperative Shell
# I/O operations for configuration management

from pathlib import Path
import tomllib

import tomli_w

from .config import default_config, validate_config


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
