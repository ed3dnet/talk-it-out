# Quick Start: Keyboard Monitoring on Wayland

**TL;DR**: Use `python-evdev` for keyboard monitoring on Wayland. It works because it reads directly from the kernel's input device layer, bypassing the compositor.

---

## 1-Minute Setup

### Install
```bash
pip install evdev
sudo usermod -a -G input $USER
# Logout and login to apply group membership
```

### Verify It Works
```bash
python3 -c "
import evdev
devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
for d in devices:
    print(f'{d.path}: {d.name}')
"
```

---

## Minimal Working Example

### Detect Any Key Press
```python
import evdev
from evdev import ecodes

device = evdev.InputDevice('/dev/input/event1')  # Adjust path

for event in device.read_loop():
    if event.type == ecodes.EV_KEY:
        key_name = ecodes.KEY.get(event.code, f'KEY_{event.code}')
        state = 'down' if event.value == 1 else 'up'
        print(f"{key_name} {state}")
```

### Detect Super+Alt
```python
import evdev
from evdev import ecodes

held_keys = set()
device = evdev.InputDevice('/dev/input/event1')

for event in device.read_loop():
    if event.type == ecodes.EV_KEY:
        if event.value == 1:  # Key pressed
            held_keys.add(event.code)
            if (ecodes.KEY_LEFTMETA in held_keys or ecodes.KEY_RIGHTMETA in held_keys) and \
               (ecodes.KEY_LEFTALT in held_keys or ecodes.KEY_RIGHTALT in held_keys):
                print("SUPER+ALT DETECTED!")
        else:  # Key released
            held_keys.discard(event.code)
```

---

## Key Names You Need

**Modifiers**:
- `KEY_LEFTMETA` / `KEY_RIGHTMETA` = Super/Windows key
- `KEY_LEFTALT` / `KEY_RIGHTALT` = Alt key
- `KEY_LEFTCTRL` / `KEY_RIGHTCTRL` = Control key
- `KEY_LEFTSHIFT` / `KEY_RIGHTSHIFT` = Shift key

**Letters/Numbers**:
- `KEY_A` through `KEY_Z` (values 30-54)
- `KEY_1` through `KEY_0` (values 2-11)

**Special Keys**:
- `KEY_SPACE` = 57
- `KEY_RETURN` / `KEY_ENTER` = 28
- `KEY_ESCAPE` = 1
- `KEY_TAB` = 15
- `KEY_BACKSPACE` = 14

**Key Event Values**:
- `0` = Key up (released)
- `1` = Key down (pressed)
- `2` = Key hold (autorepeat)

---

## Find Your Keyboard Device

```bash
# Method 1: List all devices
python -m evdev.evtest

# Method 2: List with grep
grep -i keyboard /proc/bus/input/devices

# Method 3: Check permissions
ls -la /dev/input/event*
```

---

## Why This Works on Wayland

```
Keyboard → Linux Kernel → /dev/input/eventX → python-evdev → Your Code

            (Wayland compositor never sees it)
```

The key insight: Wayland only protects input flowing through the compositor. Reading directly from `/dev/input` bypasses it entirely.

---

## Common Issues and Fixes

### "Permission denied" reading `/dev/input/event*`
```bash
# Solution 1: Add user to input group
sudo usermod -a -G input $USER
# Then logout and login

# Solution 2: Run with sudo
sudo python3 your_script.py
```

### "Device not found" / wrong event path
```bash
# Find your keyboard
python -m evdev.evtest
# Look for "Keyboard" in the output
```

### "No events captured"
- Make sure you're using the right device (run evtest to verify)
- Some keyboards may be `/dev/input/event2` or higher
- Check file permissions with `ls -la /dev/input/`

---

## When NOT to Use python-evdev

- **Want KDE integration**: Use KGlobalAccel via DBus instead
- **Need system-wide daemon**: Use swhkd (Rust tool)
- **Want X11-style shortcuts**: Those don't work on Wayland for security reasons
- **On X11**: pynput is better for X11

---

## Comparison: What Works on Wayland

| Tool | Works | Best For | Effort |
|------|-------|----------|--------|
| **python-evdev** | ✅ Yes | Detecting all keyboard events | Low |
| **KGlobalAccel/DBus** | ✅ Limited | Invoking registered KDE shortcuts | Medium |
| **swhkd** | ✅ Yes | Full hotkey daemon | High |
| **pynput** | ❌ No | - | Don't use |

---

## Full Documentation

See `/home/ed/Development/ed3dnet/talk-it-out/docs/wayland_keyboard_monitoring_research.md` for:
- Detailed architecture explanations
- Wayland security model deep-dive
- KGlobalAccel/DBus integration
- swhkd configuration
- Complete reference tables
- Troubleshooting guide

## Code Examples

Run `/home/ed/Development/ed3dnet/talk-it-out/docs/wayland_keyboard_examples.py` for:
- Simple key detection
- Modifier combinations
- Hold duration measurement
- Multiple device monitoring
- Complete hotkey system
- Reference data

---

## Platform Info

**Tested on**:
- KDE Plasma 6.3.4
- Fedora 42
- Linux 6.17.4 (Wayland)

**Should work on**:
- Any Wayland compositor (GNOME, Sway, etc.)
- Any Linux distribution
- Python 3.6+

---

## Need More Help?

1. Check full research document: `wayland_keyboard_monitoring_research.md`
2. Run example code: `python3 wayland_keyboard_examples.py`
3. Test with evtest: `python -m evdev.evtest`
4. Check system info: `echo $XDG_SESSION_TYPE` (should be "wayland")
