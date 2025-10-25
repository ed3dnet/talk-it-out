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
