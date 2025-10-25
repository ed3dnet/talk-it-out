# Key Names Reference: python-evdev on Wayland

This is a complete reference of key names and codes for python-evdev.

All values are from the Linux kernel's `input-event-codes.h`.

---

## Accessing Key Names in Python

```python
from evdev import ecodes

# Get code from name
code = ecodes.KEY_A  # 30

# Get name from code
name = ecodes.KEY[30]  # 'KEY_A'

# Get by string
code = ecodes.ecodes['KEY_A']  # 30

# List all keys
for key in sorted(dir(ecodes)):
    if key.startswith('KEY_'):
        code = getattr(ecodes, key)
        print(f"{key:30} = {code}")
```

---

## Modifier Keys (Most Important for Hotkeys)

| Name | Code | Usage |
|------|------|-------|
| `KEY_LEFTCTRL` | 29 | Left Ctrl key |
| `KEY_RIGHTCTRL` | 97 | Right Ctrl key |
| `KEY_LEFTSHIFT` | 42 | Left Shift key |
| `KEY_RIGHTSHIFT` | 54 | Right Shift key |
| `KEY_LEFTALT` | 56 | Left Alt key |
| `KEY_RIGHTALT` | 100 | Right Alt key |
| `KEY_LEFTMETA` | 125 | Left Windows/Super key |
| `KEY_RIGHTMETA` | 126 | Right Windows/Super key |
| `KEY_CAPSLOCK` | 58 | Caps Lock |
| `KEY_NUMLOCK` | 69 | Num Lock |
| `KEY_SCROLLLOCK` | 70 | Scroll Lock |

**Critical**: On Wayland, modifiers are detected as:
- `KEY_LEFTMETA` or `KEY_RIGHTMETA` for Super/Windows key
- NOT "Super" or "Windows" - those are human-readable names only

---

## Letter Keys (KEY_A through KEY_Z)

| Letter | Code | evdev Name |
|--------|------|-----------|
| A | 30 | `KEY_A` |
| B | 48 | `KEY_B` |
| C | 46 | `KEY_C` |
| D | 32 | `KEY_D` |
| E | 18 | `KEY_E` |
| F | 33 | `KEY_F` |
| G | 34 | `KEY_G` |
| H | 35 | `KEY_H` |
| I | 23 | `KEY_I` |
| J | 36 | `KEY_J` |
| K | 37 | `KEY_K` |
| L | 38 | `KEY_L` |
| M | 50 | `KEY_M` |
| N | 49 | `KEY_N` |
| O | 24 | `KEY_O` |
| P | 25 | `KEY_P` |
| Q | 16 | `KEY_Q` |
| R | 19 | `KEY_R` |
| S | 31 | `KEY_S` |
| T | 20 | `KEY_T` |
| U | 22 | `KEY_U` |
| V | 47 | `KEY_V` |
| W | 17 | `KEY_W` |
| X | 45 | `KEY_X` |
| Y | 21 | `KEY_Y` |
| Z | 44 | `KEY_Z` |

**Pattern**: `KEY_A` starts at 30. So `KEY_A + 1 = 31 (KEY_S)`, etc.

---

## Number Keys (KEY_1 through KEY_0)

| Number | Code | evdev Name |
|--------|------|-----------|
| 1 | 2 | `KEY_1` |
| 2 | 3 | `KEY_2` |
| 3 | 4 | `KEY_3` |
| 4 | 5 | `KEY_4` |
| 5 | 6 | `KEY_5` |
| 6 | 7 | `KEY_6` |
| 7 | 8 | `KEY_7` |
| 8 | 9 | `KEY_8` |
| 9 | 10 | `KEY_9` |
| 0 | 11 | `KEY_0` |

**Note**: `KEY_1` starts at 2, not 1. Keys 0-1 are reserved.

---

## Numpad Keys

| Key | Code | evdev Name |
|-----|------|-----------|
| Numpad 0 | 82 | `KEY_KP0` |
| Numpad 1 | 79 | `KEY_KP1` |
| Numpad 2 | 80 | `KEY_KP2` |
| Numpad 3 | 81 | `KEY_KP3` |
| Numpad 4 | 75 | `KEY_KP4` |
| Numpad 5 | 76 | `KEY_KP5` |
| Numpad 6 | 77 | `KEY_KP6` |
| Numpad 7 | 71 | `KEY_KP7` |
| Numpad 8 | 72 | `KEY_KP8` |
| Numpad 9 | 73 | `KEY_KP9` |
| Numpad / | 98 | `KEY_KPSLASH` |
| Numpad * | 55 | `KEY_KPASTERISK` |
| Numpad - | 74 | `KEY_KPMINUS` |
| Numpad + | 78 | `KEY_KPPLUS` |
| Numpad . | 83 | `KEY_KPDOT` |
| Numpad Enter | 96 | `KEY_KPENTER` |

---

## Special Keys (Navigation & Control)

| Key | Code | evdev Name |
|-----|------|-----------|
| Enter/Return | 28 | `KEY_RETURN` or `KEY_ENTER` |
| Escape | 1 | `KEY_ESC` |
| Backspace | 14 | `KEY_BACKSPACE` |
| Tab | 15 | `KEY_TAB` |
| Space | 57 | `KEY_SPACE` |
| Minus/Hyphen | 12 | `KEY_MINUS` |
| Equals | 13 | `KEY_EQUAL` |
| Delete | 111 | `KEY_DELETE` |
| Insert | 110 | `KEY_INSERT` |
| Home | 102 | `KEY_HOME` |
| End | 107 | `KEY_END` |
| Page Up | 104 | `KEY_PAGEUP` |
| Page Down | 109 | `KEY_PAGEDOWN` |
| Print Screen | 99 | `KEY_SYSRQ` |
| Pause | 119 | `KEY_PAUSE` |
| Break | 119 | `KEY_BREAK` |

---

## Arrow Keys

| Key | Code | evdev Name |
|-----|------|-----------|
| Left | 105 | `KEY_LEFT` |
| Right | 106 | `KEY_RIGHT` |
| Up | 103 | `KEY_UP` |
| Down | 108 | `KEY_DOWN` |

---

## Function Keys (F1 through F12)

| Key | Code | evdev Name |
|-----|------|-----------|
| F1 | 59 | `KEY_F1` |
| F2 | 60 | `KEY_F2` |
| F3 | 61 | `KEY_F3` |
| F4 | 62 | `KEY_F4` |
| F5 | 63 | `KEY_F5` |
| F6 | 64 | `KEY_F6` |
| F7 | 65 | `KEY_F7` |
| F8 | 66 | `KEY_F8` |
| F9 | 67 | `KEY_F9` |
| F10 | 68 | `KEY_F10` |
| F11 | 87 | `KEY_F11` |
| F12 | 88 | `KEY_F12` |
| F13 | 100 | `KEY_F13` |
| F14 | 101 | `KEY_F14` |
| F15 | 102 | `KEY_F15` |
| ... | ... | (up to F24) |

---

## Bracket & Symbol Keys

| Symbol | Code | evdev Name |
|--------|------|-----------|
| [ { | 26 | `KEY_LEFTBRACE` |
| ] } | 27 | `KEY_RIGHTBRACE` |
| ; : | 39 | `KEY_SEMICOLON` |
| ' " | 40 | `KEY_APOSTROPHE` |
| ` ~ | 41 | `KEY_GRAVE` |
| \ | | 43 | `KEY_BACKSLASH` |
| , < | 51 | `KEY_COMMA` |
| . > | 52 | `KEY_DOT` |
| / ? | 53 | `KEY_SLASH` |

---

## Media & Volume Keys

| Key | Code | evdev Name |
|-----|------|-----------|
| Mute | 113 | `KEY_MUTE` |
| Volume Down | 114 | `KEY_VOLUMEDOWN` |
| Volume Up | 115 | `KEY_VOLUMEUP` |
| Power | 116 | `KEY_POWER` |
| Play/Pause | 164 | `KEY_PLAYPAUSE` |
| Previous Track | 165 | `KEY_PREVIOUSSONG` |
| Next Track | 163 | `KEY_NEXTSONG` |
| Rewind | 168 | `KEY_REWIND` |
| Stop | 166 | `KEY_STOPCD` |
| Record | 167 | `KEY_RECORD` |
| Eject | 169 | `KEY_EJECTCD` |

---

## Key Event Values

The `value` field in an event indicates:

```
0 = Key up (released)
1 = Key down (pressed, initial)
2 = Key down (held, autorepeat)
```

Example:
```python
if event.value == 1:
    print("Key pressed")
elif event.value == 2:
    print("Key held (autorepeat)")
elif event.value == 0:
    print("Key released")
```

---

## Mouse Button Keys (BTN_*)

Keyboards can also report mouse buttons:

| Button | Code | evdev Name |
|--------|------|-----------|
| Left Click | 272 | `BTN_MOUSE` or `BTN_LEFT` |
| Right Click | 273 | `BTN_RIGHT` |
| Middle Click | 274 | `BTN_MIDDLE` |
| Side Button | 275 | `BTN_SIDE` |
| Extra Button | 276 | `BTN_EXTRA` |
| Forward | 277 | `BTN_FORWARD` |
| Back | 278 | `BTN_BACK` |

---

## System Keys & Special Functions

| Key | Code | evdev Name |
|-----|------|-----------|
| Sleep | 142 | `KEY_SLEEP` |
| Wake | 143 | `KEY_WAKEUP` |
| Menu/Context | 139 | `KEY_MENU` |
| Windows/Super | 125/126 | `KEY_LEFTMETA` / `KEY_RIGHTMETA` |
| Compose | 127 | `KEY_COMPOSE` |
| Alt Gr | 100 | `KEY_RIGHTALT` (on some layouts) |
| Help | 138 | `KEY_HELP` |

---

## Code Lookup Examples

### Find a Specific Key's Code

```python
from evdev import ecodes

# Example 1: What's the code for Left Meta (Super)?
code = ecodes.KEY_LEFTMETA
print(f"KEY_LEFTMETA = {code}")  # Output: 125

# Example 2: What key name is code 125?
name = ecodes.KEY[125]
print(f"Key 125 is {name}")  # Output: KEY_LEFTMETA

# Example 3: Get all keys starting with KEY_
for key in sorted(dir(ecodes)):
    if key.startswith('KEY_'):
        code = getattr(ecodes, key)
        print(f"{key}: {code}")
```

### Detecting Specific Keys

```python
import evdev
from evdev import ecodes

device = evdev.InputDevice('/dev/input/event1')

for event in device.read_loop():
    if event.type == ecodes.EV_KEY:
        # Detect specific keys
        if event.code == ecodes.KEY_LEFTMETA and event.value == 1:
            print("Super key pressed")

        if event.code == ecodes.KEY_LEFTALT and event.value == 1:
            print("Alt key pressed")

        # Get readable name
        key_name = ecodes.KEY.get(event.code, f'UNKNOWN_{event.code}')
        print(f"Key code {event.code} ({key_name}): {event.value}")
```

---

## Common Hotkey Combinations (Code Examples)

### Super+1
```python
if event.code == ecodes.KEY_LEFTMETA or event.code == ecodes.KEY_RIGHTMETA:
    if event.value == 1:
        # Check if 1 is also held
        if ecodes.KEY_1 in held_keys:
            print("Super+1 pressed")
```

### Ctrl+Alt+Delete
```python
def check_combo(held_keys):
    has_ctrl = ecodes.KEY_LEFTCTRL in held_keys or ecodes.KEY_RIGHTCTRL in held_keys
    has_alt = ecodes.KEY_LEFTALT in held_keys or ecodes.KEY_RIGHTALT in held_keys
    has_del = ecodes.KEY_DELETE in held_keys

    if has_ctrl and has_alt and has_del:
        print("Ctrl+Alt+Delete pressed")
```

### Alt+Tab (Hold Tab while Alt is pressed)
```python
# When Tab is pressed
if event.code == ecodes.KEY_TAB and event.value == 1:
    has_alt = ecodes.KEY_LEFTALT in held_keys or ecodes.KEY_RIGHTALT in held_keys
    if has_alt:
        print("Alt+Tab detected")
```

---

## Encoding Notes

- All key codes are from Linux kernel's `input-event-codes.h`
- python-evdev mirrors these constants exactly
- Same codes work across all Linux distributions
- Codes are hardware-independent (kernel abstracts the hardware)
- Same codes work on both X11 and Wayland

---

## Related References

- Linux kernel docs: https://docs.kernel.org/input/event-codes.html
- python-evdev docs: https://python-evdev.readthedocs.io/
- Full research: See `wayland_keyboard_monitoring_research.md`
- Examples: See `wayland_keyboard_examples.py`
