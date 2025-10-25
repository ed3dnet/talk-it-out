# Keyboard Monitoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement keyboard event monitoring with key combination detection for voice-to-text recording trigger

**Architecture:** Event-sourced state machine with FCIS separation - pure keyboard logic in Functional Core, device I/O in Imperative Shell, queue-based event emission

**Tech Stack:** Python 3.14+, evdev 1.6.0+, structlog, threading, select()

**Scope:** 8 phases from keyboard monitoring design (Phase 7 skipped - no migration needed as nothing deployed yet)

**Codebase verified:** 2025-10-25

---

## Phase 1: Configuration Updates

### Task 1: Update Config Validation Tests

**Files:**
- Modify: `tests/framework/test_config.py:39-40` (test_default_config_keys_section)
- Modify: `tests/framework/test_config.py:75-82` (test_validate_config_rejects_empty_key_combination)
- Modify: `tests/framework/test_config.py:88` (test_validate_config_rejects_invalid_key_names)

**Step 1: Write failing tests for combos dict structure**

Add to `tests/framework/test_config.py` after existing tests:

```python
def test_default_config_keys_combos_structure():
    """Default config should have combos dict with record_for_paste combo."""
    cfg = config.default_config()
    assert "combos" in cfg["keys"]
    assert isinstance(cfg["keys"]["combos"], dict)
    assert "record_for_paste" in cfg["keys"]["combos"]
    assert cfg["keys"]["combos"]["record_for_paste"] == ["super", "alt"]


def test_validate_config_rejects_empty_combos_dict():
    """Validation should reject empty combos dict."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {}

    errors = config.validate_config(cfg)

    assert any("combos" in err and "empty" in err for err in errors)


def test_validate_config_rejects_invalid_combo_key_names():
    """Validation should reject invalid key names in combo definitions."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {"test_combo": ["invalid_key"]}

    errors = config.validate_config(cfg)

    assert any("invalid_key" in err for err in errors)


def test_validate_config_accepts_valid_combos():
    """Validation should accept valid combos dict."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {
        "record_for_paste": ["super", "alt"],
        "quick_note": ["ctrl", "n"]
    }

    errors = config.validate_config(cfg)

    # Should have no errors for keys section
    assert not any("keys" in err or "combo" in err for err in errors)
```

**Step 2: Update existing tests to use combos dict**

```python
# tests/framework/test_config.py:39-40
def test_default_config_keys_section():
    """Default config should include keys section with combos."""
    cfg = config.default_config()
    assert cfg["keys"]["combos"]["record_for_paste"] == ["super", "alt"]


# tests/framework/test_config.py:75-82
def test_validate_config_rejects_empty_key_combos():
    """Config validation should fail if combos dict is empty."""
    cfg = config.default_config()
    cfg["keys"]["combos"] = {}

    errors = config.validate_config(cfg)

    assert len(errors) > 0
    assert any("combos" in err for err in errors)


# tests/framework/test_config.py:88 (part of test_validate_config_rejects_invalid_key_names)
# Update the line that sets combination to set combos instead:
cfg["keys"]["combos"] = {"test": ["invalid_key"]}
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/framework/test_config.py -v -k combos`

Expected: FAIL - tests fail because config.py still uses "combination"

**Step 4: Commit test changes**

```bash
git add tests/framework/test_config.py
git commit -m "test: update config tests for combos dict structure"
```

### Task 2: Update Config Default and Validation

**Files:**
- Modify: `src/talk_it_out/framework/config.py:25-27` (default_config)
- Modify: `src/talk_it_out/framework/config.py:69-77` (validate_config keys validation)

**Step 1: Update default_config() to use combos dict**

```python
# src/talk_it_out/framework/config.py:25-27
"keys": {
    "combos": {
        "record_for_paste": ["super", "alt"],
    }
},
```

**Step 2: Update validate_config() to validate combos dict**

Replace lines 69-77 with:

```python
# Validate keys.combos structure
if "combos" not in cfg["keys"]:
    errors.append("Config missing keys.combos dict")
elif not isinstance(cfg["keys"]["combos"], dict):
    errors.append("Config keys.combos must be a dict")
elif len(cfg["keys"]["combos"]) == 0:
    errors.append("Config keys.combos cannot be empty")
else:
    # Validate each combo definition
    for combo_name, key_list in cfg["keys"]["combos"].items():
        if not isinstance(key_list, list):
            errors.append(f"Config keys.combos.{combo_name} must be a list")
            continue
        if len(key_list) == 0:
            errors.append(f"Config keys.combos.{combo_name} cannot be empty")
            continue
        for key_name in key_list:
            if key_name not in VALID_KEYS:
                errors.append(
                    f"Invalid key name '{key_name}' in combo '{combo_name}'. "
                    f"Valid keys: {', '.join(VALID_KEYS.keys())}"
                )
```

**Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_config.py -v`

Expected: PASS - all config tests pass with new combos structure

**Step 4: Commit implementation**

```bash
git add src/talk_it_out/framework/config.py
git commit -m "feat: replace keys.combination with keys.combos dict

- Support multiple named combo definitions
- Validate combo names and key lists
- Default combo: record_for_paste with super+alt"
```

### Task 3: Update User Config File

**Files:**
- Modify: `~/.config/talk-it-out/config.toml:1-5`

**Step 1: Update config.toml to new format**

Edit `~/.config/talk-it-out/config.toml` to change:

```toml
[keys]
combination = [
    "super",
    "alt",
]
```

To:

```toml
[keys.combos]
record_for_paste = [
    "super",
    "alt",
]
```

**Step 2: Verify config loads without errors**

Run: `uv run python -c "from talk_it_out.framework import config, config_io; cfg = config_io.load_config(config.get_config_path()); print('Config loaded successfully')"`

Expected: "Config loaded successfully" with no errors

**Step 3: No commit needed** (user config file, not in repo)

### Task 4: Verify Phase 1 Complete

**Step 1: Run all config tests**

Run: `uv run pytest tests/framework/test_config.py -v`

Expected: All tests PASS

**Step 2: Verify validation works**

Run:
```bash
uv run python -c "
from talk_it_out.framework import config
cfg = config.default_config()
cfg['keys']['combos'] = {}
errors = config.validate_config(cfg)
print('Empty combos validation:', errors)

cfg['keys']['combos'] = {'test': ['invalid']}
errors = config.validate_config(cfg)
print('Invalid key validation:', errors)
"
```

Expected: Both validation cases should show appropriate errors

---

## Phase 2: Pure Keyboard Logic (Functional Core)

### Task 1: Create Keyboard State Dataclasses and Types

**Files:**
- Create: `src/talk_it_out/framework/keyboard.py`

**Step 1: Write file header and basic dataclasses**

```python
# pattern: Functional Core
# Pure keyboard event processing logic - no I/O operations

from dataclasses import dataclass
from typing import Dict, Tuple, List, Set, Literal, FrozenSet
from evdev import ecodes

# Type alias for combo identification
ComboType = str  # e.g., "record_for_paste", "quick_note"


@dataclass(frozen=True)
class KeyboardState:
    """Immutable state tracking which keys are currently held.

    Each device maintains its own KeyboardState instance to ensure
    press/release events are properly paired from the same device.
    """
    held_keys: frozenset[int] = frozenset()  # Currently pressed key codes
    active_combos: frozenset[ComboType] = frozenset()  # Which combos are active


@dataclass(frozen=True)
class KeyEvent:
    """A single key press or release event from an input device."""
    device_path: str  # e.g., "/dev/input/event3"
    key_code: int     # evdev key code (e.g., 125 for KEY_LEFTMETA)
    is_press: bool    # True for press, False for release


@dataclass(frozen=True)
class ComboEvent:
    """Output event when a combo is activated or released."""
    event_type: Literal['combo_pressed', 'combo_released']
    combo_type: ComboType  # e.g., "record_for_paste"
    device_path: str       # Which device triggered this combo
```

**Step 2: Create the file**

Write the code above to `src/talk_it_out/framework/keyboard.py`.

**Step 3: Verify file structure**

Run: `uv run python -c "from talk_it_out.framework.keyboard import KeyboardState, KeyEvent, ComboEvent; print('Imports successful')"`

Expected: "Imports successful"

**Step 4: Commit**

```bash
git add src/talk_it_out/framework/keyboard.py
git commit -m "feat: add keyboard state dataclasses

- KeyboardState tracks held keys and active combos
- KeyEvent represents press/release from device
- ComboEvent represents combo activation/release
- All immutable (frozen dataclasses)"
```

### Task 2: Implement Pure Reducer Function

**Files:**
- Modify: `src/talk_it_out/framework/keyboard.py`
- Create: `tests/framework/test_keyboard.py`

**Step 1: Write the test first**

Create `tests/framework/test_keyboard.py`:

```python
# pattern: Functional Core tests
# Tests for pure keyboard event processing logic

import pytest
from talk_it_out.framework.keyboard import (
    KeyboardState,
    KeyEvent,
    ComboEvent,
    process_key_event,
)


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
    target_combos = {"record_for_paste": frozenset([125, 56])}  # Super+Alt

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
    target_combos = {"record_for_paste": frozenset([125, 56])}

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
        "record_for_paste": frozenset([125, 56]),  # Super+Alt
        "quick_note": frozenset([29, 49])  # Ctrl+N
    }

    new_state, events = process_key_event(state, event, target_combos)

    assert "quick_note" in new_state.active_combos
    assert "record_for_paste" not in new_state.active_combos
    assert len(events) == 1
    assert events[0].combo_type == "quick_note"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_keyboard.py -v`

Expected: FAIL - `process_key_event` function doesn't exist yet

**Step 3: Implement minimal process_key_event function**

Add to `src/talk_it_out/framework/keyboard.py`:

```python
def process_key_event(
    state: KeyboardState,
    event: KeyEvent,
    target_combos: Dict[ComboType, frozenset[int]]
) -> Tuple[KeyboardState, List[ComboEvent]]:
    """Pure reducer: processes key event, returns (new_state, output_events).

    - On press: Add key to held_keys, check if any combo now complete
    - On release: Remove key from held_keys, check if any combo now broken
    - Returns combo_pressed/combo_released events as needed

    Args:
        state: Current keyboard state (immutable)
        event: Key press or release event
        target_combos: Map of combo names to required key sets

    Returns:
        (new_state, events): Updated state and list of combo events emitted
    """
    events: List[ComboEvent] = []

    # Update held keys based on press/release
    if event.is_press:
        new_held_keys = state.held_keys | {event.key_code}
    else:
        new_held_keys = state.held_keys - {event.key_code}

    # Check which combos are now active
    new_active_combos: Set[ComboType] = set()
    for combo_name, required_keys in target_combos.items():
        if required_keys.issubset(new_held_keys):
            new_active_combos.add(combo_name)

            # Emit combo_pressed if newly activated
            if combo_name not in state.active_combos:
                events.append(ComboEvent(
                    event_type="combo_pressed",
                    combo_type=combo_name,
                    device_path=event.device_path
                ))

    # Check for deactivated combos
    for combo_name in state.active_combos:
        if combo_name not in new_active_combos:
            events.append(ComboEvent(
                event_type="combo_released",
                combo_type=combo_name,
                device_path=event.device_path
            ))

    new_state = KeyboardState(
        held_keys=frozenset(new_held_keys),
        active_combos=frozenset(new_active_combos)
    )

    return new_state, events
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_keyboard.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/keyboard.py tests/framework/test_keyboard.py
git commit -m "feat: implement process_key_event reducer

- Pure function processes key events
- Tracks held keys and active combos
- Emits combo_pressed/released events
- Handles multiple combos independently"
```

### Task 3: Implement Config-to-Combos Converter

**Files:**
- Modify: `src/talk_it_out/framework/keyboard.py`
- Modify: `tests/framework/test_keyboard.py`

**Step 1: Write test for config_to_target_combos**

Add to `tests/framework/test_keyboard.py`:

```python
from talk_it_out.framework import config


def test_config_to_target_combos_converts_key_names_to_codes():
    """Should convert config key names to evdev key codes."""
    from talk_it_out.framework.keyboard import config_to_target_combos

    cfg = config.default_config()
    # cfg has: "keys": {"combos": {"record_for_paste": ["super", "alt"]}}

    target_combos = config_to_target_combos(cfg)

    assert "record_for_paste" in target_combos
    # super = KEY_LEFTMETA(125) or KEY_RIGHTMETA(126)
    # alt = KEY_LEFTALT(56) or KEY_RIGHTALT(100)
    # Should include all variants
    combo_keys = target_combos["record_for_paste"]
    assert 125 in combo_keys or 126 in combo_keys  # One of the super keys
    assert 56 in combo_keys or 100 in combo_keys   # One of the alt keys


def test_config_to_target_combos_expands_modifier_variants():
    """Should expand modifier keys to include left/right variants."""
    from talk_it_out.framework.keyboard import config_to_target_combos

    cfg = {
        "keys": {
            "combos": {
                "test": ["ctrl"]
            }
        }
    }

    target_combos = config_to_target_combos(cfg)

    # ctrl maps to (KEY_LEFTCTRL=29, KEY_RIGHTCTRL=97)
    # Should include at least one of them
    assert 29 in target_combos["test"] or 97 in target_combos["test"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/framework/test_keyboard.py::test_config_to_target_combos -v`

Expected: FAIL - function doesn't exist

**Step 3: Implement config_to_target_combos**

Add to `src/talk_it_out/framework/keyboard.py`:

```python
from talk_it_out.framework.config import VALID_KEYS


def config_to_target_combos(cfg: dict) -> Dict[ComboType, frozenset[int]]:
    """Convert config combo definitions to evdev key code sets.

    Expands modifier key names to their left/right variants.
    For example, "super" becomes both KEY_LEFTMETA and KEY_RIGHTMETA.

    Args:
        cfg: Configuration dict with keys.combos section

    Returns:
        Dict mapping combo names to sets of required key codes

    Example:
        Input: {"keys": {"combos": {"record": ["super", "alt"]}}}
        Output: {"record": frozenset([125, 126, 56, 100])}
        (Includes both left/right variants of super and alt)
    """
    target_combos: Dict[ComboType, frozenset[int]] = {}

    for combo_name, key_names in cfg["keys"]["combos"].items():
        key_codes: Set[int] = set()

        for key_name in key_names:
            # VALID_KEYS maps "super" -> (KEY_LEFTMETA, KEY_RIGHTMETA)
            codes = VALID_KEYS[key_name]
            key_codes.update(codes)

        target_combos[combo_name] = frozenset(key_codes)

    return target_combos
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_keyboard.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/talk_it_out/framework/keyboard.py tests/framework/test_keyboard.py
git commit -m "feat: add config_to_target_combos converter

- Converts config key names to evdev codes
- Expands modifiers to left/right variants
- Returns frozenset for efficient subset checking"
```

### Task 4: Add Edge Case Tests

**Files:**
- Modify: `tests/framework/test_keyboard.py`

**Step 1: Write edge case tests**

Add to `tests/framework/test_keyboard.py`:

```python
def test_process_key_event_ignore_unrelated_keys():
    """Keys not in any combo should update state but emit no events."""
    state = KeyboardState()
    event = KeyEvent(device_path="/dev/input/event0", key_code=30, is_press=True)  # 'A' key
    target_combos = {"record": frozenset([125, 56])}

    new_state, events = process_key_event(state, event, target_combos)

    assert 30 in new_state.held_keys
    assert len(events) == 0


def test_process_key_event_press_order_independence():
    """Combo should activate regardless of key press order."""
    target_combos = {"test": frozenset([125, 56])}

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
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/framework/test_keyboard.py -v`

Expected: All tests PASS (implementation already handles these cases)

**Step 3: Commit**

```bash
git add tests/framework/test_keyboard.py
git commit -m "test: add edge cases for keyboard event processing

- Unrelated keys don't trigger events
- Combo activation is order-independent
- Double press/release handled safely"
```

### Task 5: Verify Phase 2 Complete

**Step 1: Run all keyboard tests**

Run: `uv run pytest tests/framework/test_keyboard.py -v`

Expected: All tests PASS

**Step 2: Verify imports work**

Run:
```bash
uv run python -c "
from talk_it_out.framework.keyboard import (
    KeyboardState, KeyEvent, ComboEvent,
    process_key_event, config_to_target_combos
)
from talk_it_out.framework import config

cfg = config.default_config()
combos = config_to_target_combos(cfg)
print('Combos:', combos)

state = KeyboardState()
event = KeyEvent('/dev/input/event0', 125, True)
new_state, events = process_key_event(state, event, combos)
print('State after pressing super:', new_state)
"
```

Expected: Output showing combo definitions and state updates

---

## Phase 3: Device I/O Layer (Imperative Shell)

### Task 1: Create KeyboardMonitor Class Structure

**Files:**
- Create: `src/talk_it_out/framework/keyboard_io.py`

**Step 1: Write file header and basic class structure**

```python
# pattern: Imperative Shell
# Device I/O operations for keyboard monitoring

import select
import threading
from queue import Queue
from pathlib import Path
from typing import Dict, Optional
import structlog

from evdev import InputDevice, ecodes, list_devices
from talk_it_out.framework.keyboard import (
    KeyboardState,
    KeyEvent,
    ComboEvent,
    process_key_event,
    ComboType,
)

log = structlog.get_logger()


class KeyboardMonitor:
    """Monitors input devices for keyboard events and emits combo events.

    Scans all /dev/input/event* devices with EV_KEY capability, maintains
    per-device state, and feeds events through the pure keyboard reducer.
    Runs in background thread, emits ComboEvents to queue.
    """

    def __init__(
        self,
        target_combos: Dict[ComboType, frozenset[int]],
        event_queue: Queue
    ):
        """Initialize keyboard monitor.

        Args:
            target_combos: Map of combo names to required key code sets
            event_queue: Queue to receive ComboEvent objects
        """
        self.target_combos = target_combos
        self.event_queue = event_queue
        self.devices: Dict[str, InputDevice] = {}
        self.states: Dict[str, KeyboardState] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
```

**Step 2: Create the file**

Write the code above to `src/talk_it_out/framework/keyboard_io.py`.

**Step 3: Verify imports work**

Run: `uv run python -c "from talk_it_out.framework.keyboard_io import KeyboardMonitor; print('Import successful')"`

Expected: "Import successful"

**Step 4: Commit**

```bash
git add src/talk_it_out/framework/keyboard_io.py
git commit -m "feat: add KeyboardMonitor class structure

- Imperative Shell for device I/O
- Imports from keyboard.py (Functional Core)
- Maintains per-device state dictionaries
- Prepares for threading and queue integration"
```

### Task 2: Implement Device Scanning

**Files:**
- Modify: `src/talk_it_out/framework/keyboard_io.py`

**Step 1: Add device scanning method**

Add to `KeyboardMonitor` class:

```python
def _scan_devices(self) -> None:
    """Scan /dev/input for keyboard devices and open them.

    Opens all devices with EV_KEY capability. Skips devices that
    cannot be opened (permission denied, etc.) with warning log.
    """
    device_paths = list_devices()

    for path in device_paths:
        try:
            device = InputDevice(path)

            # Check if device has keyboard capability (EV_KEY)
            capabilities = device.capabilities(absinfo=False)
            if ecodes.EV_KEY not in capabilities:
                device.close()
                log.debug(
                    "device_not_keyboard",
                    path=path,
                    name=device.name
                )
                continue

            # Initialize state for this device
            self.devices[path] = device
            self.states[path] = KeyboardState()

            log.debug(
                "keyboard_device_opened",
                path=path,
                name=device.name
            )

        except (PermissionError, OSError) as e:
            log.warning(
                "keyboard_device_skipped",
                path=path,
                reason=str(e)
            )

    log.info(
        "keyboard_scan_complete",
        device_count=len(self.devices)
    )
```

**Step 2: Add device cleanup method**

Add to `KeyboardMonitor` class:

```python
def _close_devices(self) -> None:
    """Close all open input devices."""
    for path, device in self.devices.items():
        try:
            device.close()
            log.debug("keyboard_device_closed", path=path)
        except Exception as e:
            log.warning(
                "keyboard_device_close_error",
                path=path,
                error=str(e)
            )

    self.devices.clear()
    self.states.clear()
```

**Step 3: Verify the methods exist**

Run: `uv run python -c "from talk_it_out.framework.keyboard_io import KeyboardMonitor; import inspect; methods = [m for m in dir(KeyboardMonitor) if not m.startswith('__')]; print('Methods:', methods)"`

Expected: Should show `_scan_devices` and `_close_devices` in methods list

**Step 4: Commit**

```bash
git add src/talk_it_out/framework/keyboard_io.py
git commit -m "feat: add device scanning and cleanup

- Scan /dev/input for EV_KEY capable devices
- Skip permission-denied devices with warning
- Initialize per-device KeyboardState
- Clean close all devices on shutdown"
```

### Task 3: Implement Event Loop

**Files:**
- Modify: `src/talk_it_out/framework/keyboard_io.py`

**Step 1: Add event loop method**

Add to `KeyboardMonitor` class:

```python
def _event_loop(self) -> None:
    """Main event loop: monitor devices and process key events.

    Uses select() to efficiently wait for events from multiple devices.
    Processes events through pure reducer and emits to queue.
    Runs until self.running is set to False.
    """
    while self.running:
        # Check if we have any devices
        if not self.devices:
            log.debug("event_loop_no_devices")
            threading.Event().wait(1.0)  # Sleep 1 second
            continue

        # Use select with timeout for responsive shutdown
        device_map = {dev.fd: path for path, dev in self.devices.items()}
        readable_fds = list(device_map.keys())

        try:
            ready, _, _ = select.select(readable_fds, [], [], 1.0)
        except (OSError, ValueError) as e:
            # Device was removed or FD became invalid
            log.warning(
                "event_loop_select_error",
                error=str(e),
                device_count=len(self.devices)
            )
            break

        # Process events from ready devices
        for fd in ready:
            path = device_map[fd]
            device = self.devices[path]

            try:
                # Read events from this device
                for evdev_event in device.read():
                    # Only process key events (EV_KEY)
                    if evdev_event.type != ecodes.EV_KEY:
                        continue

                    # Convert to our KeyEvent
                    # evdev_event.value: 1=press, 0=release, 2=repeat
                    if evdev_event.value == 2:
                        continue  # Ignore key repeat events

                    key_event = KeyEvent(
                        device_path=path,
                        key_code=evdev_event.code,
                        is_press=(evdev_event.value == 1)
                    )

                    log.debug(
                        "key_event",
                        device=path,
                        code=evdev_event.code,
                        press=key_event.is_press
                    )

                    # Process through pure reducer
                    current_state = self.states[path]
                    new_state, combo_events = process_key_event(
                        current_state,
                        key_event,
                        self.target_combos
                    )

                    # Update state
                    self.states[path] = new_state

                    # Emit combo events to queue
                    for combo_event in combo_events:
                        self.event_queue.put(combo_event)
                        log.debug(
                            "combo_event_emitted",
                            event_type=combo_event.event_type,
                            combo=combo_event.combo_type
                        )

            except (OSError, IOError) as e:
                # Device disconnected - remove it
                log.warning(
                    "device_disconnected",
                    path=path,
                    device_name=device.name,
                    error=str(e)
                )
                try:
                    device.close()
                except Exception:
                    pass
                del self.devices[path]
                del self.states[path]
```

**Step 2: Verify method exists**

Run: `uv run python -c "from talk_it_out.framework.keyboard_io import KeyboardMonitor; import inspect; print(hasattr(KeyboardMonitor, '_event_loop'))"`

Expected: `True`

**Step 3: Commit**

```bash
git add src/talk_it_out/framework/keyboard_io.py
git commit -m "feat: implement event loop with select()

- Use select() for efficient multi-device monitoring
- Process EV_KEY events, ignore repeats
- Feed events through pure reducer
- Emit ComboEvents to queue
- Handle device disconnection gracefully"
```

### Task 4: Implement Start/Stop Methods

**Files:**
- Modify: `src/talk_it_out/framework/keyboard_io.py`

**Step 1: Add start() method**

Add to `KeyboardMonitor` class:

```python
def start(self) -> None:
    """Start keyboard monitoring in background thread.

    Scans devices and starts event loop thread.
    """
    if self.running:
        log.warning("keyboard_monitor_already_running")
        return

    log.info("keyboard_monitor_starting")

    # Scan for devices
    self._scan_devices()

    if not self.devices:
        log.warning(
            "keyboard_monitor_no_devices_found",
            message="No keyboard devices found - check permissions and hardware",
            hint="Ensure user is in 'input' group: sudo usermod -aG input $USER"
        )
        # Continue anyway - app can still run without keyboard monitoring

    # Start event loop thread
    self.running = True
    self.thread = threading.Thread(
        target=self._event_loop,
        name="KeyboardMonitor",
        daemon=True
    )
    self.thread.start()

    log.info(
        "keyboard_monitor_started",
        device_count=len(self.devices),
        combos=list(self.target_combos.keys())
    )
```

**Step 2: Add stop() method**

Add to `KeyboardMonitor` class:

```python
def stop(self) -> None:
    """Stop keyboard monitoring and cleanup.

    Stops event loop thread and closes all devices.
    Safe to call multiple times.
    """
    if not self.running:
        return

    log.info("keyboard_monitor_stopping")

    # Signal thread to stop
    self.running = False

    # Wait for thread to finish (with timeout)
    if self.thread and self.thread.is_alive():
        self.thread.join(timeout=2.0)
        if self.thread.is_alive():
            log.warning(
                "keyboard_monitor_thread_timeout",
                timeout_seconds=2.0,
                message="Thread did not stop gracefully"
            )

    # Close all devices
    self._close_devices()

    log.info("keyboard_monitor_stopped")
```

**Step 3: Verify methods exist**

Run: `uv run python -c "from talk_it_out.framework.keyboard_io import KeyboardMonitor; km = KeyboardMonitor({}, None); print('start:', callable(km.start), 'stop:', callable(km.stop))"`

Expected: `start: True stop: True`

**Step 4: Commit**

```bash
git add src/talk_it_out/framework/keyboard_io.py
git commit -m "feat: implement start/stop lifecycle methods

- start() scans devices and launches thread
- stop() signals shutdown and cleans up
- Thread uses daemon=True for clean exit
- Graceful shutdown with timeout"
```

### Task 5: Manual Testing Setup

**Files:**
- Create: `tests/manual/test_keyboard_monitor.py`
- Create: `tests/manual/README.md`

**Step 1: Create manual test script**

```python
#!/usr/bin/env python3
"""Manual test script for KeyboardMonitor.

Run this script and press Super+Alt to verify combo detection.
Press Ctrl-C to exit.

Usage:
    uv run python tests/manual/test_keyboard_monitor.py
"""

import queue
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from talk_it_out.framework import keyboard, keyboard_io, logging_setup

def main():
    # Setup logging
    log = logging_setup.configure_logging("DEBUG")
    log.info("manual_test_starting")

    # Create target combos
    target_combos = {
        "test_combo": frozenset([125, 126, 56, 100])  # Super+Alt (all variants)
    }

    # Create event queue
    event_queue = queue.Queue()

    # Create and start monitor
    monitor = keyboard_io.KeyboardMonitor(target_combos, event_queue)

    # Setup Ctrl-C handler
    def cleanup(signum, frame):
        log.info("manual_test_cleanup")
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    # Start monitoring
    monitor.start()

    log.info("manual_test_ready", message="Press Super+Alt to test combo detection")
    log.info("manual_test_ready", message="Press Ctrl-C to exit")

    # Process events
    try:
        while True:
            try:
                event = event_queue.get(timeout=1.0)
                log.info(
                    "combo_event_received",
                    type=event.event_type,
                    combo=event.combo_type,
                    device=event.device_path
                )
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        cleanup(None, None)

if __name__ == "__main__":
    main()
```

**Step 2: Make script executable and create directory**

Run:
```bash
mkdir -p tests/manual
chmod +x tests/manual/test_keyboard_monitor.py
```

**Step 3: Document manual test procedure**

Create `tests/manual/README.md`:

```markdown
# Manual Testing

## Keyboard Monitor Test

**Purpose:** Verify KeyboardMonitor detects key combos from physical keyboard

**Prerequisites:**
- User must be in `input` group
- Physical keyboard connected

**Run:**
```bash
uv run python tests/manual/test_keyboard_monitor.py
```

**Test steps:**
1. Script starts and logs "manual_test_ready"
2. Press Super+Alt keys together
3. Should see "combo_event_received" with type="combo_pressed"
4. Release keys
5. Should see "combo_event_received" with type="combo_released"
6. Press Ctrl-C to exit
7. Should see clean shutdown logs

**Expected output:**
```
manual_test_ready: Press Super+Alt to test combo detection
[Press Super+Alt]
combo_event_received: type=combo_pressed combo=test_combo device=/dev/input/event3
[Release keys]
combo_event_received: type=combo_released combo=test_combo device=/dev/input/event3
```
```

**Step 4: Commit**

```bash
git add tests/manual/test_keyboard_monitor.py tests/manual/README.md
git commit -m "test: add manual test for keyboard monitoring

- Manual test script for physical keyboard
- Documents test procedure and expected output
- Requires input group membership"
```

### Task 6: Verify Phase 3 Complete

**Step 1: Verify imports work**

Run:
```bash
uv run python -c "
from talk_it_out.framework.keyboard_io import KeyboardMonitor
from talk_it_out.framework.keyboard import config_to_target_combos
from talk_it_out.framework.config import default_config
print('All imports successful')
"
```

Expected: "All imports successful"

**Step 2: Verify class instantiation**

Run:
```bash
uv run python -c "
from talk_it_out.framework.keyboard_io import KeyboardMonitor
import queue
q = queue.Queue()
m = KeyboardMonitor({}, q)
print('Monitor created:', type(m).__name__)
"
```

Expected: "Monitor created: KeyboardMonitor"

**Step 3: Note manual testing required**

Manual testing with physical keyboard required - cannot be automated due to evdev hardware requirements.

---

## Phase 4: Main Application Integration

### Task 1: Add Required Imports

**Files:**
- Modify: `src/talk_it_out/main.py:10`

**Step 1: Add queue and keyboard imports**

Modify line 10 to include new modules:

```python
# Line 4-10 (modify lines 4 and 10)
import typer
import sys
import time
import queue
from pathlib import Path
from typing import Optional

from talk_it_out.framework import config, config_io, logging_setup, permissions, signals, keyboard, keyboard_io
```

**Step 2: Verify imports work**

Run: `uv run python -c "from talk_it_out.main import app; print('Imports successful')"`

Expected: "Imports successful"

**Step 3: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: add keyboard monitoring imports

- Import queue for event queue
- Import keyboard and keyboard_io modules"
```

### Task 2: Initialize Keyboard Monitoring

**Files:**
- Modify: `src/talk_it_out/main.py:50-53`

**Step 1: Replace TODO with keyboard initialization**

Replace lines 50-53 with:

```python
# Convert config combos to evdev keycodes
target_combos = keyboard.config_to_target_combos(cfg)

# Create event queue for combo events
combo_queue: queue.Queue[keyboard.ComboEvent] = queue.Queue()

# Start keyboard monitor
monitor = keyboard_io.KeyboardMonitor(target_combos, combo_queue)
registry.register(monitor.stop)
monitor.start()

log.info("keyboard_monitoring_started", combos=list(target_combos.keys()))
```

**Step 2: Verify changes are correct**

Run: `uv run python -c "import ast; tree = ast.parse(open('src/talk_it_out/main.py').read()); print('Syntax valid')"`

Expected: "Syntax valid"

**Step 3: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: initialize keyboard monitoring in run command

- Convert config combos to target key codes
- Create queue for ComboEvent objects
- Start KeyboardMonitor with cleanup registration
- Log monitoring start with combo names"
```

### Task 3: Replace Keep-Alive Loop with Event Processing

**Files:**
- Modify: `src/talk_it_out/main.py:55-61`

**Step 1: Replace sleep loop with queue processing**

Replace lines 55-61 with:

```python
# Event processing loop
try:
    while True:
        try:
            combo_event = combo_queue.get(timeout=1.0)

            if combo_event.event_type == 'combo_pressed':
                log.info(
                    "combo_activated",
                    combo=combo_event.combo_type,
                    device=combo_event.device_path
                )

            elif combo_event.event_type == 'combo_released':
                log.info(
                    "combo_released",
                    combo=combo_event.combo_type,
                    device=combo_event.device_path
                )

        except queue.Empty:
            # Timeout - continue loop (allows periodic signal checking)
            pass

except KeyboardInterrupt:
    # Signal handler will take care of cleanup
    pass
```

**Step 2: Verify syntax**

Run: `uv run python -m py_compile src/talk_it_out/main.py`

Expected: No output (successful compilation)

**Step 3: Commit**

```bash
git add src/talk_it_out/main.py
git commit -m "feat: replace keep-alive with event processing loop

- Process ComboEvents from queue
- Log combo_activated on press
- Log combo_released on release
- Use timeout for responsive shutdown
- Maintain KeyboardInterrupt handling"
```

### Task 4: Manual Integration Test

**Files:**
- Create: `tests/manual/test_main_integration.md`

**Step 1: Document manual test procedure**

```markdown
# Main Application Integration Test

## Purpose
Verify keyboard monitoring integration in main run command.

## Prerequisites
- User in `input` group
- Physical keyboard connected
- Config file at `~/.config/talk-it-out/config.toml` with combos defined

## Test Procedure

### 1. Start Application

```bash
uv run python -m talk_it_out.main run --log-level INFO
```

**Expected output:**
```
application_started: config_path=/home/user/.config/talk-it-out/config.toml
keyboard_monitoring_started: combos=['record_for_paste']
```

### 2. Press Combo Keys

Press Super+Alt together.

**Expected output:**
```
combo_activated: combo=record_for_paste device=/dev/input/event3
```

### 3. Release Combo Keys

Release Super+Alt.

**Expected output:**
```
combo_released: combo=record_for_paste device=/dev/input/event3
```

### 4. Press Ctrl-C

**Expected output:**
```
keyboard_monitor_stopping
keyboard_device_closed: path=/dev/input/event3
keyboard_monitor_stopped
shutdown_complete
```

### 5. Verify Clean Exit

Command should exit with status 0, no error messages.

## Troubleshooting

**No devices found:**
- Check `groups` includes `input`
- Reboot may be required after adding to group

**Permission denied:**
- Check `/dev/input/event*` permissions
- Verify user in input group: `groups | grep input`

**No combo_activated logs:**
- Verify config has correct combo definition
- Try DEBUG log level to see key events: `--log-level DEBUG`
- Check device path in logs matches your keyboard
```

**Step 2: Create the file**

Write the content above to `tests/manual/test_main_integration.md`.

**Step 3: Commit**

```bash
git add tests/manual/test_main_integration.md
git commit -m "docs: add manual integration test procedure

- Documents end-to-end testing steps
- Expected log output at each stage
- Troubleshooting common issues"
```

### Task 5: Verify Phase 4 Complete

**Step 1: Verify main.py structure**

Run:
```bash
uv run python -c "
import ast

# Parse main.py
with open('src/talk_it_out/main.py') as f:
    tree = ast.parse(f.read())

# Verify imports exist
source = open('src/talk_it_out/main.py').read()
assert 'import queue' in source
assert 'keyboard' in source
assert 'keyboard_io' in source

print('Structure verified')
"
```

Expected: "Structure verified"

**Step 2: Verify run command can be called**

Run: `uv run python -m talk_it_out.main --help`

Expected: Shows help with `run` command listed

**Step 3: Document integration complete**

Add comment to main.py above keyboard initialization:

```python
# Keyboard monitoring integration
# Phase 4: Main application now processes combo events via queue
```

**Step 4: Final commit for phase**

```bash
git add src/talk_it_out/main.py
git commit -m "docs: document keyboard integration completion

- Add comment explaining phase 4 integration
- Queue-based event processing now active"
```

---

## Phase 5: Error Handling

### Task 1: Add Debug Logging to Event Processing

**Files:**
- Verify: `src/talk_it_out/framework/keyboard_io.py` (event loop section)

**Step 1: Verify debug logging exists**

Check that debug logging is present in the event loop:

```python
# Inside _event_loop, after creating KeyEvent
log.debug(
    "key_event",
    device=path,
    code=evdev_event.code,
    press=key_event.is_press
)

# After queue.put(combo_event)
log.debug(
    "combo_event_emitted",
    event_type=combo_event.event_type,
    combo=combo_event.combo_type
)
```

Run: `grep -n "log.debug" src/talk_it_out/framework/keyboard_io.py`

Expected: Shows debug log calls in event loop (already added in Phase 3)

### Task 2: Enhance Device Scanning Error Handling

**Files:**
- Modify: `src/talk_it_out/framework/keyboard_io.py` (_scan_devices method)

**Step 1: Add device capability check logging**

Verify the EV_KEY check section logs when devices are skipped:

```python
# Check if device has keyboard capability (EV_KEY)
capabilities = device.capabilities(absinfo=False)
if ecodes.EV_KEY not in capabilities:
    device.close()
    log.debug(
        "device_not_keyboard",
        path=path,
        name=device.name
    )
    continue
```

Run: `grep -A2 "device_not_keyboard" src/talk_it_out/framework/keyboard_io.py`

Expected: Shows the debug log for non-keyboard devices (already added in Phase 3)

### Task 3: Add Empty Device List Handling

**Files:**
- Verify: `src/talk_it_out/framework/keyboard_io.py` (start method)

**Step 1: Verify empty device handling exists**

Check that start() method includes helpful warning for no devices:

```python
if not self.devices:
    log.warning(
        "keyboard_monitor_no_devices_found",
        message="No keyboard devices found - check permissions and hardware",
        hint="Ensure user is in 'input' group: sudo usermod -aG input $USER"
    )
```

Run: `grep -A3 "no_devices_found" src/talk_it_out/framework/keyboard_io.py`

Expected: Shows WARNING level with helpful message (already added in Phase 3)

### Task 4: Enhance Event Loop Error Handling

**Files:**
- Verify: `src/talk_it_out/framework/keyboard_io.py` (_event_loop method)

**Step 1: Verify error context in select() failure**

Check that select() exception includes error details:

```python
except (OSError, ValueError) as e:
    log.warning(
        "event_loop_select_error",
        error=str(e),
        device_count=len(self.devices)
    )
    break
```

**Step 2: Verify error context in device disconnection**

Check that device disconnection includes error details:

```python
except (OSError, IOError) as e:
    log.warning(
        "device_disconnected",
        path=path,
        device_name=device.name,
        error=str(e)
    )
```

Run: `grep -B1 -A3 "device_disconnected" src/talk_it_out/framework/keyboard_io.py`

Expected: Shows error variable captured and logged (already added in Phase 3)

### Task 5: Add Thread Timeout Warning

**Files:**
- Verify: `src/talk_it_out/framework/keyboard_io.py` (stop method)

**Step 1: Verify timeout logging includes context**

Check that thread timeout warning has helpful information:

```python
if self.thread.is_alive():
    log.warning(
        "keyboard_monitor_thread_timeout",
        timeout_seconds=2.0,
        message="Thread did not stop gracefully"
    )
```

Run: `grep -A2 "thread_timeout" src/talk_it_out/framework/keyboard_io.py`

Expected: Shows timeout_seconds and message fields (already added in Phase 3)

### Task 6: Document Error Handling Strategy

**Files:**
- Modify: `src/talk_it_out/framework/keyboard_io.py` (add module docstring)

**Step 1: Add comprehensive module docstring**

Add after the pattern comment at the top of keyboard_io.py:

```python
# pattern: Imperative Shell
# Device I/O operations for keyboard monitoring

"""Keyboard device monitoring with error handling.

Error Handling Strategy:
- Device permission errors: Skip device, log WARNING, continue
- Device disconnection: Remove device, log WARNING, continue monitoring
- No devices found: Log WARNING with hint, continue app execution
- Event loop failures: Log WARNING, stop monitoring thread
- Thread timeout: Log WARNING, continue shutdown

Logging Levels:
- DEBUG: Individual key events, device open/close, non-keyboard devices
- INFO: Monitoring start/stop, combo events, device count
- WARNING: Device errors, permission issues, disconnections
- ERROR: Not used (all errors are recoverable)

All errors are handled gracefully - the application continues running
even if keyboard monitoring fails completely.
"""
```

**Step 2: Verify docstring is present**

Run: `head -30 src/talk_it_out/framework/keyboard_io.py | grep -A10 "Error Handling"`

Expected: Shows the error handling documentation

**Step 3: Commit**

```bash
git add src/talk_it_out/framework/keyboard_io.py
git commit -m "docs: document error handling strategy

- Explain all error scenarios
- Document logging level usage
- Clarify graceful degradation"
```

### Task 7: Create Error Handling Test Checklist

**Files:**
- Create: `tests/manual/test_error_handling.md`

**Step 1: Create manual test checklist**

```markdown
# Error Handling Manual Tests

## Test 1: Permission Check (Unit Test)

Unit test with mocked group membership (not manual system modification).

See `tests/framework/test_permissions.py` for permission validation tests.

---

## Test 2: No Keyboard Devices

**Setup:** Disconnect all keyboards (use SSH/remote session)

**Run:** `uv run python -m talk_it_out.main run --log-level INFO`

**Expected:**
```
keyboard_scan_complete: device_count=0
keyboard_monitor_no_devices_found: message=No keyboard devices found...
keyboard_monitoring_started: combos=['record_for_paste']
```
- Application continues running
- No crash or error exit

---

## Test 3: Device Disconnection During Operation

**Setup:** Start app with keyboard connected

**Run:** `uv run python -m talk_it_out.main run --log-level DEBUG`

**Action:** Unplug keyboard while running

**Expected:**
```
device_disconnected: path=/dev/input/eventX device_name=...
```
- Monitoring continues with remaining devices
- No crash

---

## Test 4: Debug Logging

**Run:** `uv run python -m talk_it_out.main run --log-level DEBUG`

**Action:** Press Super+Alt

**Expected:** Should see:
```
key_event: device=/dev/input/eventX code=125 press=True
key_event: device=/dev/input/eventX code=56 press=True
combo_event_emitted: event_type=combo_pressed combo=record_for_paste
```

---

## Test 5: Graceful Shutdown Under Load

**Run:** `uv run python -m talk_it_out.main run`

**Action:** Press keys rapidly, then Ctrl-C while still pressing

**Expected:**
```
keyboard_monitor_stopping
keyboard_device_closed: path=/dev/input/eventX
keyboard_monitor_stopped
shutdown_complete
```
- Clean shutdown within 3 seconds
- No thread timeout warnings

---

## Test 6: Invalid Config Handling

**Setup:** Create invalid config
```bash
echo '[keys.combos]
test = ["invalid_key_name"]' > ~/.config/talk-it-out/config.toml
```

**Run:** `uv run python -m talk_it_out.main run`

**Expected:**
- Config validation error before keyboard monitoring starts
- Clear error message about invalid key name
- Application exits with status 1

**Cleanup:** Restore valid config
```

**Step 2: Create the file**

Write the content above to `tests/manual/test_error_handling.md`.

**Step 3: Commit**

```bash
git add tests/manual/test_error_handling.md
git commit -m "test: add error handling manual test checklist

- Permission check via unit test
- No devices found scenario
- Device disconnection during operation
- Debug logging verification
- Graceful shutdown under load
- Invalid config handling"
```

### Task 8: Verify Phase 5 Complete

**Step 1: Verify all error scenarios have logging**

Run:
```bash
grep -n "log.warning\|log.error\|log.debug" src/talk_it_out/framework/keyboard_io.py | wc -l
```

Expected: Multiple logging calls (at least 8-10)

**Step 2: Verify error handling doesn't crash**

Run:
```bash
uv run python -c "
from talk_it_out.framework.keyboard_io import KeyboardMonitor
import queue

# Should not crash even with empty combos
q = queue.Queue()
m = KeyboardMonitor({}, q)
print('No crash on initialization')
"
```

Expected: "No crash on initialization"

**Step 3: Review manual test checklist**

Confirm all error scenarios documented:
- Permission check ✓ (unit test)
- No devices found ✓
- Device disconnection ✓
- Debug logging ✓
- Graceful shutdown ✓
- Invalid config ✓

---

## Phase 6: Documentation and Manual Testing

### Task 1: Update README Status Section

**Files:**
- Modify: `README.md:5-16`

**Step 1: Update status to reflect keyboard monitoring completion**

Replace lines 5-16 with:

```markdown
## Status

**Phase 1 (CLI Framework): Complete**

The CLI application framework is implemented with:
- Configuration management (TOML)
- Structured logging (structlog)
- Signal handling with cleanup timeout
- Permission checks for input group
- Subcommands: `run`, `config-edit`

**Phase 2 (Keyboard Monitoring): Complete**

Keyboard event monitoring is implemented with:
- Multi-device keyboard monitoring via evdev
- Key combination detection (e.g., Super+Alt)
- Per-device state isolation (paired press/release events)
- Queue-based event emission
- Graceful error handling (device disconnection, permissions)

**Next:** Phase 3 will add audio recording with PulseAudio/PipeWire.
```

**Step 2: Verify markdown formatting**

Run: `head -25 README.md`

Expected: Shows updated status section with Phase 2 complete

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README status for keyboard monitoring

- Mark Phase 2 (Keyboard Monitoring) as complete
- List keyboard monitoring features
- Update next phase to audio recording"
```

### Task 2: Update README Config Example

**Files:**
- Modify: `README.md:64-85`

**Step 1: Update config example to use combos dict**

Replace the `[keys]` section with:

```toml
[keys.combos]
record_for_paste = ["super", "alt"]
```

**Step 2: Add explanation of combos format**

After the config example, add:

```markdown
### Key Combinations

Multiple key combinations can be defined in `[keys.combos]`:

```toml
[keys.combos]
record_for_paste = ["super", "alt"]
quick_note = ["ctrl", "n"]
```

Valid key names:
- `super` - Windows/Command key (left or right)
- `alt` - Alt key (left or right)
- `ctrl` - Control key (left or right)
- `shift` - Shift key (left or right)

Each combo is detected when all keys are pressed together on the same device.
```

**Step 3: Verify config example is correct**

Run: `grep -A10 "\[keys" README.md`

Expected: Shows new `[keys.combos]` format

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update config example to use combos dict

- Change from combination list to combos dict
- Add explanation of combos format
- Document valid key names
- Note per-device detection"
```

### Task 3: Create Manual Test Checklist

**Files:**
- Create: `tests/manual/CHECKLIST.md`

**Step 1: Create tests/manual directory**

Run: `mkdir -p tests/manual`

**Step 2: Create comprehensive manual test checklist**

```markdown
# Keyboard Monitoring Manual Test Checklist

Use this checklist to manually verify keyboard monitoring behavior.

## Prerequisites

- [ ] User is in `input` group: `groups | grep input`
- [ ] Physical keyboard connected
- [ ] Config file exists: `~/.config/talk-it-out/config.toml`
- [ ] Config has valid combos defined

---

## Test 1: Basic Combo Activation

**Objective:** Verify combo press/release detection

**Steps:**
1. Run: `uv run python -m talk_it_out.main run --log-level INFO`
2. Press Super+Alt keys together
3. Hold for 1 second
4. Release both keys
5. Press Ctrl-C to exit

**Expected Results:**
- [ ] Log shows: `combo_activated: combo=record_for_paste`
- [ ] Log shows: `combo_released: combo=record_for_paste`
- [ ] Both events show same `device=` path
- [ ] Clean shutdown with no errors

---

## Test 2: Press/Release Event Pairing

**Objective:** Verify events are paired from same device

**Steps:**
1. Run: `uv run python -m talk_it_out.main run --log-level INFO`
2. Press Super+Alt
3. Note the device path in combo_activated log
4. Release Super+Alt
5. Note the device path in combo_released log

**Expected Results:**
- [ ] combo_activated shows device path (e.g., `/dev/input/event3`)
- [ ] combo_released shows **same** device path
- [ ] Device paths match between press and release

---

## Test 3: Multiple Rapid Presses

**Objective:** Verify rapid activation/deactivation works correctly

**Steps:**
1. Run: `uv run python -m talk_it_out.main run --log-level INFO`
2. Press Super+Alt rapidly 5 times (press and release quickly)

**Expected Results:**
- [ ] Each press shows combo_activated log
- [ ] Each release shows combo_released log
- [ ] Total of 5 activated + 5 released events
- [ ] No missed or duplicate events

---

## Test 4: Clean Shutdown (Ctrl-C)

**Objective:** Verify graceful shutdown under normal conditions

**Steps:**
1. Run: `uv run python -m talk_it_out.main run --log-level INFO`
2. Wait 2 seconds
3. Press Ctrl-C

**Expected Results:**
- [ ] Log shows: `keyboard_monitor_stopping`
- [ ] Log shows: `keyboard_monitor_stopped`
- [ ] Log shows: `shutdown_complete`
- [ ] Exit within 3 seconds
- [ ] No error messages
- [ ] No thread timeout warnings

---

## Test 5: Multiple Keyboards (if available)

**Objective:** Verify per-device state isolation

**Prerequisites:** Two physical keyboards connected

**Steps:**
1. Run: `uv run python -m talk_it_out.main run --log-level DEBUG`
2. Press Super+Alt on keyboard 1
3. Note the device path in logs
4. Keep holding on keyboard 1
5. Press Super+Alt on keyboard 2
6. Note the device path in logs

**Expected Results:**
- [ ] Both keyboards trigger combo_activated
- [ ] Each shows different device path
- [ ] Releasing keyboard 1 doesn't affect keyboard 2
- [ ] Each keyboard tracked independently

---

## Test 6: Invalid Config Detection

**Objective:** Verify config validation catches errors

**Steps:**
1. Edit config: `nano ~/.config/talk-it-out/config.toml`
2. Change combo to: `test = ["invalid_key_name"]`
3. Save and exit
4. Run: `uv run python -m talk_it_out.main run`

**Expected Results:**
- [ ] Application exits immediately
- [ ] Error message shows: `Invalid key name 'invalid_key_name'`
- [ ] Lists valid key names
- [ ] Exit status is 1

**Cleanup:**
```bash
# Restore valid config
uv run python -m talk_it_out.main config-edit
```

---

## Test 7: Debug Logging Verification

**Objective:** Verify debug logs show key event details

**Steps:**
1. Run: `uv run python -m talk_it_out.main run --log-level DEBUG`
2. Press Super key (don't release yet)
3. Press Alt key (both now held)
4. Release Super key
5. Release Alt key

**Expected Results:**
- [ ] Log shows: `key_event: code=125 press=True` (or 126 for right super)
- [ ] Log shows: `key_event: code=56 press=True` (or 100 for right alt)
- [ ] Log shows: `combo_event_emitted: event_type=combo_pressed`
- [ ] Log shows: `key_event: code=125 press=False`
- [ ] Log shows: `combo_event_emitted: event_type=combo_released`
- [ ] Key codes match expected values

---

## Test Results Template

Date: _____________
Tester: _____________
OS: _____________
Keyboard(s): _____________

| Test | Pass | Fail | Notes |
|------|------|------|-------|
| 1. Basic Combo Activation | ☐ | ☐ | |
| 2. Event Pairing | ☐ | ☐ | |
| 3. Rapid Presses | ☐ | ☐ | |
| 4. Clean Shutdown | ☐ | ☐ | |
| 5. Multiple Keyboards | ☐ | ☐ | |
| 6. Invalid Config | ☐ | ☐ | |
| 7. Debug Logging | ☐ | ☐ | |

**Overall Status:** ☐ Pass ☐ Fail

**Issues Found:**
```

**Step 3: Create the file**

Write the content above to `tests/manual/CHECKLIST.md`.

**Step 4: Commit**

```bash
git add tests/manual/CHECKLIST.md
git commit -m "test: create manual testing checklist

- 7 test scenarios covering core functionality
- Prerequisites and cleanup steps
- Expected results for each test
- Test results tracking template"
```

### Task 4: Add Keyboard Monitoring Section to README

**Files:**
- Modify: `README.md` (add new section after Usage)

**Step 1: Add Keyboard Monitoring section**

After the Usage section, add:

```markdown
## Keyboard Monitoring

The application monitors all keyboard input devices for configured key combinations.

### How It Works

1. **Device Scanning:** On startup, scans `/dev/input/event*` for devices with keyboard capability
2. **Event Processing:** Monitors all keyboards simultaneously using efficient `select()` system call
3. **Per-Device State:** Each keyboard maintains independent state for proper press/release pairing
4. **Queue-Based Events:** Combo activations are emitted to a queue for asynchronous processing

### Supported Key Combinations

Configure combinations in `~/.config/talk-it-out/config.toml`:

```toml
[keys.combos]
record_for_paste = ["super", "alt"]
quick_note = ["ctrl", "n"]
```

### Requirements

- User must be in `input` group: `sudo usermod -aG input $USER`
- Reboot required after adding to group
- At least one keyboard device with EV_KEY capability

### Troubleshooting

**No combo events detected:**
- Verify user in input group: `groups | grep input`
- Check devices found: Run with `--log-level DEBUG`
- Verify config syntax: `uv run python -m talk_it_out.main config-edit`

**Permission denied errors:**
- Ensure input group membership
- Reboot after group change
- Check `/dev/input/event*` permissions

### Manual Testing

See [`tests/manual/CHECKLIST.md`](tests/manual/CHECKLIST.md) for comprehensive test procedures.
```

**Step 2: Verify section formatting**

Run: `grep -A30 "## Keyboard Monitoring" README.md`

Expected: Shows the new section with all subsections

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Keyboard Monitoring section to README

- Explain how monitoring works
- Document configuration format
- List requirements and troubleshooting
- Link to manual test checklist"
```

### Task 5: Verify Phase 6 Complete

**Step 1: Verify all documentation updates**

Run:
```bash
# Check status section updated
grep -A15 "Phase 2" README.md

# Check config example updated
grep -A3 "\[keys.combos\]" README.md

# Check manual test checklist exists
ls -la tests/manual/CHECKLIST.md

# Check new Keyboard Monitoring section
grep "## Keyboard Monitoring" README.md
```

Expected: All sections present and correct

**Step 2: Verify checklist has all 7 tests**

Run: `grep "^## Test" tests/manual/CHECKLIST.md | wc -l`

Expected: 7

**Step 3: Verify README formatting**

Visual inspection or markdown validation tool.

---

## Phase 7: Config Migration Helper (SKIPPED)

**Reason:** No deployment yet, so no existing configs to migrate. Users will start with new format from Phase 1.

---

## Phase 8: Integration Testing

### Task 1: Add Keyboard Monitoring Startup Test

**Files:**
- Modify: `tests/integration/test_cli_framework.sh`

**Step 1: Add test after Test 5**

```bash
# Test 6: Keyboard monitoring starts successfully
echo "Test 6: Keyboard monitoring starts successfully"
rm -rf ~/.config/talk-it-out
uv run python -m talk_it_out.main run --log-level INFO 2>&1 | head -20 > /tmp/test6-output.txt &
PID=$!
sleep 2
kill -INT $PID || true
wait $PID || true

# Check for keyboard monitoring startup log
if grep -q "keyboard_monitoring_started" /tmp/test6-output.txt; then
    echo "✅ Test 6 passed: Keyboard monitoring started"
else
    echo "❌ Test 6 failed: No keyboard monitoring startup log found"
    cat /tmp/test6-output.txt
    exit 1
fi
rm /tmp/test6-output.txt
```

**Step 2: Verify test runs**

Run: `bash tests/integration/test_cli_framework.sh`

Expected: Test 6 passes with ✅

**Step 3: Commit**

```bash
git add tests/integration/test_cli_framework.sh
git commit -m "test: add keyboard monitoring startup test

- Verify keyboard_monitoring_started log appears
- Check successful initialization
- Test 6 in integration suite"
```

### Task 2: Add Combo Config Validation Test

**Files:**
- Modify: `tests/integration/test_cli_framework.sh`

**Step 1: Add test after Test 6**

```bash
# Test 7: Invalid combo key name detection
echo "Test 7: Invalid combo key name detection"
rm -rf ~/.config/talk-it-out
mkdir -p ~/.config/talk-it-out

# Create config with invalid key name in combo
cat > ~/.config/talk-it-out/config.toml << 'EOF'
[keys.combos]
test_combo = ["invalid_key"]

[audio]
sample_rate = 16000
channels = 1
device = ""

[whisper]
model = "base"
language = ""

[paste]
method = "clipboard"

[logging]
level = "INFO"
EOF

# Run and expect validation error
if uv run python -m talk_it_out.main run 2>&1 | grep -q "Invalid key name 'invalid_key'"; then
    echo "✅ Test 7 passed: Invalid combo key detected"
else
    echo "❌ Test 7 failed: Invalid key validation did not trigger"
    exit 1
fi
```

**Step 2: Verify test runs**

Run: `bash tests/integration/test_cli_framework.sh`

Expected: Test 7 passes with ✅

**Step 3: Commit**

```bash
git add tests/integration/test_cli_framework.sh
git commit -m "test: add combo config validation test

- Test invalid key name detection
- Verify error message includes key name
- Test 7 in integration suite"
```

### Task 3: Add Empty Combos Dict Test

**Files:**
- Modify: `tests/integration/test_cli_framework.sh`

**Step 1: Add test after Test 7**

```bash
# Test 8: Empty combos dict validation
echo "Test 8: Empty combos dict validation"
rm -rf ~/.config/talk-it-out
mkdir -p ~/.config/talk-it-out

# Create config with empty combos
cat > ~/.config/talk-it-out/config.toml << 'EOF'
[keys.combos]

[audio]
sample_rate = 16000
channels = 1
device = ""

[whisper]
model = "base"
language = ""

[paste]
method = "clipboard"

[logging]
level = "INFO"
EOF

# Run and expect validation error
if uv run python -m talk_it_out.main run 2>&1 | grep -q "combos cannot be empty"; then
    echo "✅ Test 8 passed: Empty combos dict detected"
else
    echo "❌ Test 8 failed: Empty combos validation did not trigger"
    exit 1
fi
```

**Step 2: Verify test runs**

Run: `bash tests/integration/test_cli_framework.sh`

Expected: Test 8 passes with ✅

**Step 3: Commit**

```bash
git add tests/integration/test_cli_framework.sh
git commit -m "test: add empty combos dict validation test

- Test empty combos section is rejected
- Verify helpful error message
- Test 8 in integration suite"
```

### Task 4: Add Multi-Device Cleanup Test

**Files:**
- Modify: `tests/integration/test_cli_framework.sh`

**Step 1: Add test after Test 8**

```bash
# Test 9: Keyboard monitoring cleanup on shutdown
echo "Test 9: Keyboard monitoring cleanup on shutdown"
rm -rf ~/.config/talk-it-out
uv run python -m talk_it_out.main run --log-level INFO 2>&1 | head -30 > /tmp/test9-output.txt &
PID=$!
sleep 2
kill -INT $PID
wait $PID

# Check for clean shutdown logs
if grep -q "keyboard_monitor_stopping" /tmp/test9-output.txt && \
   grep -q "keyboard_monitor_stopped" /tmp/test9-output.txt && \
   grep -q "shutdown_complete" /tmp/test9-output.txt; then
    echo "✅ Test 9 passed: Keyboard monitoring cleanup successful"
else
    echo "❌ Test 9 failed: Missing cleanup logs"
    cat /tmp/test9-output.txt
    exit 1
fi
rm /tmp/test9-output.txt
```

**Step 2: Verify test runs**

Run: `bash tests/integration/test_cli_framework.sh`

Expected: Test 9 passes with ✅

**Step 3: Commit**

```bash
git add tests/integration/test_cli_framework.sh
git commit -m "test: add keyboard monitoring cleanup test

- Verify monitor stops cleanly on SIGINT
- Check all cleanup logs present
- Test 9 in integration suite"
```

### Task 5: Update Test Summary

**Files:**
- Modify: `tests/integration/test_cli_framework.sh` (final line)

**Step 1: Update success message**

Change the final echo to:

```bash
echo ""
echo "All integration tests passed! (9 tests)"
```

**Step 2: Verify all tests pass**

Run: `bash tests/integration/test_cli_framework.sh`

Expected: All 9 tests pass, final message shows "(9 tests)"

**Step 3: Commit**

```bash
git add tests/integration/test_cli_framework.sh
git commit -m "test: update test count in summary

- 9 total integration tests
- 4 new keyboard monitoring tests added"
```

### Task 6: Add Integration Test Documentation

**Files:**
- Create: `tests/integration/README.md`

**Step 1: Document integration test suite**

```markdown
# Integration Tests

Integration tests verify end-to-end behavior of the CLI application.

## Running Tests

```bash
bash tests/integration/test_cli_framework.sh
```

Or from project root:
```bash
./tests/integration/test_cli_framework.sh
```

## Test Suite

### Framework Tests (1-5)

1. **Fresh install config creation** - Verifies default config is created
2. **Invalid config detection** - Tests config validation errors
3. **Custom config path** - Tests --config flag
4. **Log level override** - Tests --log-level flag
5. **SIGTERM handling** - Verifies graceful shutdown

### Keyboard Monitoring Tests (6-9)

6. **Keyboard monitoring startup** - Verifies monitoring initializes
7. **Invalid combo key detection** - Tests key name validation
8. **Empty combos dict validation** - Tests empty combos are rejected
9. **Keyboard monitoring cleanup** - Verifies clean shutdown

## Test Structure

Each test:
1. Sets up test environment (cleans config, creates test files)
2. Runs application with specific configuration
3. Verifies expected behavior (logs, exit codes, files)
4. Cleans up test artifacts

## Cleanup

Tests use `trap cleanup EXIT` to ensure cleanup runs regardless of test outcome.

Cleaned resources:
- `~/.config/talk-it-out` directory
- `/tmp/test-config.toml`
- `/tmp/test*-output.txt` files

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed

## Requirements

- User in `input` group (for keyboard monitoring tests)
- `uv` package manager installed
- Project dependencies installed (`uv sync`)
```

**Step 2: Create the file**

Write the content above to `tests/integration/README.md`.

**Step 3: Commit**

```bash
git add tests/integration/README.md
git commit -m "docs: add integration test documentation

- Explain how to run tests
- List all 9 tests with descriptions
- Document test structure and cleanup
- Note requirements"
```

### Task 7: Verify Phase 8 Complete

**Step 1: Run full integration test suite**

Run: `bash tests/integration/test_cli_framework.sh`

Expected: All 9 tests pass

**Step 2: Verify test coverage**

Check that keyboard monitoring is tested:
- ✓ Startup initialization (Test 6)
- ✓ Config validation (Tests 7, 8)
- ✓ Clean shutdown (Test 9)
- ✓ Integration with existing framework (all tests)

**Step 3: Verify documentation**

Run: `cat tests/integration/README.md | grep "Test Suite" -A20`

Expected: Shows all 9 tests documented

---

## Execution Handoff

Plan complete and saved to `docs/plans/2025-10-25-keyboard-monitoring-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - Dispatch fresh subagent per task, review between tasks, fast iteration

Use: `ed3d-superpowers:subagent-driven-development`

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Use: `ed3d-superpowers:executing-plans` in new session
