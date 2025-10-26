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
