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
            "model": "turbo",
            "language": "en",
            "device": "auto",
            "compute_type": "auto",
            "beam_size": 5,
            "vad_filter": True,
            "save_debug_audio": False,
        },
        "output": {
            "strategy": "wl-clip-simplepaste",
            "wl-clip": {
                "targets": ["clipboard", "primary"],
            },
        },
        "logging": {
            "level": "INFO",
        },
    }


VALID_WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "turbo"]
VALID_DEVICES = ["auto", "cuda", "cpu"]
VALID_COMPUTE_TYPES = [
    "auto", "int8", "int8_float32", "int8_float16",
    "int16", "float16", "float32"
]
# ISO 639-1 language codes supported by Whisper
VALID_LANGUAGES = [
    "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr", "pl", "ca", "nl",
    "ar", "sv", "it", "id", "hi", "fi", "vi", "he", "uk", "el", "ms", "cs", "ro",
    "da", "hu", "ta", "no", "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy",
    "sk", "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk", "br", "eu",
    "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw", "gl", "mr", "pa", "si", "km",
    "sn", "yo", "so", "af", "oc", "ka", "be", "tg", "sd", "gu", "am", "yi", "lo",
    "uz", "fo", "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl", "mg",
    "as", "tt", "haw", "ln", "ha", "ba", "jw", "su"
]
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]


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

    # Validate whisper.model (required)
    if "whisper" not in cfg or "model" not in cfg["whisper"]:
        errors.append("Missing whisper.model")
    elif cfg["whisper"]["model"] not in VALID_WHISPER_MODELS:
        errors.append(f"Invalid whisper.model: {cfg['whisper']['model']}. Must be one of: {VALID_WHISPER_MODELS}")

    # Validate whisper.language (required)
    if "whisper" not in cfg or "language" not in cfg["whisper"]:
        errors.append("Missing whisper.language")
    elif cfg["whisper"]["language"] not in VALID_LANGUAGES:
        errors.append(
            f"Invalid whisper.language: {cfg['whisper']['language']}. "
            f"Must be a valid ISO 639-1 language code."
        )

    # Validate whisper.device (required)
    if "whisper" not in cfg or "device" not in cfg["whisper"]:
        errors.append("Missing whisper.device")
    elif cfg["whisper"]["device"] not in VALID_DEVICES:
        errors.append(
            f"Invalid whisper.device: {cfg['whisper']['device']}. "
            f"Must be one of: {VALID_DEVICES}"
        )

    # Validate whisper.compute_type (required)
    if "whisper" not in cfg or "compute_type" not in cfg["whisper"]:
        errors.append("Missing whisper.compute_type")
    elif cfg["whisper"]["compute_type"] not in VALID_COMPUTE_TYPES:
        errors.append(
            f"Invalid whisper.compute_type: {cfg['whisper']['compute_type']}. "
            f"Must be one of: {VALID_COMPUTE_TYPES}"
        )

    # Validate whisper.beam_size (required)
    if "whisper" not in cfg or "beam_size" not in cfg["whisper"]:
        errors.append("Missing whisper.beam_size")
    else:
        beam_size = cfg["whisper"]["beam_size"]
        if not isinstance(beam_size, int) or beam_size < 1 or beam_size > 10:
            errors.append(
                f"Invalid whisper.beam_size: {beam_size}. "
                "Must be an integer between 1 and 10."
            )

    # Validate whisper.vad_filter (required, boolean)
    if "whisper" not in cfg or "vad_filter" not in cfg["whisper"]:
        errors.append("Missing whisper.vad_filter")
    elif not isinstance(cfg["whisper"]["vad_filter"], bool):
        errors.append(
            f"Invalid whisper.vad_filter: {cfg['whisper']['vad_filter']}. "
            "Must be a boolean (true or false)."
        )

    # Validate whisper.save_debug_audio (required, boolean)
    if "whisper" not in cfg or "save_debug_audio" not in cfg["whisper"]:
        errors.append("Missing whisper.save_debug_audio")
    elif not isinstance(cfg["whisper"]["save_debug_audio"], bool):
        errors.append(
            f"Invalid whisper.save_debug_audio: {cfg['whisper']['save_debug_audio']}. "
            "Must be a boolean (true or false)."
        )

    # Validate output section
    if "output" not in cfg:
        errors.append("Missing [output] section in config")
    else:
        output = cfg["output"]

        if "strategy" not in output:
            errors.append("Missing 'strategy' in [output] section")
        else:
            valid_strategies = {"wl-clip-simplepaste"}
            if output["strategy"] not in valid_strategies:
                errors.append(
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
                                errors.append(
                                    f"Invalid clipboard target: '{target}'. "
                                    f"Valid: {', '.join(valid_targets)}"
                                )

    # Validate logging.level
    if "logging" not in cfg or "level" not in cfg["logging"]:
        errors.append("Missing logging.level")
    elif cfg["logging"]["level"] not in VALID_LOG_LEVELS:
        errors.append(f"Invalid logging.level: {cfg['logging']['level']}. Must be one of: {VALID_LOG_LEVELS}")

    return errors
