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
2. Change combo to: `test = [["INVALID_KEY"]]`
3. Save and exit
4. Run: `uv run python -m talk_it_out.main run`

**Expected Results:**
- [ ] Application exits immediately
- [ ] Error message shows: `Invalid key name 'INVALID_KEY'`
- [ ] Error mentions checking evdev.ecodes
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
