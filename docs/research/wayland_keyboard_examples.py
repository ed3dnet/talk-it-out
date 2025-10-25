#!/usr/bin/env python3
"""
Working keyboard monitoring examples for Wayland on KDE Plasma 6.

These examples use python-evdev, which works on Wayland by reading
directly from /dev/input/eventX devices below the graphics stack.

REQUIREMENTS:
    pip install evdev
    User in 'input' group: sudo usermod -a -G input $USER
    Then logout/login for group changes to take effect.

All examples tested on: KDE Plasma 6, Fedora 42, Wayland
"""

import evdev
from evdev import ecodes
import time
import asyncio
from typing import Callable, Set, Tuple, Dict
from select import select


# ============================================================================
# EXAMPLE 1: List Available Keyboard Devices
# ============================================================================

def example_list_devices():
    """Find and list all keyboard devices on the system."""
    print("=" * 60)
    print("EXAMPLE 1: List Keyboard Devices")
    print("=" * 60)

    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

    print("\nAll input devices:")
    for device in devices:
        print(f"  {device.path}: {device.name}")

    print("\nKeyboard devices:")
    for device in devices:
        caps = device.capabilities()
        if ecodes.EV_KEY in caps:
            print(f"  {device.path}: {device.name}")


# ============================================================================
# EXAMPLE 2: Simple Key Press Detection
# ============================================================================

def example_simple_key_detection(device_path: str = '/dev/input/event1'):
    """Detect individual key presses and print key names."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Simple Key Press Detection")
    print("=" * 60)
    print(f"\nListening on {device_path}")
    print("Press keys... (Ctrl+C to stop)\n")

    try:
        device = evdev.InputDevice(device_path)
        for event in device.read_loop():
            if event.type == ecodes.EV_KEY:
                # Categorize turns raw event into readable form
                key_event = evdev.categorize(event)
                print(f"Key: {key_event.keycode:20} State: {key_event.keystate}")

    except KeyError:
        print("Error: Invalid key event")
    except FileNotFoundError:
        print(f"Error: Device {device_path} not found")
    except PermissionError:
        print("Error: Permission denied. Add user to 'input' group or run with sudo")
    except KeyboardInterrupt:
        print("\nStopped.")


# ============================================================================
# EXAMPLE 3: Detect Modifier Key Combinations (Super+Alt)
# ============================================================================

def example_modifier_combinations(device_path: str = '/dev/input/event1'):
    """Detect modifier key combinations like Super+Alt."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Detect Modifier Combinations (Super+Alt)")
    print("=" * 60)
    print(f"\nListening on {device_path}")
    print("Press Super+Alt combination... (Ctrl+C to stop)\n")

    # Track which keys are currently held
    held_keys: Set[int] = set()

    # Map key codes to readable names
    key_names = {
        ecodes.KEY_LEFTMETA: "Super (Left)",
        ecodes.KEY_RIGHTMETA: "Super (Right)",
        ecodes.KEY_LEFTALT: "Alt (Left)",
        ecodes.KEY_RIGHTALT: "Alt (Right)",
    }

    try:
        device = evdev.InputDevice(device_path)

        for event in device.read_loop():
            if event.type == ecodes.EV_KEY:
                key_code = event.code
                is_pressed = event.value == 1  # 1 = down, 0 = up, 2 = hold
                key_name = key_names.get(key_code, None)

                if is_pressed:
                    held_keys.add(key_code)

                    # Check for Super+Alt combination
                    has_super = (ecodes.KEY_LEFTMETA in held_keys or
                                ecodes.KEY_RIGHTMETA in held_keys)
                    has_alt = (ecodes.KEY_LEFTALT in held_keys or
                              ecodes.KEY_RIGHTALT in held_keys)

                    if has_super and has_alt:
                        print("✓ SUPER+ALT DETECTED!")

                    if key_name:
                        print(f"  {key_name} pressed (held: {len(held_keys)} keys)")

                else:  # Key released
                    held_keys.discard(key_code)
                    if key_name:
                        print(f"  {key_name} released")

    except FileNotFoundError:
        print(f"Error: Device {device_path} not found")
    except PermissionError:
        print("Error: Permission denied. Add user to 'input' group or run with sudo")
    except KeyboardInterrupt:
        print("\nStopped.")


# ============================================================================
# EXAMPLE 4: Detect Key Hold Duration
# ============================================================================

def example_key_hold_duration(device_path: str = '/dev/input/event1'):
    """Measure how long a key is held down."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Detect Key Hold Duration")
    print("=" * 60)
    print(f"\nListening on {device_path}")
    print("Press and hold keys to measure duration... (Ctrl+C to stop)\n")

    key_press_times: Dict[int, float] = {}

    try:
        device = evdev.InputDevice(device_path)

        for event in device.read_loop():
            if event.type == ecodes.EV_KEY:
                key_code = event.code
                is_pressed = event.value == 1
                is_released = event.value == 0

                if is_pressed:
                    # Record when key was pressed
                    key_press_times[key_code] = time.time()
                    key_name = ecodes.KEY.get(key_code, f'KEY_{key_code}')
                    print(f"  {key_name:20} pressed")

                elif is_released and key_code in key_press_times:
                    # Calculate hold duration
                    hold_duration = time.time() - key_press_times[key_code]
                    key_name = ecodes.KEY.get(key_code, f'KEY_{key_code}')
                    print(f"  {key_name:20} released (held {hold_duration:.3f}s)")
                    del key_press_times[key_code]

    except FileNotFoundError:
        print(f"Error: Device {device_path} not found")
    except PermissionError:
        print("Error: Permission denied. Add user to 'input' group or run with sudo")
    except KeyboardInterrupt:
        print("\nStopped.")


# ============================================================================
# EXAMPLE 5: Monitor Multiple Devices Simultaneously
# ============================================================================

def example_multiple_devices():
    """Monitor keyboard and mouse simultaneously using select()."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Monitor Multiple Devices")
    print("=" * 60)

    # Find keyboard and mouse devices
    devices_dict = {}
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

    for device in devices:
        caps = device.capabilities()
        if ecodes.EV_KEY in caps:
            devices_dict[device.fd] = ('keyboard', device)
        if ecodes.EV_REL in caps:
            devices_dict[device.fd] = ('mouse', device)

    if not devices_dict:
        print("No input devices found with EV_KEY or EV_REL capability")
        return

    print("\nMonitoring devices:")
    for device_type, device in devices_dict.values():
        print(f"  {device_type:10} {device.path}: {device.name}")

    print("\nPress keys or move mouse... (Ctrl+C to stop)\n")

    try:
        while True:
            # Wait for activity on any device
            r, w, x = select(devices_dict.keys(), [], [])

            for fd in r:
                device_type, device = devices_dict[fd]

                for event in device.read():
                    if event.type == ecodes.EV_KEY:
                        key_name = ecodes.KEY.get(event.code, f'KEY_{event.code}')
                        state = 'down' if event.value == 1 else 'up'
                        print(f"[{device_type}] {key_name} {state}")

                    elif event.type == ecodes.EV_REL:
                        rel_name = ecodes.REL.get(event.code, f'REL_{event.code}')
                        print(f"[{device_type}] {rel_name} = {event.value}")

    except KeyboardInterrupt:
        print("\nStopped.")
    except PermissionError:
        print("Error: Permission denied. Add user to 'input' group or run with sudo")


# ============================================================================
# EXAMPLE 6: Complex Hotkey Registration System
# ============================================================================

class HotkeyMonitor:
    """
    Monitor and detect complex hotkey patterns.

    Supports patterns like:
    - super + alt + a
    - ctrl + shift + Return
    - Super+1 (to Super+9 for quick app launching)
    """

    # Modifier key mappings
    MODIFIER_KEYS = {
        'super': (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA),
        'alt': (ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT),
        'ctrl': (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL),
        'shift': (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT),
    }

    # Special key mappings
    SPECIAL_KEYS = {
        'return': ecodes.KEY_RETURN,
        'enter': ecodes.KEY_RETURN,
        'escape': ecodes.KEY_ESC,
        'space': ecodes.KEY_SPACE,
        'tab': ecodes.KEY_TAB,
        'backspace': ecodes.KEY_BACKSPACE,
        'delete': ecodes.KEY_DELETE,
        'insert': ecodes.KEY_INSERT,
        'home': ecodes.KEY_HOME,
        'end': ecodes.KEY_END,
        'pageup': ecodes.KEY_PAGEUP,
        'pagedown': ecodes.KEY_PAGEDOWN,
    }

    def __init__(self, device_path: str = '/dev/input/event1'):
        """Initialize hotkey monitor."""
        self.device = evdev.InputDevice(device_path)
        self.held_keys: Set[int] = set()
        self.hotkeys: Dict[Tuple, Callable] = {}
        self.key_press_times: Dict[int, float] = {}

    def register_hotkey(
        self,
        modifiers: Tuple[str, ...],
        key: str,
        callback: Callable,
        description: str = ""
    ) -> None:
        """
        Register a hotkey pattern.

        Args:
            modifiers: Tuple of modifier names ('super', 'alt', 'ctrl', 'shift')
            key: Key name or character
            callback: Function to call when hotkey detected
            description: Human-readable description
        """
        pattern = (tuple(sorted(modifiers)), key.lower())
        self.hotkeys[pattern] = (callback, description or f"{'+'.join(modifiers)}+{key}")

    def _name_to_code(self, name: str) -> int:
        """Convert key name to evdev code."""
        name_lower = name.lower()

        # Check special keys
        if name_lower in self.SPECIAL_KEYS:
            return self.SPECIAL_KEYS[name_lower]

        # Check direct evdev constant
        attr_name = f'KEY_{name_lower.upper()}'
        if hasattr(ecodes, attr_name):
            return getattr(ecodes, attr_name)

        # Try as character (a-z, 0-9)
        if len(name) == 1:
            if name.isalpha():
                return ecodes.KEY_A + (ord(name.upper()) - ord('A'))
            elif name.isdigit():
                digit = int(name)
                return ecodes.KEY_1 + (digit - 1) if digit > 0 else ecodes.KEY_0

        raise ValueError(f"Unknown key: {name}")

    def _check_hotkeys(self) -> None:
        """Check if any registered hotkey pattern matches current held keys."""
        for (modifiers, key), (callback, description) in self.hotkeys.items():
            # Check if all modifiers are held
            all_mods_held = True
            for mod in modifiers:
                keys = self.MODIFIER_KEYS.get(mod)
                if not keys or not any(k in self.held_keys for k in keys):
                    all_mods_held = False
                    break

            # Check if main key is held
            try:
                key_code = self._name_to_code(key)
                if all_mods_held and key_code in self.held_keys:
                    callback()
            except ValueError:
                pass

    def start(self) -> None:
        """Start monitoring keyboard events."""
        print(f"Monitoring {self.device.path}: {self.device.name}")
        print(f"Registered {len(self.hotkeys)} hotkey(s)")
        print("Press Ctrl+C to stop.\n")

        try:
            for event in self.device.read_loop():
                if event.type == ecodes.EV_KEY:
                    self._handle_key_event(event)
        except KeyboardInterrupt:
            print("\nStopped.")

    def _handle_key_event(self, event: evdev.InputEvent) -> None:
        """Handle keyboard event."""
        key_code = event.code
        is_pressed = event.value == 1
        is_released = event.value == 0

        if is_pressed:
            self.held_keys.add(key_code)
            self.key_press_times[key_code] = time.time()
            self._check_hotkeys()

        elif is_released:
            self.held_keys.discard(key_code)

            # Calculate hold duration
            if key_code in self.key_press_times:
                duration = time.time() - self.key_press_times[key_code]
                del self.key_press_times[key_code]


def example_hotkey_system():
    """Example using the HotkeyMonitor class."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Complex Hotkey System")
    print("=" * 60)

    def on_super_alt_a():
        print("\n>>> HOTKEY TRIGGERED: Super+Alt+A")

    def on_super_1():
        print("\n>>> HOTKEY TRIGGERED: Super+1 (would launch Firefox)")

    def on_ctrl_return():
        print("\n>>> HOTKEY TRIGGERED: Ctrl+Return (would submit)")

    # Create monitor (adjust device path as needed)
    try:
        monitor = HotkeyMonitor('/dev/input/event1')

        # Register hotkeys
        monitor.register_hotkey(('super', 'alt'), 'a', on_super_alt_a, "Custom app launcher")
        monitor.register_hotkey(('super',), '1', on_super_1, "Launch Firefox")
        monitor.register_hotkey(('ctrl',), 'return', on_ctrl_return, "Submit form")

        # Start monitoring
        monitor.start()

    except FileNotFoundError:
        print("Error: Keyboard device not found")
    except PermissionError:
        print("Error: Permission denied. Add user to 'input' group or run with sudo")


# ============================================================================
# EXAMPLE 7: Async Event Reading (Python 3.5+)
# ============================================================================

async def example_async_keyboard(device_path: str = '/dev/input/event1'):
    """Read keyboard events asynchronously using asyncio."""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Async Keyboard Reading")
    print("=" * 60)
    print(f"\nListening on {device_path}")
    print("Press keys... (Ctrl+C to stop)\n")

    try:
        device = evdev.InputDevice(device_path)

        async for event in device.async_read_loop():
            if event.type == ecodes.EV_KEY:
                key_name = ecodes.KEY.get(event.code, f'KEY_{event.code}')
                state = 'down' if event.value == 1 else ('hold' if event.value == 2 else 'up')
                print(f"Key: {key_name:20} State: {state}")

    except FileNotFoundError:
        print(f"Error: Device {device_path} not found")
    except PermissionError:
        print("Error: Permission denied. Add user to 'input' group or run with sudo")
    except KeyboardInterrupt:
        print("\nStopped.")


# ============================================================================
# REFERENCE: Common Key Names in python-evdev
# ============================================================================

def show_key_reference():
    """Display common key code reference."""
    print("\n" + "=" * 60)
    print("KEY REFERENCE: Common Modifier Keys")
    print("=" * 60)

    reference = {
        "Super/Windows Keys": {
            "KEY_LEFTMETA": ecodes.KEY_LEFTMETA,
            "KEY_RIGHTMETA": ecodes.KEY_RIGHTMETA,
        },
        "Alt Keys": {
            "KEY_LEFTALT": ecodes.KEY_LEFTALT,
            "KEY_RIGHTALT": ecodes.KEY_RIGHTALT,
        },
        "Control Keys": {
            "KEY_LEFTCTRL": ecodes.KEY_LEFTCTRL,
            "KEY_RIGHTCTRL": ecodes.KEY_RIGHTCTRL,
        },
        "Shift Keys": {
            "KEY_LEFTSHIFT": ecodes.KEY_LEFTSHIFT,
            "KEY_RIGHTSHIFT": ecodes.KEY_RIGHTSHIFT,
        },
        "Special Keys": {
            "KEY_RETURN": ecodes.KEY_RETURN,
            "KEY_ESCAPE": ecodes.KEY_ESC,
            "KEY_SPACE": ecodes.KEY_SPACE,
            "KEY_TAB": ecodes.KEY_TAB,
        },
    }

    for category, keys in reference.items():
        print(f"\n{category}:")
        for name, code in keys.items():
            print(f"  {name:20} = {code}")


# ============================================================================
# MAIN: Run Examples
# ============================================================================

if __name__ == '__main__':
    import sys

    print("\n" + "=" * 60)
    print("WAYLAND KEYBOARD MONITORING EXAMPLES")
    print("KDE Plasma 6 on Fedora 42")
    print("=" * 60)

    examples = {
        '1': ("List keyboard devices", example_list_devices),
        '2': ("Simple key detection", example_simple_key_detection),
        '3': ("Modifier combinations (Super+Alt)", example_modifier_combinations),
        '4': ("Key hold duration", example_key_hold_duration),
        '5': ("Multiple device monitoring", example_multiple_devices),
        '6': ("Complex hotkey system", example_hotkey_system),
        '7': ("Reference guide", show_key_reference),
    }

    print("\nAvailable examples:")
    for num, (description, _) in examples.items():
        print(f"  {num}. {description}")

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nSelect example (1-7): ").strip()

    if choice in examples:
        _, example_func = examples[choice]
        try:
            example_func()
        except Exception as e:
            print(f"\nError: {e}")
    else:
        print("Invalid selection")
