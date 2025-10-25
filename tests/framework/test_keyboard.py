# pattern: Functional Core tests
# Tests for pure keyboard event processing logic

import pytest
from talk_it_out.framework.keyboard import (
    KeyboardState,
    KeyEvent,
    ComboEvent,
    process_key_event,
)
from talk_it_out.framework import config


def test_process_key_event_press_adds_to_held_keys():
    """Pressing a key should add it to held_keys set."""
    state = KeyboardState()
    event = KeyEvent(device_path="/dev/input/event0", key_code=125, is_press=True)
    target_combos = {}

    new_state, events = process_key_event(state, event, target_combos)

    assert 125 in new_state.held_keys
    assert len(events) == 0  # No combo triggered


def test_process_key_event_release_removes_from_held_keys():
    """Releasing a key should remove it from held_keys set."""
    state = KeyboardState(held_keys=frozenset([125]))
    event = KeyEvent(device_path="/dev/input/event0", key_code=125, is_press=False)
    target_combos = {}

    new_state, events = process_key_event(state, event, target_combos)

    assert 125 not in new_state.held_keys
    assert len(events) == 0


def test_process_key_event_combo_activated():
    """When all combo keys are pressed, should emit combo_pressed event."""
    state = KeyboardState(held_keys=frozenset([125]))  # Super already held
    event = KeyEvent(device_path="/dev/input/event0", key_code=56, is_press=True)  # Press Alt
    # New format: list of valid key combinations (frozensets)
    target_combos = {"record_for_paste": [frozenset([125, 56])]}  # Super+Alt

    new_state, events = process_key_event(state, event, target_combos)

    assert new_state.held_keys == frozenset([125, 56])
    assert "record_for_paste" in new_state.active_combos
    assert len(events) == 1
    assert events[0].event_type == "combo_pressed"
    assert events[0].combo_type == "record_for_paste"
    assert events[0].device_path == "/dev/input/event0"


def test_process_key_event_combo_released():
    """When any combo key is released, should emit combo_released event."""
    state = KeyboardState(
        held_keys=frozenset([125, 56]),
        active_combos=frozenset(["record_for_paste"])
    )
    event = KeyEvent(device_path="/dev/input/event0", key_code=56, is_press=False)  # Release Alt
    target_combos = {"record_for_paste": [frozenset([125, 56])]}

    new_state, events = process_key_event(state, event, target_combos)

    assert new_state.held_keys == frozenset([125])
    assert "record_for_paste" not in new_state.active_combos
    assert len(events) == 1
    assert events[0].event_type == "combo_released"
    assert events[0].combo_type == "record_for_paste"


def test_process_key_event_multiple_combos():
    """Should track multiple different combos independently."""
    state = KeyboardState(held_keys=frozenset([29]))  # Ctrl held
    event = KeyEvent(device_path="/dev/input/event0", key_code=49, is_press=True)  # Press N
    target_combos = {
        "record_for_paste": [frozenset([125, 56])],  # Super+Alt
        "quick_note": [frozenset([29, 49])]  # Ctrl+N
    }

    new_state, events = process_key_event(state, event, target_combos)

    assert "quick_note" in new_state.active_combos
    assert "record_for_paste" not in new_state.active_combos
    assert len(events) == 1
    assert events[0].combo_type == "quick_note"


def test_config_to_target_combos_converts_key_names_to_codes():
    """Should convert config key names to evdev key codes."""
    from talk_it_out.framework.keyboard import config_to_target_combos

    cfg = config.default_config()
    # cfg has: "keys": {"combos": {"record_for_paste": [["KEY_LEFTMETA", "KEY_LEFTALT"]]}}

    target_combos = config_to_target_combos(cfg)

    assert "record_for_paste" in target_combos
    # Should return list of frozensets, one per valid key combination
    assert isinstance(target_combos["record_for_paste"], list)
    assert len(target_combos["record_for_paste"]) == 1

    # First combination should be frozenset([125, 56]) - left meta and left alt
    combo_keys = target_combos["record_for_paste"][0]
    assert isinstance(combo_keys, frozenset)
    assert 125 in combo_keys  # KEY_LEFTMETA
    assert 56 in combo_keys   # KEY_LEFTALT


def test_config_to_target_combos_expands_modifier_variants():
    """Should handle multiple valid key combinations for a combo."""
    from talk_it_out.framework.keyboard import config_to_target_combos

    cfg = {
        "keys": {
            "combos": {
                "test": [
                    ["KEY_LEFTCTRL"],  # First valid combo
                    ["KEY_RIGHTCTRL"]  # Second valid combo
                ]
            }
        }
    }

    target_combos = config_to_target_combos(cfg)

    # Should have two valid combinations
    assert len(target_combos["test"]) == 2
    # First combination has KEY_LEFTCTRL
    assert 29 in target_combos["test"][0]
    # Second combination has KEY_RIGHTCTRL
    assert 97 in target_combos["test"][1]


def test_process_key_event_ignore_unrelated_keys():
    """Keys not in any combo should update state but emit no events."""
    state = KeyboardState()
    event = KeyEvent(device_path="/dev/input/event0", key_code=30, is_press=True)  # 'A' key
    target_combos = {"record": [frozenset([125, 56])]}

    new_state, events = process_key_event(state, event, target_combos)

    assert 30 in new_state.held_keys
    assert len(events) == 0


def test_process_key_event_press_order_independence():
    """Combo should activate regardless of key press order."""
    target_combos = {"test": [frozenset([125, 56])]}

    # Order 1: Super then Alt
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 125, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 56, True), target_combos)
    assert len(events) == 1 and events[0].event_type == "combo_pressed"

    # Order 2: Alt then Super
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 56, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 125, True), target_combos)
    assert len(events) == 1 and events[0].event_type == "combo_pressed"


def test_process_key_event_double_press_same_key():
    """Pressing already-held key should be idempotent."""
    state = KeyboardState(held_keys=frozenset([125]))
    event = KeyEvent(device_path="/dev/input/event0", key_code=125, is_press=True)
    target_combos = {}

    new_state, events = process_key_event(state, event, target_combos)

    assert new_state.held_keys == frozenset([125])
    assert len(events) == 0


def test_process_key_event_release_unheld_key():
    """Releasing key that wasn't held should be safe (no-op)."""
    state = KeyboardState()
    event = KeyEvent(device_path="/dev/input/event0", key_code=125, is_press=False)
    target_combos = {}

    new_state, events = process_key_event(state, event, target_combos)

    assert len(new_state.held_keys) == 0
    assert len(events) == 0


def test_process_key_event_multiple_valid_combinations():
    """Combo should trigger with any of the valid key combinations."""
    # Define combo with two valid combinations: either left or right meta+alt
    target_combos = {
        "record": [
            frozenset([125, 56]),  # Left meta + left alt
            frozenset([126, 100])  # Right meta + right alt
        ]
    }

    # Test first combination (left meta + left alt)
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 125, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 56, True), target_combos)
    assert len(events) == 1 and events[0].event_type == "combo_pressed"

    # Test second combination (right meta + right alt)
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 126, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 100, True), target_combos)
    assert len(events) == 1 and events[0].event_type == "combo_pressed"

    # Test mixed keys should NOT trigger (left meta + right alt)
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 125, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 100, True), target_combos)
    assert len(events) == 0  # No combo triggered


def test_integration_config_to_activation():
    """Integration test: config format -> conversion -> combo activation."""
    from talk_it_out.framework.keyboard import config_to_target_combos

    # Define config with multiple valid combinations for same combo
    cfg = {
        "keys": {
            "combos": {
                "record_for_paste": [
                    ["KEY_LEFTMETA", "KEY_LEFTALT"],   # Left-side combo
                    ["KEY_RIGHTMETA", "KEY_RIGHTALT"]  # Right-side combo
                ]
            }
        }
    }

    # Convert config to target combos
    target_combos = config_to_target_combos(cfg)

    # Verify conversion produced correct structure
    assert "record_for_paste" in target_combos
    assert len(target_combos["record_for_paste"]) == 2
    assert frozenset([125, 56]) in target_combos["record_for_paste"]
    assert frozenset([126, 100]) in target_combos["record_for_paste"]

    # Test left-side combo activates
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 125, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 56, True), target_combos)
    assert len(events) == 1
    assert events[0].event_type == "combo_pressed"
    assert events[0].combo_type == "record_for_paste"

    # Test right-side combo activates
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 126, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 100, True), target_combos)
    assert len(events) == 1
    assert events[0].event_type == "combo_pressed"
    assert events[0].combo_type == "record_for_paste"

    # Test mixed sides do NOT activate
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 125, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 100, True), target_combos)
    assert len(events) == 0


def test_integration_case_insensitivity():
    """Integration test: case-insensitive key names work end-to-end."""
    from talk_it_out.framework.keyboard import config_to_target_combos

    # Config with different case variations
    cfg = {
        "keys": {
            "combos": {
                "test": [
                    ["key_leftmeta", "key_leftalt"],  # lowercase
                ]
            }
        }
    }

    # Convert config
    target_combos = config_to_target_combos(cfg)

    # Verify keys were correctly converted
    assert len(target_combos["test"]) == 1
    assert frozenset([125, 56]) in target_combos["test"]

    # Verify combo activates
    state = KeyboardState()
    state, _ = process_key_event(state, KeyEvent("/dev/input/event0", 125, True), target_combos)
    state, events = process_key_event(state, KeyEvent("/dev/input/event0", 56, True), target_combos)
    assert len(events) == 1
    assert events[0].event_type == "combo_pressed"
