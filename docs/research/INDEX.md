# Wayland Keyboard Monitoring Research - Complete Index

This directory contains comprehensive research and working solutions for detecting keyboard input (including global hotkeys with modifier combinations) on Linux Wayland with KDE Plasma 6.

**Platform**: KDE Plasma 6.3.4 on Fedora 42 (Wayland)
**Research Date**: October 25, 2025
**Status**: Current and validated

---

## Files Overview

### 1. **QUICK_START.md** (Start Here)
**Purpose**: Get started in 1 minute
**Contains**:
- Installation instructions
- Minimal working examples (copy-paste ready)
- Common key names you need
- Quick troubleshooting
- Comparison table of approaches

**Best For**: You want to implement something quickly without reading everything

**Length**: 4.8 KB | **Read Time**: 5 minutes

---

### 2. **wayland_keyboard_monitoring_research.md** (The Bible)
**Purpose**: Comprehensive research and deep explanations
**Contains**:
- Detailed answers to all 5 research questions
- Wayland security model explanation
- Comparison of all alternatives (pynput, python-evdev, KGlobalAccel, swhkd, wayremap)
- Architecture diagrams
- Practical implementation examples
- Installation and setup for Fedora 42
- Known limitations and caveats
- Complete reference links

**Best For**: Understanding why Wayland works differently, comparing options, or diving deep

**Length**: 25 KB | **Read Time**: 30-40 minutes

---

### 3. **wayland_keyboard_examples.py** (Copy-Paste Code)
**Purpose**: Working Python code examples you can run immediately
**Contains**:
- Example 1: List keyboard devices
- Example 2: Simple key press detection
- Example 3: Detect modifier combinations (Super+Alt)
- Example 4: Detect key hold duration
- Example 5: Monitor multiple devices simultaneously
- Example 6: Complex hotkey registration system (HotkeyMonitor class)
- Example 7: Async keyboard reading
- Reference guide for common key names

**Best For**: Learning by doing, or getting a complete working implementation

**Usage**: `python3 wayland_keyboard_examples.py`

**Length**: 18 KB | **Read Time**: 15-20 minutes (to understand), 2 minutes (to copy code)

---

### 4. **KEY_NAMES_REFERENCE.md** (Look-Up Reference)
**Purpose**: Complete reference of key names and their numeric codes
**Contains**:
- Modifier keys (Super, Alt, Ctrl, Shift)
- Letter keys (A-Z with codes)
- Number keys (0-9)
- Numpad keys
- Special keys (Enter, Escape, arrows, etc.)
- Function keys (F1-F24)
- Media keys (Play, Pause, Volume, etc.)
- How to look up keys dynamically in code
- Common hotkey combination examples

**Best For**: Finding the exact key code/name you need

**Length**: 8.6 KB | **Reference Table**: 200+ keys

---

### 5. **INDEX.md** (This File)
**Purpose**: Navigation guide for the research
**Contains**:
- Overview of all files
- Quick lookup for specific questions
- Learning paths based on your goal
- File relationship diagram

**Best For**: Orienting yourself, understanding structure

---

## Quick Lookup by Question

### "Does pynput work on Wayland?"
→ See `wayland_keyboard_monitoring_research.md` Section 1: "pynput on Wayland: Status and Issues"

**TL;DR**: No. Broken as of February 2025 even with uinput backend.

---

### "What alternatives exist?"
→ See `wayland_keyboard_monitoring_research.md` Section 3: "Working Alternatives for Global Hotkey Detection"

**Options**:
1. python-evdev (kernel-level, works great, requires setup)
2. KGlobalAccel/DBus (KDE native, limited functionality)
3. swhkd (Rust daemon, complete solution)
4. wayremap (Python, less mature)

---

### "How do I detect Super+Alt?"
→ See `QUICK_START.md` "Detect Super+Alt" or `wayland_keyboard_examples.py` Example 3

**Key insight**:
- `KEY_LEFTMETA` / `KEY_RIGHTMETA` = Super key
- `KEY_LEFTALT` / `KEY_RIGHTALT` = Alt key
- Track held keys, check both are present

---

### "What are the key name conventions?"
→ See `KEY_NAMES_REFERENCE.md` (complete lookup table) or quick reference in `QUICK_START.md`

**Important distinction**:
- **evdev names**: `KEY_A`, `KEY_LEFTMETA` (all caps, underscores)
- **swhkd names**: `a`, `super` (lowercase, human-friendly)
- **XKB names**: `<AD01>` (symbolic, not relevant here)

---

### "How do I measure key hold duration?"
→ See `wayland_keyboard_examples.py` Example 4: "Detect Key Hold Duration"

**Approach**: Track `time.time()` when key is pressed (value=1), calculate difference when released (value=0)

---

### "Does KGlobalAccel work on Wayland?"
→ See `wayland_keyboard_monitoring_research.md` Section 3.1

**Yes, but limited**:
- Can only INVOKE existing registered shortcuts
- Cannot DETECT keypresses
- KDE-specific
- Use for integrating with KDE's shortcut system

---

### "What about X11 on the same system?"
→ See `wayland_keyboard_monitoring_research.md` Section 6

**Recommendation**: python-evdev works on both X11 and Wayland. Use it for cross-platform compatibility.

---

### "How do I find my keyboard device path?"
→ See `QUICK_START.md` "Find Your Keyboard Device" or `wayland_keyboard_examples.py` Example 1

**Quick command**:
```bash
python -m evdev.evtest
```

---

## Learning Paths

### Path 1: "I Just Want Something That Works" (15 minutes)
1. Read: `QUICK_START.md` (5 min)
2. Copy code: `wayland_keyboard_examples.py` Example 2 or 3 (5 min)
3. Run and adapt: Test with your keyboard (5 min)

**Result**: Working keyboard monitoring on Wayland

---

### Path 2: "I Want to Understand Everything" (60 minutes)
1. Read: `QUICK_START.md` (5 min) - orientation
2. Read: `wayland_keyboard_monitoring_research.md` Sections 1-3 (20 min) - background
3. Skim: `wayland_keyboard_monitoring_research.md` Sections 4-6 (10 min) - solutions overview
4. Run: `wayland_keyboard_examples.py` with different examples (15 min) - hands-on
5. Reference: `KEY_NAMES_REFERENCE.md` as needed (10 min) - lookups

**Result**: Deep understanding of Wayland constraints and all available approaches

---

### Path 3: "I Want a Production-Ready Solution" (2 hours)
1. Read: `wayland_keyboard_monitoring_research.md` entirely (40 min)
2. Study: `wayland_keyboard_examples.py` Example 6 (HotkeyMonitor class) (20 min)
3. Understand: Key naming conventions in `KEY_NAMES_REFERENCE.md` (10 min)
4. Make decision: KGlobalAccel vs python-evdev vs swhkd (10 min)
5. Implement and test (40 min)

**Result**: Production-ready implementation specific to your use case

---

## Key Findings Summary

### What Works on Wayland
✅ **python-evdev** - Direct kernel input reading
✅ **KGlobalAccel/DBus** - KDE native (limited)
✅ **swhkd** - Rust-based daemon
✅ **wayremap** - Python remapper

### What Doesn't Work
❌ **pynput** - Broken on Wayland as of 2025
❌ **X11 solutions** - X11 APIs don't work on Wayland
❌ **Global key logging** - Fundamental Wayland security design

### Architecture Insight
```
                X11/Xwayland Path (doesn't work)
                ↓
Keyboard → Kernel → X11 Server → pynput ❌
                ↓
                Direct evdev Path (works!)
                ↓
Keyboard → Kernel → /dev/input/eventX → python-evdev ✅
```

The key: Wayland only protects input going through the compositor. Direct kernel access bypasses the security boundary.

---

## Technical Details at a Glance

| Aspect | Answer |
|--------|--------|
| **Wayland Security Model** | Prevents inter-process input snooping (good security, complicates tools) |
| **Why python-evdev Works** | Reads `/dev/input/eventX` directly from kernel, below Wayland |
| **Why pynput Fails** | Uses X11 core APIs which aren't available on Wayland |
| **Why KGlobalAccel is Limited** | Only invokes shortcuts, doesn't detect keypresses (by design) |
| **Best Python Solution** | python-evdev (low-level, most flexible) |
| **Best Complete Solution** | swhkd (daemon, configuration-based) |
| **Key Naming** | evdev: `KEY_A`, swhkd: `a`, both work great in their context |

---

## Prerequisites Checklist

- [ ] KDE Plasma 6 on Wayland (verify: `echo $XDG_SESSION_TYPE` shows "wayland")
- [ ] Python 3.6+
- [ ] `pip` package manager
- [ ] User in `input` group OR ability to run with `sudo`
- [ ] Ability to find keyboard device path (`/dev/input/eventX`)

---

## Installation Quick Reference

```bash
# Install python-evdev
pip install evdev

# Add user to input group (one-time)
sudo usermod -a -G input $USER
# Then logout and login

# Verify
python -m evdev.evtest
```

---

## File Size and Format

| File | Size | Format | Purpose |
|------|------|--------|---------|
| QUICK_START.md | 4.8 KB | Markdown | Quick reference |
| wayland_keyboard_monitoring_research.md | 25 KB | Markdown | Complete research |
| wayland_keyboard_examples.py | 18 KB | Python | Runnable code |
| KEY_NAMES_REFERENCE.md | 8.6 KB | Markdown | Look-up tables |
| INDEX.md | ~5 KB | Markdown | This file |

**Total**: ~61 KB of pure knowledge, no dependencies

---

## Source Attribution

All research is based on:
- Official python-evdev documentation and source
- Linux kernel input event codes documentation
- KDE Framework documentation (KGlobalAccel, KWin)
- KDE Eco project Season of KDE 2024 blog post (real-world implementation)
- Martin Gräßlin's blog on Wayland security (KDE developer)
- Current GitHub issues and discussions (2024-2025)
- Testing on actual system (KDE Plasma 6.3.4, Fedora 42, Wayland)

---

## Next Steps

1. **To Start Using**: Go to `QUICK_START.md`
2. **To Understand**: Read `wayland_keyboard_monitoring_research.md`
3. **To Code**: Run `python3 wayland_keyboard_examples.py`
4. **To Look Up**: Use `KEY_NAMES_REFERENCE.md`

---

## Questions Not Covered?

This research covers:
- ✅ Global keyboard monitoring on Wayland
- ✅ Modifier key detection (Super, Alt, Ctrl, Shift)
- ✅ Key hold/release detection
- ✅ Multiple key combinations
- ✅ KDE Plasma integration
- ✅ Key naming conventions
- ✅ Wayland security model

Related but not covered:
- Mouse input (similar approach but different events)
- Screen recording / window automation
- Input injection (intentionally restricted on Wayland)
- Non-KDE compositors (swhkd works, but different setup)
- Wayland protocols for custom compositors

---

## Last Updated

October 25, 2025

Current as of:
- KDE Plasma 6.3.4
- Fedora 42
- Linux kernel 6.17.4
- python-evdev latest
- Wayland specification 1.0

---

**Welcome to Wayland keyboard monitoring! You've got this.**
