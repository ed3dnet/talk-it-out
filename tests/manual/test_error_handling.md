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
