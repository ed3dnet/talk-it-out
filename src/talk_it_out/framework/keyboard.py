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


def config_to_target_combos(cfg: dict) -> Dict[ComboType, List[frozenset[int]]]:
    """Convert config to list of valid key code sets per combo.

    Each combo can have multiple valid key combinations. Each combination
    is represented as a frozenset of key codes.

    Args:
        cfg: Configuration dict with keys.combos section

    Returns:
        Dict mapping combo names to lists of frozensets.
        Each frozenset is one valid key combination.

    Example:
        Input: {"keys": {"combos": {"record": [
            ["KEY_LEFTMETA", "KEY_LEFTALT"],
            ["KEY_RIGHTMETA", "KEY_RIGHTALT"]
        ]}}}
        Output: {"record": [frozenset([125, 56]), frozenset([126, 100])]}
    """
    target_combos: Dict[ComboType, List[frozenset[int]]] = {}

    for combo_name, combo_list in cfg["keys"]["combos"].items():
        valid_combos: List[frozenset[int]] = []

        # Each inner list is one valid key combination
        for key_list in combo_list:
            key_codes: Set[int] = set()

            # Convert each key name to its evdev code (case-insensitive)
            for key_name in key_list:
                key_upper = key_name.upper()
                # Get the key code from ecodes module
                key_code = getattr(ecodes, key_upper)
                key_codes.add(key_code)

            valid_combos.append(frozenset(key_codes))

        target_combos[combo_name] = valid_combos

    return target_combos


def process_key_event(
    state: KeyboardState,
    event: KeyEvent,
    target_combos: Dict[ComboType, List[frozenset[int]]]
) -> Tuple[KeyboardState, List[ComboEvent]]:
    """Pure reducer: processes key event, returns (new_state, output_events).

    - On press: Add key to held_keys, check if any combo now complete
    - On release: Remove key from held_keys, check if any combo now broken
    - Returns combo_pressed/combo_released events as needed

    Args:
        state: Current keyboard state (immutable)
        event: Key press or release event
        target_combos: Map of combo names to lists of valid key combinations

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
    for combo_name, valid_combos in target_combos.items():
        # Check if held_keys matches ANY of the valid combos
        if any(combo_keys == new_held_keys for combo_keys in valid_combos):
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
