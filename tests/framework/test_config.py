# pattern: Mixed (unavoidable)
# Tests for both pure configuration functions and I/O operations
# Mixed because tests need to verify both functional core and imperative shell

from pathlib import Path
from talk_it_out.framework import config
from talk_it_out.framework import config_io
from evdev import ecodes
import tempfile
import tomllib


def test_get_config_path_returns_xdg_config_location():
    """Config path should be ~/.config/talk-it-out/config.toml"""
    path = config.get_config_path()

    assert isinstance(path, Path)
    assert path.name == "config.toml"
    assert "talk-it-out" in str(path)
    assert ".config" in str(path)


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
    """Default config should have combos dict with record_for_paste combo."""
    cfg = config.default_config()

    assert "combos" in cfg["keys"]
    assert isinstance(cfg["keys"]["combos"], dict)
    assert "record_for_paste" in cfg["keys"]["combos"]
    # New format: array of arrays with explicit evdev key names
    assert cfg["keys"]["combos"]["record_for_paste"] == [["KEY_LEFTMETA", "KEY_LEFTALT"]]


def test_default_config_audio_section():
    """Audio section should have sensible defaults"""
    cfg = config.default_config()

    assert cfg["audio"]["sample_rate"] == 16000
    assert cfg["audio"]["channels"] == 1
    assert cfg["audio"]["device"] == ""


def test_default_config_whisper_section():
    """Test that default config includes whisper section with all required keys."""
    cfg = config.default_config()

    assert "whisper" in cfg
    assert cfg["whisper"]["model"] == "turbo"
    assert cfg["whisper"]["language"] == "en"
    assert cfg["whisper"]["device"] == "auto"
    assert cfg["whisper"]["compute_type"] == "auto"
    assert cfg["whisper"]["beam_size"] == 5
    assert cfg["whisper"]["vad_filter"] is True
    assert cfg["whisper"]["save_debug_audio"] is False


def test_default_config_logging_section():
    """Logging should default to INFO level"""
    cfg = config.default_config()

    assert cfg["logging"]["level"] == "INFO"


def test_validate_config_accepts_valid_config():
    """Valid configuration should pass validation"""
    cfg = config.default_config()
    errors = config.validate_config(cfg)

    assert errors == []


def test_validate_config_rejects_empty_key_combos():
    """Config validation should fail if combos dict is empty."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {}

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("combos" in err for err in errors)


def test_validate_config_rejects_invalid_key_names():
    """Invalid key names should fail validation"""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {"test": [["INVALID_KEY"]]}
    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("invalid" in err.lower() or "key" in err.lower() for err in errors)


def test_validate_config_rejects_invalid_combo_key_names():
    """Validation should reject invalid key names in combo definitions."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {"test_combo": [["INVALID_KEY"]]}

    errors = config.validate_config(cfg)

    assert any("INVALID_KEY" in err for err in errors)


def test_validate_config_accepts_valid_combos():
    """Validation should accept valid combos dict."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {
        "record_for_paste": [["KEY_LEFTMETA", "KEY_LEFTALT"], ["KEY_RIGHTMETA", "KEY_RIGHTALT"]],
        "quick_note": [["KEY_LEFTCTRL", "KEY_LEFTSHIFT"]]
    }

    errors = config.validate_config(cfg)

    # Should have no errors for keys section
    assert not any("keys" in err or "combo" in err for err in errors)


def test_validate_config_rejects_non_list_combo_value():
    """Combo values must be lists of lists, not strings or other types."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {"test": "KEY_LEFTMETA"}

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("list" in err.lower() for err in errors)


def test_validate_config_rejects_empty_inner_list():
    """Inner key lists cannot be empty."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {"test": [[]]}

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("empty" in err.lower() for err in errors)


def test_validate_config_accepts_case_insensitive_key_names():
    """Key names should be case-insensitive."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {
        "test1": [["key_leftmeta", "key_leftalt"]],  # lowercase
        "test2": [["Key_LeftMeta", "Key_LeftAlt"]],  # mixed case
        "test3": [["KEY_LEFTMETA", "KEY_LEFTALT"]],  # uppercase
    }

    errors = config.validate_config(cfg)

    # Should have no errors for keys section
    assert not any("keys" in err or "combo" in err for err in errors)


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


def test_save_config_creates_toml_file(tmp_path):
    """save_config should write TOML file"""
    config_path = tmp_path / "config.toml"
    cfg = config.default_config()

    config_io.save_config(config_path, cfg)

    assert config_path.exists()


def test_save_config_creates_parent_directory(tmp_path):
    """save_config should create parent dirs if needed"""
    config_path = tmp_path / "nested" / "dir" / "config.toml"
    cfg = config.default_config()

    config_io.save_config(config_path, cfg)

    assert config_path.exists()
    assert config_path.parent.exists()


def test_save_config_writes_valid_toml(tmp_path):
    """Saved config should be valid TOML"""
    config_path = tmp_path / "config.toml"
    cfg = config.default_config()

    config_io.save_config(config_path, cfg)

    # Read back and parse
    with open(config_path, "rb") as f:
        loaded = tomllib.load(f)

    assert loaded == cfg


def test_load_config_reads_existing_file(tmp_path):
    """load_config should read and parse existing TOML"""
    config_path = tmp_path / "config.toml"
    original = config.default_config()
    config_io.save_config(config_path, original)

    loaded = config_io.load_config(config_path)

    assert loaded == original


def test_load_config_creates_default_if_missing(tmp_path):
    """load_config should create default config if file doesn't exist"""
    config_path = tmp_path / "config.toml"

    loaded = config_io.load_config(config_path)

    assert loaded == config.default_config()
    assert config_path.exists()


def test_load_config_validates_loaded_config(tmp_path):
    """load_config should raise if loaded config is invalid"""
    config_path = tmp_path / "config.toml"
    invalid_cfg = config.default_config()
    invalid_cfg["whisper"]["model"] = "invalid"
    config_io.save_config(config_path, invalid_cfg)

    try:
        config_io.load_config(config_path)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "model" in str(e).lower()


def test_validate_config_rejects_invalid_whisper_device():
    """Test that validate_config rejects invalid whisper.device values."""
    cfg = config.default_config()
    cfg["whisper"]["device"] = "invalid"

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.device" in err for err in errors)


def test_validate_config_accepts_valid_whisper_devices():
    """Test that validate_config accepts all valid device values."""
    cfg = config.default_config()

    for device in ["auto", "cuda", "cpu"]:
        cfg["whisper"]["device"] = device
        errors = config.validate_config(cfg)
        assert len(errors) == 0, f"device={device} should be valid"


def test_validate_config_rejects_invalid_compute_type():
    """Test that validate_config rejects invalid whisper.compute_type values."""
    cfg = config.default_config()
    cfg["whisper"]["compute_type"] = "invalid"

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.compute_type" in err for err in errors)


def test_validate_config_accepts_valid_compute_types():
    """Test that validate_config accepts all valid compute_type values."""
    cfg = config.default_config()

    valid_types = ["auto", "int8", "int8_float32", "int8_float16",
                   "int16", "float16", "float32"]
    for compute_type in valid_types:
        cfg["whisper"]["compute_type"] = compute_type
        errors = config.validate_config(cfg)
        assert len(errors) == 0, f"compute_type={compute_type} should be valid"


def test_validate_config_rejects_invalid_beam_size():
    """Test that validate_config rejects beam_size outside 1-10 range."""
    cfg = config.default_config()

    # Test below range
    cfg["whisper"]["beam_size"] = 0
    errors = config.validate_config(cfg)
    assert len(errors) > 0
    assert any("whisper.beam_size" in err for err in errors)

    # Test above range
    cfg["whisper"]["beam_size"] = 11
    errors = config.validate_config(cfg)
    assert len(errors) > 0
    assert any("whisper.beam_size" in err for err in errors)


def test_validate_config_accepts_valid_beam_sizes():
    """Test that validate_config accepts beam_size in 1-10 range."""
    cfg = config.default_config()

    for beam_size in [1, 5, 10]:
        cfg["whisper"]["beam_size"] = beam_size
        errors = config.validate_config(cfg)
        assert len(errors) == 0, f"beam_size={beam_size} should be valid"


def test_validate_config_rejects_non_boolean_vad_filter():
    """Test that validate_config rejects non-boolean vad_filter."""
    cfg = config.default_config()
    cfg["whisper"]["vad_filter"] = "true"  # String instead of bool

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.vad_filter" in err for err in errors)


def test_validate_config_rejects_non_boolean_save_debug_audio():
    """Test that validate_config rejects non-boolean save_debug_audio."""
    cfg = config.default_config()
    cfg["whisper"]["save_debug_audio"] = 1  # Int instead of bool

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.save_debug_audio" in err for err in errors)


def test_validate_config_accepts_boolean_whisper_flags():
    """Test that validate_config accepts boolean values for flags."""
    cfg = config.default_config()

    cfg["whisper"]["vad_filter"] = True
    cfg["whisper"]["save_debug_audio"] = False
    errors = config.validate_config(cfg)
    assert len(errors) == 0

    cfg["whisper"]["vad_filter"] = False
    cfg["whisper"]["save_debug_audio"] = True
    errors = config.validate_config(cfg)
    assert len(errors) == 0


def test_validate_config_rejects_missing_whisper_device():
    """Test that validate_config rejects missing whisper.device field."""
    cfg = config.default_config()
    del cfg["whisper"]["device"]

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.device" in err for err in errors)


def test_validate_config_rejects_missing_whisper_compute_type():
    """Test that validate_config rejects missing whisper.compute_type field."""
    cfg = config.default_config()
    del cfg["whisper"]["compute_type"]

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.compute_type" in err for err in errors)


def test_validate_config_rejects_missing_whisper_beam_size():
    """Test that validate_config rejects missing whisper.beam_size field."""
    cfg = config.default_config()
    del cfg["whisper"]["beam_size"]

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.beam_size" in err for err in errors)


def test_validate_config_rejects_missing_whisper_vad_filter():
    """Test that validate_config rejects missing whisper.vad_filter field."""
    cfg = config.default_config()
    del cfg["whisper"]["vad_filter"]

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.vad_filter" in err for err in errors)


def test_validate_config_rejects_missing_whisper_save_debug_audio():
    """Test that validate_config rejects missing whisper.save_debug_audio field."""
    cfg = config.default_config()
    del cfg["whisper"]["save_debug_audio"]

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.save_debug_audio" in err for err in errors)


def test_validate_config_rejects_missing_whisper_language():
    """Test that validate_config rejects missing whisper.language field."""
    cfg = config.default_config()
    del cfg["whisper"]["language"]

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.language" in err for err in errors)


def test_validate_config_rejects_invalid_whisper_language():
    """Test that validate_config rejects invalid whisper.language values."""
    cfg = config.default_config()
    cfg["whisper"]["language"] = "invalid_lang_code"

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("whisper.language" in err for err in errors)


def test_validate_config_accepts_valid_whisper_languages():
    """Test that validate_config accepts valid ISO 639-1 language codes."""
    cfg = config.default_config()

    # Test a few common language codes
    for lang in ["en", "es", "fr", "de", "zh", "ja", "ru"]:
        cfg["whisper"]["language"] = lang
        errors = config.validate_config(cfg)
        assert len(errors) == 0, f"language={lang} should be valid"
