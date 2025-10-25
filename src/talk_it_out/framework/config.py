# pattern: Functional Core
# Pure functions for configuration management

from pathlib import Path

from evdev import ecodes


def get_config_path() -> Path:
    """Get path to configuration file.

    Returns:
        Path to ~/.config/talk-it-out/config.toml
    """
    return Path.home() / ".config" / "talk-it-out" / "config.toml"


def default_config() -> dict:
    """Get default configuration.

    Returns:
        Dictionary with default configuration values
    """
    return {
        "keys": {
            "combos": {
                "record_for_paste": [
                    ["KEY_LEFTMETA", "KEY_LEFTALT"],
                ],
            }
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

    # Validate keys.combos structure
    if "combos" not in cfg["keys"]:
        errors.append("Config missing keys.combos dict")
    elif not isinstance(cfg["keys"]["combos"], dict):
        errors.append("Config keys.combos must be a dict")
    elif len(cfg["keys"]["combos"]) == 0:
        errors.append("Config keys.combos cannot be empty")
    else:
        # Validate each combo definition (now array of arrays)
        for combo_name, combo_list in cfg["keys"]["combos"].items():
            if not isinstance(combo_list, list):
                errors.append(f"Config keys.combos.{combo_name} must be a list")
                continue
            if len(combo_list) == 0:
                errors.append(f"Config keys.combos.{combo_name} cannot be empty")
                continue

            # Each combo is an array of valid key combinations
            for i, key_list in enumerate(combo_list):
                if not isinstance(key_list, list):
                    errors.append(
                        f"Config keys.combos.{combo_name}[{i}] must be a list, got {type(key_list).__name__}"
                    )
                    continue
                if len(key_list) == 0:
                    errors.append(
                        f"Config keys.combos.{combo_name}[{i}] cannot be empty"
                    )
                    continue

                # Validate each key name exists in evdev.ecodes (case-insensitive)
                for key_name in key_list:
                    if not isinstance(key_name, str):
                        errors.append(
                            f"Key name in combo '{combo_name}' must be a string, got {type(key_name).__name__}"
                        )
                        continue

                    # Check if key exists in ecodes module (case-insensitive)
                    key_upper = key_name.upper()
                    if not hasattr(ecodes, key_upper):
                        errors.append(
                            f"Invalid key name '{key_name}' in combo '{combo_name}'. "
                            f"Check evdev.ecodes for valid KEY_* names"
                        )

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
