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

    # Should be WlClipSimplePaste instance
    assert strategy is not None


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
