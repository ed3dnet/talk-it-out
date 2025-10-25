# Keyboard Monitoring Libraries for Linux Wayland on KDE Plasma 6

**Platform**: KDE Plasma 6 on Fedora 42 (Wayland)
**Research Date**: 2025-10-25
**Status**: Current as of 2025

---

## Executive Summary

Wayland's security model fundamentally prevents traditional global keyboard monitoring that was possible in X11. This document provides working solutions and explains the constraints, alternatives, and key naming conventions for Python-based keyboard monitoring on Wayland/KDE Plasma 6.

---

## 1. pynput on Wayland: Status and Issues

### Current Status
**DOES NOT WORK** for keyboard monitoring on Wayland as of February 2025.

### Why It Fails
- pynput only supports X11 on Linux via X11 core API
- A uinput backend was partially implemented but remains broken for keyboard listening
- Xwayland emulator provides only limited functionality (only receives events from Xwayland clients)

### KDE Eco Season 2024 Attempt
The KDE Eco project (Season of KDE 2024) completed a pynput backend for Wayland using libevdev, but:
- It was experimental and not fully integrated into pynput upstream
- Keyboard listener still doesn't work reliably on Wayland even with uinput
- libinput processing causes issues with simulated events

### Recommendation
**Do not use pynput for Wayland keyboard monitoring**. Consider alternatives below.

---

## 2. Wayland Security Model: Why Traditional Monitoring Fails

Wayland introduced security measures that prevent:
- **Global key logging**: No application can snoop on input from other programs
- **Input injection**: Applications cannot generate events that appear to come from the user
- **Exclusive input capture**: Applications cannot intercept all input events

### Architecture Stack
```
Kernel → libevdev → libinput → Wayland Compositor → Wayland Client
```

The compositor controls input distribution, preventing unprivileged applications from accessing all keyboard events.

---

## 3. Working Alternatives for Global Hotkey Detection

### 3.1 **KGlobalAccel via DBus (KDE Plasma Native)**

**Best Option for KDE Plasma 6 Wayland**

**Architecture**:
- KWin (KDE's Wayland compositor) integrates KGlobalAccel internally
- Global shortcuts are handled by KWin, not a separate daemon
- Applications register shortcuts via DBus service `org.kde.kglobalaccel`

**Key Implementation Details**:
- KGlobalAccel uses a DBus interface for registration and invocation
- KWin must start the KGlobalAccel service before other processes
- Security: KWin validates all shortcuts before delivery

**Python Implementation**:

```python
# Using dbus-next library (recommended modern DBus binding for Python)
from dbus_next.aio import MessageBus
import asyncio

async def invoke_shortcut():
    bus = await MessageBus().connect()

    # Invoke existing KDE shortcut
    introspection = await bus.introspect('org.kde.kglobalaccel', '/component/krunner')
    proxy = bus.get_proxy('org.kde.kglobalaccel', '/component/krunner', introspection)

    # Call invokeShortcut method
    result = await proxy.call_org_kde_kglobalaccel_Component_invokeShortcut('run command')
    return result

asyncio.run(invoke_shortcut())
```

**Limitations**:
- Only works with registered global shortcuts
- Cannot create arbitrary global shortcuts from Python
- Specific to KDE Plasma
- Cannot detect key hold/release at the global level

**Alternative DBus Libraries for Python**:
- `dbus-next` (recommended) - async/await support, modern Python
- `pydbus` - simpler API, synchronous
- `dbus-python` - mature but discouraged for threaded applications
- `python-sdbus` - modern, type hints, asyncio support

### 3.2 **python-evdev (Kernel Input Events)**

**Best for Low-Level Monitoring on Wayland**

Works because it reads from `/dev/input/eventX` directly below the graphics stack.

**Architecture**:
```
Kernel evdev → python-evdev → Your Python Code
(Wayland compositor is bypassed)
```

**Requirements**:
- Run as root OR
- User must have read/write permissions to `/dev/input/eventX` and `/dev/uinput`
- Typical group: `input` (add user: `usermod -a -G input $USER`)

**Key Features**:
- Supports all keys, modifiers, and mouse events
- Can detect key press (value=1), hold (value=2), and release (value=0)
- Supports multiple devices simultaneously
- Works on both X11 and Wayland

**Installation**:
```bash
pip install evdev
# Grant permissions (run once)
sudo usermod -a -G input $USER
# Logout and login for group membership to take effect
```

**Python Implementation - Single Keyboard Monitor**:

```python
#!/usr/bin/env python3
import evdev
from evdev import ecodes

# List available devices
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
    print(f"{device.path}: {device.name}")

# Monitor keyboard device
keyboard = evdev.InputDevice('/dev/input/event1')  # Adjust path as needed

print("Listening for keyboard events. Press Ctrl+C to stop.")
for event in keyboard.read_loop():
    if event.type == ecodes.EV_KEY:
        key_event = evdev.categorize(event)
        print(f"Key: {key_event.keycode} ({key_event.keystate})")
        print(f"  Code: {event.code}, Value: {event.value}")
```

**Key Naming Conventions in python-evdev**:

Access via `evdev.ecodes.KEY_*` format:

```python
from evdev import ecodes

# Modifier keys (Super/Windows key)
KEY_LEFTMETA = 125      # Left Windows/Super key
KEY_RIGHTMETA = 126     # Right Windows/Super key

# Alt keys
KEY_LEFTALT = 56        # Left Alt key
KEY_RIGHTALT = 100      # Right Alt key

# Control keys
KEY_LEFTCTRL = 29       # Left Control
KEY_RIGHTCTRL = 97      # Right Control

# Shift keys
KEY_LEFTSHIFT = 42      # Left Shift
KEY_RIGHTSHIFT = 54     # Right Shift

# Examples of other keys
KEY_A = 30
KEY_SPACE = 57
KEY_RETURN = 28
KEY_ENTER = 28
KEY_ESCAPE = 1
```

**Detecting Super+Alt Combination**:

```python
#!/usr/bin/env python3
import evdev
from evdev import ecodes
from select import select

# Track held keys
held_keys = set()

keyboard = evdev.InputDevice('/dev/input/event1')

print("Press Super+Alt to trigger. Press Ctrl+C to stop.")
for event in keyboard.read_loop():
    if event.type == ecodes.EV_KEY:
        key_event = evdev.categorize(event)

        if key_event.keystate == 1:  # Key down (pressed)
            held_keys.add(event.code)

            # Check for Super+Alt combination
            has_super = ecodes.KEY_LEFTMETA in held_keys or ecodes.KEY_RIGHTMETA in held_keys
            has_alt = ecodes.KEY_LEFTALT in held_keys or ecodes.KEY_RIGHTALT in held_keys

            if has_super and has_alt:
                print("Super+Alt detected!")

        elif key_event.keystate == 0:  # Key up (released)
            held_keys.discard(event.code)

        elif key_event.keystate == 2:  # Key held
            pass  # Autorepeat
```

**Detecting Key Hold Duration**:

```python
import time

key_press_times = {}

for event in keyboard.read_loop():
    if event.type == ecodes.EV_KEY:
        key_event = evdev.categorize(event)
        key_code = event.code

        if key_event.keystate == 1:  # Pressed
            key_press_times[key_code] = time.time()

        elif key_event.keystate == 0:  # Released
            if key_code in key_press_times:
                hold_duration = time.time() - key_press_times[key_code]
                print(f"Key held for {hold_duration:.3f} seconds")
                del key_press_times[key_code]
```

**Advantages**:
- Works on Wayland (reads from kernel directly)
- No daemon required
- Supports all keyboard features
- Well-maintained library

**Disadvantages**:
- Requires elevated permissions or group membership
- Less convenient for application-level shortcuts
- No integration with KDE's shortcut system
- Need to handle multiple devices manually

### 3.3 **swhkd (Rust-Based Daemon)**

**Good for Wayland-Specific Hotkey Mapping**

A modern hotkey daemon written in Rust designed specifically for Wayland.

**Features**:
- Works on Wayland, X11, and TTY
- Drop-in replacement for sxhkd config format
- Client-server architecture with privilege separation
- Server-side validation prevents unauthorized keystrokes

**Installation**:
```bash
# Available in AUR or GitHub releases
# On Fedora, may need to build from source
git clone https://github.com/waycrate/swhkd.git
cd swhkd
cargo build --release
sudo ./target/release/swhkd
```

**Configuration** (`~/.config/swhkd/swhkdrc`):
```bash
# Example config (sxhkd-compatible format)
super + alt
    notify-send "Super+Alt pressed"

super + 1
    firefox

alt + e
    emacsclient -c
```

**Key Names** (Compatible with sxhkd):
- `super` / `Super_L` / `Super_R` - Windows/Super key
- `alt` / `Alt_L` / `Alt_R` - Alt key
- `ctrl` / `Control_L` / `Control_R` - Control key
- `shift` / `Shift_L` / `Shift_R` - Shift key
- `a-z`, `0-9` - Letter and number keys
- `Return`, `BackSpace`, `Tab`, `Escape`, `space`
- `F1-F12` - Function keys
- `plus`, `minus`, `equal`, `bracketleft`, etc.

**Advantages**:
- Native Wayland support (not X11 emulation)
- Modern, actively maintained
- No Python required (Rust daemon)
- Configuration-based, not code-based
- Can handle complex key combinations

**Disadvantages**:
- Not a Python library (daemon runs separately)
- Requires separate installation
- Still needs root/privileged access
- Config file format, not programmatic

**Interaction from Python**:
Use system commands to send signals or socket communication:
```python
import subprocess
import os
import signal

# Reload swhkd config
os.kill(swhkd_pid, signal.SIGHUP)

# Or use dbus if swhkd implements it
```

### 3.4 **wayremap (Python Key Remapper)**

**Python-Based Dynamic Key Remapping**

A Python tool specifically designed for Wayland keyboard remapping and monitoring.

**Installation**:
```bash
pip install wayremap
```

**Features**:
- Per-application key remapping
- Supports Emacs-like key bindings
- Works on both X11 and Wayland
- Pure Python implementation

**Limitations**:
- Requires root/elevated permissions
- Primarily for remapping, not monitoring
- Uses same evdev backend as python-evdev
- Less mature than other options

**Not Recommended** for your use case - python-evdev provides the same capabilities with better documentation.

---

## 4. Comparison Matrix

| Feature | pynput | python-evdev | KGlobalAccel/DBus | swhkd | wayremap |
|---------|--------|--------------|-------------------|-------|----------|
| **Wayland Support** | ❌ No | ✅ Yes | ✅ Yes (KDE only) | ✅ Yes | ✅ Yes |
| **Key Detection** | ❌ Broken | ✅ Yes | ❌ No* | ✅ Yes | ✅ Yes |
| **Hold Detection** | N/A | ✅ Yes | N/A | Limited** | ✅ Yes |
| **Super+Alt Combo** | N/A | ✅ Yes | N/A | ✅ Yes | ✅ Yes |
| **Python Library** | ✅ Yes | ✅ Yes | DBus only | No | ✅ Yes |
| **Requires Root** | ❌ No | ⚠️ Yes*** | ❌ No | ✅ Yes | ✅ Yes |
| **KDE Integration** | N/A | No | ✅ Yes | Limited | No |
| **Maturity** | High | High | Stable | Medium | Low |
| **Active Maintenance** | Medium | High | KDE/Stable | High | Medium |

\* KGlobalAccel is for invoking shortcuts, not detecting keypresses
\*\* swhkd can detect combos but not arbitrary hold times
\*\*\* Can be avoided with group membership or udev rules

---

## 5. Key Naming Convention Reference

### python-evdev Constants

**Import**:
```python
from evdev import ecodes
```

**Modifier Keys**:
```
KEY_LEFTCTRL = 29       # Left Ctrl
KEY_RIGHTCTRL = 97      # Right Ctrl
KEY_LEFTSHIFT = 42      # Left Shift
KEY_RIGHTSHIFT = 54     # Right Shift
KEY_LEFTALT = 56        # Left Alt
KEY_RIGHTALT = 100      # Right Alt
KEY_LEFTMETA = 125      # Left Super/Windows
KEY_RIGHTMETA = 126     # Right Super/Windows
```

**Letter Keys**:
```
KEY_A = 30, KEY_B = 48, KEY_C = 46, ... KEY_Z = 44
# etc. (offset 30 for KEY_A)
```

**Number Keys**:
```
KEY_1 = 2, KEY_2 = 3, ... KEY_0 = 11
```

**Special Keys**:
```
KEY_SPACE = 57
KEY_RETURN = 28 (also called KEY_ENTER)
KEY_ESCAPE = 1
KEY_TAB = 15
KEY_BACKSPACE = 14
KEY_DELETE = 111
KEY_HOME = 102
KEY_END = 107
KEY_PAGEUP = 104
KEY_PAGEDOWN = 109
```

**Function Keys**:
```
KEY_F1 = 59, KEY_F2 = 60, ... KEY_F12 = 88
```

**Arrow Keys**:
```
KEY_LEFT = 105
KEY_RIGHT = 106
KEY_UP = 103
KEY_DOWN = 108
```

**Media Keys**:
```
KEY_MUTE = 113
KEY_VOLUMEDOWN = 114
KEY_VOLUMEUP = 115
KEY_PLAYCD = 200
KEY_NEXTSONG = 163
KEY_PREVIOUSSONG = 165
```

**Accessing Dynamically**:
```python
# Forward mapping (name to code)
code = ecodes.KEY_A  # 30

# Reverse mapping (code to name)
name = ecodes.KEY[30]  # 'KEY_A'

# Get by string name
code = ecodes.ecodes['KEY_A']  # 30

# Get by type then code
name = ecodes.bytype[ecodes.EV_KEY][30]  # 'KEY_A'

# List all key codes
for name in dir(ecodes):
    if name.startswith('KEY_'):
        print(f"{name}: {getattr(ecodes, name)}")
```

### swhkd Key Names

Different format from evdev (more human-readable):
```
super / Super_L / Super_R      # Windows/Super key
alt / Alt_L / Alt_R            # Alt key
ctrl / Control_L / Control_R   # Control key
shift / Shift_L / Shift_R      # Shift key
a-z, 0-9                       # Letter and number keys
Return, BackSpace, Tab         # Special keys
Escape, space                  # More special keys
F1-F12                         # Function keys
Left, Right, Up, Down          # Arrow keys
```

### Key Event Values

In python-evdev, the `value` field indicates:
```
0 = Key up (released)
1 = Key down (pressed)
2 = Key hold (autorepeat)
```

---

## 6. Recommended Solutions by Use Case

### Use Case A: "I want to detect when the user presses Super+Alt globally"

**Recommendation**: **python-evdev**

```python
#!/usr/bin/env python3
import evdev
from evdev import ecodes

held_keys = set()
keyboard = evdev.InputDevice('/dev/input/event1')

for event in keyboard.read_loop():
    if event.type == ecodes.EV_KEY:
        if event.value == 1:  # Key pressed
            held_keys.add(event.code)
            if (ecodes.KEY_LEFTMETA in held_keys or ecodes.KEY_RIGHTMETA in held_keys) and \
               (ecodes.KEY_LEFTALT in held_keys or ecodes.KEY_RIGHTALT in held_keys):
                print("Super+Alt detected!")
        elif event.value == 0:  # Key released
            held_keys.discard(event.code)
```

### Use Case B: "I want to register a global keyboard shortcut that integrates with KDE"

**Recommendation**: **KGlobalAccel via DBus**

```python
#!/usr/bin/env python3
from dbus_next.aio import MessageBus
import asyncio

async def register_and_invoke():
    bus = await MessageBus().connect()

    # Invoke a registered KDE shortcut
    proxy = bus.get_proxy('org.kde.kglobalaccel', '/component/krunner')
    await proxy.call_org_kde_kglobalaccel_Component_invokeShortcut('run command')

asyncio.run(register_and_invoke())
```

### Use Case C: "I want a complete hotkey daemon for my desktop"

**Recommendation**: **swhkd** (Rust daemon with config file)

Create `~/.config/swhkd/swhkdrc`:
```bash
super + alt
    notify-send "Hotkey triggered!"

super + 1
    firefox
```

Then run:
```bash
sudo swhkd
```

### Use Case D: "I need to detect key hold duration and complex patterns"

**Recommendation**: **python-evdev with custom state machine**

See "Detecting Key Hold Duration" section above in 3.2.

---

## 7. Practical Implementation Example

Here's a complete working solution combining multiple approaches:

```python
#!/usr/bin/env python3
"""
Keyboard monitoring on Wayland using python-evdev.
Detects global hotkey patterns and integrates with KDE.

Requirements:
    pip install evdev
    User must be in 'input' group: usermod -a -G input $USER
"""

import evdev
from evdev import ecodes
from select import select
import time
import asyncio
from typing import Callable, Set, Tuple


class WaylandHotkeyMonitor:
    """Monitor keyboard and detect hotkey patterns on Wayland."""

    # Key name mappings
    MODIFIER_KEYS = {
        'super': (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA),
        'alt': (ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT),
        'ctrl': (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL),
        'shift': (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT),
    }

    def __init__(self, device_path: str):
        """
        Initialize keyboard monitor.

        Args:
            device_path: Path to keyboard device (e.g., '/dev/input/event1')
        """
        self.device = evdev.InputDevice(device_path)
        self.held_keys: Set[int] = set()
        self.key_press_times: dict = {}
        self.hotkey_callbacks: dict = {}

    def register_hotkey(
        self,
        modifiers: Tuple[str, ...],
        key: str,
        callback: Callable
    ) -> None:
        """
        Register a hotkey pattern.

        Args:
            modifiers: Tuple of modifier names ('super', 'alt', 'ctrl', 'shift')
            key: Key name (e.g., 'a', 'Return', 'F1')
            callback: Function to call when hotkey is detected
        """
        pattern = (modifiers, key)
        self.hotkey_callbacks[pattern] = callback

    def _key_name_to_code(self, name: str) -> int:
        """Convert key name to evdev code."""
        # Try direct mapping
        attr_name = f'KEY_{name.upper()}'
        if hasattr(ecodes, attr_name):
            return getattr(ecodes, attr_name)

        # Try lowercase
        if hasattr(ecodes, name):
            return getattr(ecodes, name)

        raise ValueError(f"Unknown key: {name}")

    def _check_hotkeys(self) -> None:
        """Check if any registered hotkey is active."""
        for (modifiers, key), callback in self.hotkey_callbacks.items():
            # Check modifiers
            all_mods_held = True
            for mod in modifiers:
                keys = self.MODIFIER_KEYS.get(mod)
                if not keys or not any(k in self.held_keys for k in keys):
                    all_mods_held = False
                    break

            # Check main key
            key_code = self._key_name_to_code(key)
            if all_mods_held and key_code in self.held_keys:
                callback()

    def start(self) -> None:
        """Start monitoring keyboard events."""
        print(f"Monitoring {self.device.path}: {self.device.name}")
        print("Press Ctrl+C to stop.")

        try:
            for event in self.device.read_loop():
                if event.type == ecodes.EV_KEY:
                    self._handle_key_event(event)
        except KeyboardInterrupt:
            print("\nStopped.")

    def _handle_key_event(self, event: evdev.InputEvent) -> None:
        """Handle a keyboard event."""
        key_code = event.code
        value = event.value  # 0=up, 1=down, 2=hold

        if value == 1:  # Key pressed
            self.held_keys.add(key_code)
            self.key_press_times[key_code] = time.time()
            self._check_hotkeys()

        elif value == 0:  # Key released
            if key_code in self.held_keys:
                self.held_keys.discard(key_code)

            # Calculate hold duration
            if key_code in self.key_press_times:
                duration = time.time() - self.key_press_times[key_code]
                key_name = ecodes.KEY.get(key_code, f'KEY_{key_code}')
                # print(f"Key {key_name} held for {duration:.3f}s")
                del self.key_press_times[key_code]


def main():
    """Example usage."""
    # Find keyboard device
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    keyboard = None

    for device in devices:
        if 'Keyboard' in device.name or 'keyboard' in device.name:
            keyboard = device
            break

    if not keyboard:
        # Fallback to first event device with KEY capability
        for device in devices:
            caps = device.capabilities()
            if ecodes.EV_KEY in caps:
                keyboard = device
                break

    if not keyboard:
        print("No keyboard device found!")
        print("Available devices:")
        for device in devices:
            print(f"  {device.path}: {device.name}")
        return

    # Initialize monitor
    monitor = WaylandHotkeyMonitor(keyboard.path)

    # Register hotkeys
    monitor.register_hotkey(('super', 'alt'), 'a', lambda: print("Super+Alt+A pressed!"))
    monitor.register_hotkey(('super',), '1', lambda: print("Super+1 pressed!"))
    monitor.register_hotkey(('ctrl',), 'Return', lambda: print("Ctrl+Return pressed!"))

    # Start monitoring
    monitor.start()


if __name__ == '__main__':
    main()
```

---

## 8. Installation & Setup for Fedora 42

### Install python-evdev

```bash
# Install library
pip install evdev

# Add user to input group
sudo usermod -a -G input $USER

# Logout and login for group membership to take effect
# Or test with sudo
```

### Verify Keyboard Device

```bash
# List all input devices
python -m evdev.evtest

# Or manually find keyboard
ls -la /dev/input/event*
cat /proc/bus/input/devices | grep -i keyboard
```

### Run as Root (Alternative to Group Membership)

```bash
# Create service that runs with sudo
sudo python3 script.py
```

### KGlobalAccel/DBus Setup

```bash
# Install dbus-next for DBus communication
pip install dbus-next

# Verify kglobalaccel is running
qdbus org.kde.kglobalaccel /component/krunner org.kde.kglobalaccel.Component.invokeShortcut "run command"
```

---

## 9. Known Limitations and Caveats

### KGlobalAccel on Wayland
- **Cannot detect keypresses** - only invoke existing registered shortcuts
- **Security by design** - applications cannot register arbitrary global shortcuts
- **KDE-specific** - only works on KDE Plasma

### python-evdev on Wayland
- **Requires root or group membership** - needed for `/dev/input` access
- **All input captured** - will capture keys from all applications
- **No X11 modifiers** - uses evdev constants, not XKB names
- **Mouse acceleration** - pointer movement affected by libinput configuration

### swhkd on Wayland
- **Requires installation** - not pure Python
- **Privilege separation** - daemon must run as root
- **Config file format** - not programmatic control

### General Wayland Constraints
- **No global key logger possible** - fundamental design decision
- **Compositor mediation** - input distribution controlled by KWin/compositor
- **No input injection** - cannot simulate keystrokes appearing from user
- **Incomplete support** - many traditional hotkey daemons still not fully ported

---

## 10. Testing and Verification

### Test Keyboard Device Detection

```bash
python3 -c "
import evdev
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
    print(f'{device.path}: {device.name}')
"
```

### Test Key Event Reading

```bash
python3 -c "
import evdev
from evdev import ecodes

device = evdev.InputDevice('/dev/input/event1')  # Adjust path
print('Press keys... (Ctrl+C to stop)')
for event in device.read_loop():
    if event.type == ecodes.EV_KEY:
        print(f'Key code {event.code}, value {event.value}')
" 2>/dev/null || echo "Requires permissions - run with sudo or add user to input group"
```

### Test DBus KGlobalAccel

```bash
# Test invoking a KDE shortcut
qdbus org.kde.kglobalaccel /component/krunner \
    org.kde.kglobalaccel.Component.invokeShortcut 'run command'
```

---

## 11. Reference Links

### Official Documentation
- [python-evdev Documentation](https://python-evdev.readthedocs.io/)
- [Linux Input Event Codes](https://docs.kernel.org/input/event-codes.html)
- [KDE KGlobalAccel Framework](https://api.kde.org/frameworks-api/kglobalaccel/)
- [Wayland Security Model](https://wayland.freedesktop.org/security.html)

### Community Projects
- [swhkd GitHub](https://github.com/waycrate/swhkd) - Wayland hotkey daemon
- [wayremap GitHub](https://github.com/acro5piano/wayremap) - Python key remapper
- [KDE Eco Project](https://eco.kde.org/) - KDE's sustainability initiatives

### Related Articles
- [Global Shortcut Handling in Plasma Wayland](https://blog.martin-graesslin.com/blog/2015/06/global-shortcut-handling-in-a-plasma-wayland-session/) - Martin Gräßlin's detailed explanation
- [Making Way for Wayland in KdeEcoTest](https://eco.kde.org/blog/2024-02-20-sok24-wayland_support_kdeecotest/) - KDE Eco Season 2024 implementation
- [Wayland Input Security](https://lwn.net/Articles/589147/) - LWN article on security

### Bug Trackers
- [pynput Issue #628 - Keyboard listener doesn't work on Wayland](https://github.com/moses-palmer/pynput/issues/628)
- [KDE Bug #484063 - No global shortcuts working in Plasma 6](https://bugs.kde.org/show_bug.cgi?id=484063)

---

## Summary: What Actually Works on KDE Plasma 6 Wayland (Fedora 42)

| Solution | Works? | Best For | Complexity |
|----------|--------|----------|-----------|
| **python-evdev** | ✅ Yes | Detecting all keyboard events globally | Medium |
| **KGlobalAccel/DBus** | ✅ Yes (limited) | Invoking registered KDE shortcuts only | Low |
| **swhkd** | ✅ Yes | Full hotkey daemon with config file | Medium |
| **pynput** | ❌ No | Don't use on Wayland | N/A |

**Bottom Line**: Use **python-evdev** for flexibility or **swhkd** for a complete daemon solution.
